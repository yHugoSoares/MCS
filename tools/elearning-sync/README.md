# eLearning sync

Pulls the lecture PDFs from [UMinho eLearning](https://elearning.uminho.pt/ultra/courses)
(Blackboard Ultra) into this repo, mirroring each course's folder structure inside its
`theory/` folder.

It does **not** scrape HTML and does **not** log in. It replays the same REST calls the
Ultra web app makes, using a session cookie you copy from your own browser:

| Call | Purpose |
| ---- | ------- |
| `GET /learn/api/v1/users/me/memberships?expand=course.effectiveAvailability` | courses you are enrolled in |
| `GET /learn/api/v1/courses/{pk}/contents?recursive=true` | course outline (folders + items) |
| `GET /bbcswebdav/pid-…/xid-…` | the actual file |

Pure Python standard library — no dependencies.

## Why not log in with a password?

UMinho's identity provider (`login2.uminho.pt`) sits behind a WAF that blocks automated
logins and returns *"O URL que tentou aceder foi Bloqueado"*. Trying to get around that
would be evasion of your institution's security controls, so this tool doesn't attempt it.
You log in normally once and hand it the resulting cookie.

## Setup

```sh
cd tools/elearning-sync
cp .env.example .env
chmod 600 .env
```

Then grab the cookie:

1. Log in at <https://elearning.uminho.pt/ultra/courses> in your normal browser.
2. Open DevTools → **Network**.
3. Reload the page, click any request whose URL starts with `/learn/api/`.
4. Under **Request Headers**, copy the whole `Cookie:` value.
5. Paste it after `ELEARNING_COOKIE=` in `.env` (quotes are fine).

## Usage

```sh
python3 sync.py --list       # tree only, no downloads
python3 sync.py --dry-run    # what would be written
python3 sync.py              # download
python3 sync.py --course SD  # one course (SD, SR, SSC)
python3 sync.py --force      # re-download unchanged files
```

Existing files with the same size are skipped, so re-running is cheap.

## What goes where

| Course | Destination |
| ------ | ----------- |
| Segurança de Dados | `year-1/semester-1/SD/theory/` |
| Segurança de Redes | `year-1/semester-1/SR/theory/` |
| Segurança de Sistemas de Computação | `year-1/semester-1/SSC/theory/` |
| anything else | `materials/<slug>/theory/` |

Only `resource/x-bb-file` items with `mimeType: application/pdf` are downloaded. Ultra
documents (lab statements written in the page editor) and ZIPs are ignored — grab those by
hand if you need them.

Because the whole outline is mirrored, lab guides that happen to be PDFs land in `theory/`
too, inside their original block folder. Prune or move them as you like.

## Notes

- The cookie expires (typically within hours). When it does you get
  `session rejected (HTTP 401)` — just copy a fresh one.
- The script only reads: it never posts, submits, or modifies anything on eLearning.
- Sequential, one request per file. Don't loop it.
- Course material belongs to the University of Minho and the lecturers. This is for your
  own study; do not republish it.
