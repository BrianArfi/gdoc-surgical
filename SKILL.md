---
name: gdoc-surgical
description: Edit a Google Doc in place without overwriting it. Use for any change to an existing Doc - fixing a line, updating a table cell, adding a revision row, hyperlinking a reference, appending a section - so hand edits, comments, images and sharing survive. Use INSTEAD of any tool that writes a whole document, because those delete edits made since your last read.
---

# gdoc-surgical

A connected Google Doc is not a private file. Other people edit it, and they do,
between the moment you last read it and the moment you write.

Most write tools replace the whole document. So their edit is not merged, it is
deleted, and nothing warns them. They find out when they reopen the document and
their paragraph is gone.

This skill edits the parts you name and leaves the rest alone.

## The order, every time

1. **Read the live document.** Not your local copy, and not the version you
   produced earlier in this conversation. The one that is there now.

   ```bash
   python3 gdoc_surgical.py read --id DOC_ID
   python3 gdoc_surgical.py list-tables --id DOC_ID
   ```

2. **Verify the target is unique.** `replace` hits every occurrence. If the
   find-string is short or common, widen it until only your target matches.

3. **Write the smallest edit that does the job.**

4. **Report the document link**, and treat a write with no document id in the
   response as a failure.

A version number or a changelog row does not stand in for step 1. Somebody can
edit a document without touching either, which is exactly the case this rule
exists for.

## Commands

```bash
python3 gdoc_surgical.py read         --id DOC_ID
python3 gdoc_surgical.py list-tables  --id DOC_ID
python3 gdoc_surgical.py replace      --id DOC_ID --find "old text" --with "new text" [--match-case]
python3 gdoc_surgical.py linkify      --id DOC_ID --find "Q3 Roadmap" --url "https://..."
python3 gdoc_surgical.py append       --id DOC_ID --text '## Heading\n- a bullet\nplain line'
python3 gdoc_surgical.py insert-table --id DOC_ID --rows "Header A|Header B" --rows "1|2"
python3 gdoc_surgical.py insert-row   --id DOC_ID --table 0 --cells "v1.3|2026-09-22|Sam|Added the refund rule"
python3 gdoc_surgical.py set-cell     --id DOC_ID --table 0 --row 2 --col 1 --with "Approved" --expect "Pending"
python3 gdoc_surgical.py delete-row   --id DOC_ID --table 0 --row 3 --expect "text in that row"
```

Add `--account <name>` for a second Google account, or `--token <path>` to point
at a token file directly.

## Choosing between replace and set-cell

`replace` is global. It cannot safely target a cell whose whole content is a
common string: a version cell reading `1.4` would also rewrite every `1.4` in the
changelog. Address a cell by coordinate with `set-cell` instead.

## The guards, and why not to route around them

- **`--expect` on `delete-row` and `set-cell`.** Row indexes move under any
  concurrent edit. `--expect` names text that must already be in the target, so
  a shifted index fails loudly instead of editing somebody else's row. Do not
  drop it to save a step.
- **`replace` exits 2 when it changed nothing.** That is a real failure: the
  wording is not what you remembered, so read again rather than trying variants.
- **Revision tables cannot go backwards.** A version at or below one already in
  the table is refused, because a version number that goes backwards is
  invisible to a reader. `--allow-version-regression` exists for a deliberate
  duplicate and nothing else.
- **Every write is verified.** No document id in the response means failure, not
  a quiet success. Never report a doc as updated on an unchecked response.

## What this does not do

- **Create a document.** It edits existing ones.
- **Rewrite a whole document.** If that is genuinely what you want, you are
  choosing to delete other people's edits, so say that out loud first.
- **Read or resolve comments.** Different API surface.

## If an edit has already been lost

Say so plainly rather than hoping it goes unnoticed, and recover it. Google Docs
keeps version history, and the overwritten version is still in there: **File,
Version history, See version history**. Restore from it, merge it into the
current text, and tell the owner what was lost and what came back.

## Setup

```bash
pip install -r requirements.txt
python3 gdoc_surgical.py auth --credentials client_secret.json
```

Needs the Google Docs API and the Google Drive API enabled on the Cloud project,
and an OAuth client of type Desktop app. A Drive-scoped token issued by another
tool also works.

## Tests

```bash
python3 tests/test_gdoc_surgical.py
```
