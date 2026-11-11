#!/usr/bin/env python3
"""Sync lecture PDFs from UMinho eLearning (Blackboard Ultra) into this repo.

Auth: the UMinho identity provider blocks automated logins (WAF), so this tool
does not try to log in. You log in normally in your browser, copy the session
cookie once, and put it in .env:

    ELEARNING_COOKIE="BbRouter=...; session_id=...; ..."

Then it replays the Ultra web app's own REST calls:

    GET /learn/api/v1/users/me/memberships?expand=course.effectiveAvailability
    GET /learn/api/v1/courses/{pk}/contents?recursive=true
    GET /bbcswebdav/pid-…/xid-…            (the file itself)

PDFs are mirrored, preserving the course's folder structure, into
``<course>/theory/``.

Usage:
    python3 sync.py --list          # show the tree, download nothing
    python3 sync.py --dry-run       # show what would be saved
    python3 sync.py                 # download everything
    python3 sync.py --course SD     # one course only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://elearning.uminho.pt"
REPO_ROOT = Path(__file__).resolve().parents[2]
SEMESTER_DIR = REPO_ROOT / "year-1" / "semester-1"

# A normal browser UA: the WAF rejects default python-urllib clients outright.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
)

# Course name (substring, accent-insensitive) -> repo folder under the semester.
COURSE_FOLDERS = {
    "seguranca de dados": "SD",
    "seguranca de redes": "SR",
    "seguranca de sistemas de computacao": "SSC",
}

FILE_HANDLER = "resource/x-bb-file"


# --------------------------------------------------------------------------- utils


def norm(text: str) -> str:
    """Lowercase and strip accents, for tolerant matching."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", norm(text)).strip("-") or "course"


def safe_name(name: str) -> str:
    """Make a title safe to use as a single path component."""
    name = re.sub(r"[/\\:\x00-\x1f]", "-", name).strip().strip(".")
    return name or "untitled"


def load_env(path: Path) -> dict[str, str]:
    """Minimal .env reader (KEY=VALUE, # comments, optional quotes)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def human(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


# ---------------------------------------------------------------------------- http


class Client:
    def __init__(self, cookie: str) -> None:
        self.cookie = cookie.strip()

    def open(self, path: str) -> urllib.request.addinfourl:
        req = urllib.request.Request(
            BASE + path,
            headers={
                "Cookie": self.cookie,
                "User-Agent": USER_AGENT,
                "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
                "Referer": f"{BASE}/ultra/courses",
            },
        )
        try:
            return urllib.request.urlopen(req, timeout=60)
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                raise SystemExit(
                    "session rejected (HTTP %d) — the cookie has expired.\n"
                    "Log in at %s/ultra/courses, copy the Cookie header again\n"
                    "and update ELEARNING_COOKIE in .env." % (exc.code, BASE)
                )
            raise

    def json(self, path: str):
        with self.open(path) as res:
            return json.load(res)

    def bytes(self, path: str) -> bytes:
        with self.open(path) as res:
            return res.read()


# -------------------------------------------------------------------------- crawl


def courses(client: Client) -> list[dict]:
    data = client.json(
        "/learn/api/v1/users/me/memberships"
        "?expand=course.effectiveAvailability&includeCount=true&limit=10000"
    )
    out = []
    for row in data.get("results", []):
        course = row.get("course") or {}
        if course.get("id"):
            out.append({"id": course["id"], "name": course.get("name", "")})
    return out


def outline(client: Client, course_id: str) -> list[dict]:
    return client.json(f"/learn/api/v1/courses/{course_id}/contents?recursive=true").get("results", [])


def folder_path(item: dict, by_id: dict[str, dict]) -> list[str]:
    """Titles of the folders containing `item`, outermost first."""
    parts, parent = [], by_id.get(item.get("parentId") or "")
    while parent is not None:
        if parent.get("contentHandler") == "resource/x-bb-folder":
            parts.append(safe_name(parent.get("title", "")))
        parent = by_id.get(parent.get("parentId") or "")
    return list(reversed(parts))


def pdf_of(item: dict) -> dict | None:
    if item.get("contentHandler") != FILE_HANDLER:
        return None
    detail = (item.get("contentDetail") or {}).get(FILE_HANDLER) or {}
    file = detail.get("file") or {}
    if file.get("mimeType") != "application/pdf":
        return None
    url = file.get("permanentUrl") or file.get("viewerUrl")
    if not url:
        return None
    return {
        "name": file.get("fileName") or item.get("title") or "document.pdf",
        "url": url,
        "size": int(file.get("fileSize") or 0),
    }


def destination(course_name: str, folder: list[str], filename: str) -> Path:
    key = next((v for k, v in COURSE_FOLDERS.items() if k in norm(course_name)), None)
    course_dir = SEMESTER_DIR / key if key else REPO_ROOT / "materials" / slug(course_name)
    return course_dir / "theory" / Path(*folder) / safe_name(filename)


# ----------------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--course", action="append", metavar="CODE", help="only this repo folder (SD, SR, SSC); repeatable")
    parser.add_argument("--list", action="store_true", help="print the course tree and exit")
    parser.add_argument("--dry-run", action="store_true", help="show what would be downloaded")
    parser.add_argument("--force", action="store_true", help="re-download files that already exist")
    parser.add_argument("--env", default=str(Path(__file__).with_name(".env")), help="path to the .env file")
    args = parser.parse_args()

    env = {**load_env(Path(args.env)), **os.environ}
    cookie = env.get("ELEARNING_COOKIE", "")
    if not cookie:
        raise SystemExit(
            "ELEARNING_COOKIE is not set.\n"
            "Log in at %s/ultra/courses, open DevTools > Network, pick any\n"
            "'/learn/api/...' request, copy its Cookie request header into .env." % BASE
        )

    client = Client(cookie)
    todo: list[tuple[Path, dict]] = []

    for course in courses(client):
        key = next((v for k, v in COURSE_FOLDERS.items() if k in norm(course["name"])), None)
        if args.course and key not in args.course:
            continue
        items = outline(client, course["id"])
        by_id = {i["id"]: i for i in items}
        pdfs = [(folder_path(i, by_id), p) for i in items if (p := pdf_of(i))]
        print(f"\n{course['name']} -> {key or 'materials/' + slug(course['name'])}: {len(pdfs)} PDFs")
        for folder, pdf in pdfs:
            dest = destination(course["name"], folder, pdf["name"])
            todo.append((dest, pdf))
            if args.list:
                print("  " + str(dest.relative_to(REPO_ROOT)))
            elif args.dry_run:
                state = "skip" if dest.exists() and not args.force else "get "
                print(f"  {state} {dest.relative_to(REPO_ROOT)}")

    if args.list or args.dry_run:
        return 0

    saved = skipped = failed = 0
    for dest, pdf in todo:
        if dest.exists() and not args.force and dest.stat().st_size == pdf["size"]:
            skipped += 1
            continue
        try:
            body = client.bytes(pdf["url"])
            if not body.startswith(b"%PDF"):
                raise RuntimeError("not a PDF")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(body)
            saved += 1
            print(f"  + {dest.relative_to(REPO_ROOT)} ({human(len(body))})")
        except SystemExit:
            raise
        except Exception as exc:  # keep going; report at the end
            failed += 1
            print(f"  ! {dest.relative_to(REPO_ROOT)}: {exc}", file=sys.stderr)

    print(f"\n{saved} downloaded, {skipped} unchanged, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
