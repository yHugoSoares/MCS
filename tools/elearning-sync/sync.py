#!/usr/bin/env python3
"""Sync lecture PDFs from UMinho eLearning (Blackboard Ultra) into this repo.

Auth: the UMinho identity provider blocks automated logins (WAF), so this tool
does not try to log in. You log in normally in your browser, copy the session
cookie once, and put it in .env:

    ELEARNING_COOKIE="BbRouter=...; session_id=...; ..."

The destination structure is learned from the repo itself:

  * course folders are discovered under year-*/semester-*/<CODE>
  * a Blackboard course name is matched to a folder by its acronym
    ("Segurança de Dados" -> SD, "Segurança de Sistemas de Computação" -> SSC)
  * items are routed by title into the folders that course already has:
        lecture decks      -> <course>/theory/      (flat)
        lab guides         -> <course>/guides/      (or <course>/labs/)
        assignment sheets  -> <course>/assignments/
  * a lab guide is skipped when that lab is already present in guides/

It replays the Ultra web app's own REST calls:

    GET /learn/api/v1/users/me/memberships?expand=course.effectiveAvailability
    GET /learn/api/v1/courses/{pk}/contents?recursive=true
    GET /bbcswebdav/pid-…/xid-…            (the file itself)

Usage:
    python3 sync.py --list          # show where everything would go
    python3 sync.py --dry-run       # same, with get/skip decisions
    python3 sync.py                 # download
    python3 sync.py --course SD     # one course
"""

from __future__ import annotations

import argparse
import hashlib
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

# A normal browser UA: the WAF rejects default python-urllib clients outright.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
)

FILE_HANDLER = "resource/x-bb-file"

STOPWORDS = {"de", "da", "do", "das", "dos", "e", "em", "para", "of", "the", "and", "a", "o"}

LAB_RE = re.compile(r"\blab\b", re.I)
ASSIGNMENT_RE = re.compile(r"\b(assignment|assessment|ficha|enunciado|trabalho)\b", re.I)
LAB_NUMBER_RE = re.compile(r"\blab\s*0*(\d+)", re.I)


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


# ------------------------------------------------------------- repo structure


def discover_courses() -> dict[str, Path]:
    """Map course code -> folder, by scanning year-*/semester-*/."""
    found: dict[str, Path] = {}
    for year in sorted(REPO_ROOT.glob("year-*")):
        for semester in sorted(year.glob("semester-*")):
            for course in sorted(semester.iterdir()):
                if course.is_dir() and not course.name.startswith("."):
                    found.setdefault(course.name.upper(), course)
    return found


def acronym(name: str) -> str:
    """'[26-27] Segurança de Dados' -> 'SD'; '[MC]' is ignored."""
    clean = re.sub(r"\[[^\]]*\]", " ", name)
    words = re.findall(r"[0-9A-Za-zÀ-ÿ]+", clean)
    return "".join(w[0].upper() for w in words if norm(w) not in STOPWORDS)


def resolve_course(name: str, courses: dict[str, Path]) -> tuple[str | None, Path | None]:
    code = acronym(name)
    if code in courses:
        return code, courses[code]
    for candidate, path in courses.items():  # e.g. SD2627 -> SD
        if candidate and code.startswith(candidate):
            return candidate, path
    return None, None


def category(title: str) -> str:
    if LAB_RE.search(title):
        return "lab"
    if ASSIGNMENT_RE.search(title):
        return "assignment"
    return "theory"


def destination(course_dir: Path, cat: str, filename: str) -> Path:
    if cat == "lab":
        guides = course_dir / "guides"
        folder = guides if guides.is_dir() else course_dir / "labs"
    elif cat == "assignment":
        folder = course_dir / "assignments"
    else:
        folder = course_dir / "theory"
    return folder / safe_name(filename)


def existing_lab(course_dir: Path, title: str) -> Path | None:
    """A lab guide already in guides/ for the same lab number, whatever its name."""
    match = LAB_NUMBER_RE.search(title)
    guides = course_dir / "guides"
    if not match or not guides.is_dir():
        return None
    number = int(match.group(1))
    pattern = re.compile(rf"^(?:lab[-_ ]?)?0*{number}(?:\D|$)", re.I)
    return next((p for p in sorted(guides.glob("*.pdf")) if pattern.match(p.name)), None)


def duplicate_of(folder: Path, body: bytes) -> Path | None:
    """An existing file in `folder` with identical bytes."""
    if not folder.is_dir():
        return None
    digest = hashlib.md5(body).hexdigest()
    for path in folder.glob("*.pdf"):
        if path.stat().st_size == len(body) and hashlib.md5(path.read_bytes()).hexdigest() == digest:
            return path
    return None


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


# ----------------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--course", action="append", metavar="CODE", help="only this course folder (SD, SR, SSC); repeatable")
    parser.add_argument("--list", action="store_true", help="print the destination of every PDF and exit")
    parser.add_argument("--dry-run", action="store_true", help="show get/skip decisions without writing")
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
    known = discover_courses()
    todo: list[tuple[Path, dict]] = []

    for course in courses(client):
        code, course_dir = resolve_course(course["name"], known)
        if args.course and code not in args.course:
            continue
        label = code or f"materials/{slug(course['name'])}"
        if course_dir is None:
            course_dir = REPO_ROOT / "materials" / slug(course["name"])

        items = outline(client, course["id"])
        pdfs = [p for i in items if (p := pdf_of(i))]
        counts: dict[str, int] = {}
        print(f"\n{course['name']} -> {label}: {len(pdfs)} PDFs")

        for item in items:
            pdf = pdf_of(item)
            if not pdf:
                continue
            cat = category(item.get("title", ""))
            counts[cat] = counts.get(cat, 0) + 1
            dest = destination(course_dir, cat, pdf["name"])
            todo.append((dest, pdf, item.get("title", "")))
            if args.list:
                print(f"  [{cat}] {dest.relative_to(REPO_ROOT)}")
            elif args.dry_run:
                state = "get"
                if not args.force:
                    if dest.exists() and dest.stat().st_size == pdf["size"]:
                        state = "skip"
                    elif dest.parent.name == "guides" and (lab := existing_lab(course_dir, item.get("title", ""))):
                        state = f"skip ({lab.name})"
                print(f"  {state:6} [{cat}] {dest.relative_to(REPO_ROOT)}")

        if counts:
            print("  " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))

    if args.list or args.dry_run:
        return 0

    saved = skipped = failed = 0
    for dest, pdf, title in todo:
        if dest.exists() and not args.force and dest.stat().st_size == pdf["size"]:
            skipped += 1
            continue

        course_dir = dest.parents[1]
        if dest.parent.name == "guides" and not args.force:
            already = existing_lab(course_dir, title)
            if already:
                print(f"  = {dest.relative_to(REPO_ROOT)} (already present as {already.name})")
                skipped += 1
                continue

        try:
            body = client.bytes(pdf["url"])
            if not body.startswith(b"%PDF"):
                raise RuntimeError("not a PDF")

            twin = duplicate_of(dest.parent, body) if dest.parent.is_dir() else None
            if twin and not args.force:
                print(f"  = {dest.relative_to(REPO_ROOT)} (identical to {twin.name})")
                skipped += 1
                continue

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
