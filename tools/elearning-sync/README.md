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

The script learns the layout from the repo instead of hard-coding paths:

1. It scans `year-*/semester-*/` for course folders.
2. It matches each Blackboard course to a folder by acronym — `Segurança de Dados` → `SD`,
   `Segurança de Redes` → `SR`, `Segurança de Sistemas de Computação [MC]` → `SSC`.
3. It routes each PDF by its title into the folders that course already has:

| Item | Destination |
| ---- | ----------- |
| Lecture decks (`Lecture 3: …`, `00 DS Presentation.pdf`, `NetSecurity-01: …`) | `<course>/theory/`, flat |
| Lab guides (`Lab 3: …`) | `<course>/guides/` if it exists, else `<course>/labs/` |
| Assignment sheets (`Assignment 2`, `Ficha 3`) | `<course>/assignments/` |
| Anything unrecognised | `<course>/theory/` |

Only `resource/x-bb-file` items with `mimeType: application/pdf` are downloaded. Ultra
documents (lab statements written in the page editor) and ZIPs are ignored — grab those by
hand if you need them.

Duplicates are never created:

- a file that already exists with the same size is skipped;
- a lab guide is skipped when `guides/` already has a PDF for that lab number, whatever
  its name (`Lab 3` matches `03 - PAM and the Authentication Stack.pdf`);
- content is compared by hash before writing, so a re-download under a new name is caught.

That means a second run on an unchanged course prints `0 downloaded, N unchanged`.

## Notes

- The cookie expires (typically within hours). When it does you get
  `session rejected (HTTP 401)` — just copy a fresh one.
- The script only reads: it never posts, submits, or modifies anything on eLearning.
- Sequential, one request per file. Don't loop it.
- Course material belongs to the University of Minho and the lecturers. This is for your
  own study; do not republish it.
