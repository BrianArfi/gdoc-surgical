# gdoc-surgical

![version 1.0.0](https://img.shields.io/badge/version-1.0.0-blue) Version 1.0.0. See [CHANGELOG.md](CHANGELOG.md).

Most tools that write to a Google Doc replace the whole document. So an edit
somebody made between your last read and your write is not merged, it is deleted,
and nothing warns them. They find out when they reopen the document and their
paragraph is gone.

This edits the parts you name and leaves the rest alone: hand edits, comments,
suggestions, images, sharing, revision history.

```bash
pip install -r requirements.txt
python3 gdoc_surgical.py auth --credentials client_secret.json

python3 gdoc_surgical.py read         --id DOC_ID
python3 gdoc_surgical.py replace      --id DOC_ID --find "Q3 target" --with "Q4 target"
python3 gdoc_surgical.py linkify      --id DOC_ID --find "Q3 Roadmap" --url "https://..."
python3 gdoc_surgical.py append       --id DOC_ID --text '## Decision\n- we ship on the 30th'
python3 gdoc_surgical.py list-tables  --id DOC_ID
python3 gdoc_surgical.py insert-row   --id DOC_ID --table 0 --cells "v1.3|2026-09-22|Sam|Added the refund rule"
python3 gdoc_surgical.py set-cell     --id DOC_ID --table 0 --row 2 --col 1 --with "Approved" --expect "Pending"
python3 gdoc_surgical.py delete-row   --id DOC_ID --table 0 --row 3 --expect "the draft row"
```

One file, no framework, nothing to configure beyond the token.

## Why the guards are the point

Every destructive command targets an index, and indexes move the moment somebody
else edits the document. So each one refuses to guess:

- **`delete-row` and `set-cell` want `--expect`**: text that must already be in
  the target. A shifted index then fails loudly instead of quietly editing the
  wrong row. This is the difference between a tool you can run unattended and
  one you cannot.
- **`replace` reports the occurrence count before it writes**, and exits 2 when
  it changed nothing, because a silent zero-match usually means the wording is
  not what you remembered.
- **Revision tables cannot go backwards.** Writing `v1.2` into a table that
  already has `v1.3` is refused. A version number that goes backwards is
  invisible: the row looks right and the reader trusts a version that is older
  than the text above it. Override with `--allow-version-regression`.
- **Every write is verified.** An API response with no document id in it is
  reported as a failure, never as a quiet success.

## Commands

| Command | What it does |
| :--- | :--- |
| `read` | Print the document with the index of every paragraph, so you can find your target |
| `list-tables` | Every table with its index, size and header row |
| `replace` | Replace every occurrence of exact text |
| `linkify` | Hyperlink every occurrence, including inside table cells, without changing the visible text |
| `append` | Add markdown-ish text at the end: `#` headings, `-` bullets, plain lines |
| `insert-table` | Append a table and fill it |
| `insert-row` | Insert a row into a table and fill its cells |
| `set-cell` | Replace one cell, addressed by row and column |
| `delete-row` | Delete one row |

Always `read` or `list-tables` first. `replace` hits EVERY occurrence, so widen
the find-string until it is unique.

## Auth

You need an OAuth client from the Google Cloud Console: **APIs and Services →
Credentials → Create credentials → OAuth client ID → Desktop app**, then download
the JSON. Enable the **Google Docs API** and the **Google Drive API** on that
project.

```bash
python3 gdoc_surgical.py auth --credentials client_secret.json
```

The token lands in `~/.config/gdoc-surgical/default.json` and refreshes itself.
Several accounts: `--account work` writes `work.json`, and every command takes
the same flag. `--token /path/to/token.json` overrides both, and
`GDOC_SURGICAL_TOKEN` does the same from the environment.

A Drive-scoped token already issued by another tool works here, the Docs API
accepts it.

## Using it as an agent skill

`SKILL.md` carries the rules of engagement in the format Claude Code and similar
harnesses read. Drop the directory into your skills folder:

```bash
cp -r gdoc-surgical ~/.claude/skills/
```

The rule that matters for an agent: read the live document before writing to it.
A version number or a changelog row is not a substitute, because somebody can
edit a document without touching either.

## Tests

```bash
python3 tests/test_gdoc_surgical.py
```

No network and no credentials. The request builders and the guards are pure
functions over plain dicts, which is why they are pure functions.

## Changelog

Every release is recorded in [CHANGELOG.md](CHANGELOG.md), newest first. The CLI
reads the same file:

```bash
python3 gdoc_surgical.py --version            # gdoc-surgical 1.0.0
python3 gdoc_surgical.py --changelog          # list of versions
python3 gdoc_surgical.py --changelog full     # the whole changelog
```

## License

MIT. See [LICENSE](LICENSE).
