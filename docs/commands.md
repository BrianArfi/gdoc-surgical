# Commands, flags and exit codes

[Back to README](../README.md)

## What it can do

| Command | What you get | Use it for |
| :--- | :--- | :--- |
| `read` | The document as text, each paragraph with its start and end index, each table as `<TABLE #n: rows x cols>` | Finding the exact target before any write |
| `list-tables` | Every table with its index, size, start index and header row | Picking the right `--table` number |
| `replace` | Every occurrence of exact text replaced, body and table cells. Prints the body-paragraph count before it writes, the total changed after, and exits 2 on zero | Renaming a feature across a doc. Moving a target date |
| `linkify` | Every occurrence hyperlinked, including inside table cells. Only the link style changes, never the words. Exits 2 when the text is not found | Linking tickets or a roadmap wherever they are named |
| `append` | New lines at the end. `#` to `####` become headings, `-` or `*` become bullets, the rest is normal text | A weekly update. A decision log entry |
| `insert-table` | A new table at the end, filled row by row from `--rows "a\|b\|c"` flags | A new status table or a risk table |
| `insert-row` | One row inserted below a given row (default: the last row) and filled from `--cells`. A version in the first cell must be higher than every version already in that column | A revision table row. A new line in a tracker table |
| `set-cell` | One cell replaced by row and column. With `--expect`, it changes only if the cell still holds that text | Marking an approval in a sign-off table. Updating one status |
| `delete-row` | One row deleted. `--expect` is mandatory, and the row must contain it | Removing an old draft row |

One Python file, no framework. The only configuration is a Google sign-in.

## Commands and flags

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

| Flag | Used by | Meaning |
| :--- | :--- | :--- |
| `--id` | every command except `auth` | The Google Doc id |
| `--find`, `--with` | `replace` (both), `linkify` (`--find`), `set-cell` (`--with`) | Exact text to find, and the new text |
| `--match-case` | `replace` | Case-sensitive match. Default is case-insensitive |
| `--url` | `linkify` | The link target |
| `--text` | `append` | Text to add. `\n` for a new line, `#` for a heading, `-` for a bullet |
| `--table` | `insert-row`, `set-cell`, `delete-row` | 0-based table index, from `list-tables`. Default 0 |
| `--row` | `insert-row`, `set-cell`, `delete-row` | 0-based row. For `insert-row`, the new row goes below it, and -1 means the last row. Mandatory for `set-cell` and `delete-row` |
| `--col` | `set-cell` | 0-based column. Default 0 |
| `--cells` | `insert-row` | Pipe-separated values. Extra values beyond the column count are dropped with a warning |
| `--rows` | `insert-table` | One pipe-separated row per flag, repeated |
| `--expect` | `set-cell` (optional), `delete-row` (mandatory) | Text that must already be in the target |
| `--allow-version-regression` | `insert-row`, `set-cell` | Permit a version at or below one already in the table |
| `--version`, `--changelog [list\|full]` | none | Print the version, or the bundled changelog |

**Exit codes.** `0` success. `1` an error: no token, a table or row out of range, a write with no document id, or a refused version. `2` nothing matched: zero replacements, `linkify` text not found, or an `--expect` mismatch. In every non-zero case except a failed write response, the document is unchanged. `insert-row` inserts the row first and fills it second. If the fill fails, an empty row remains. `insert-table` works the same way.

`replace` or `set-cell`? `replace` is global. It cannot safely target a cell whose whole content is a common string: a version cell reading `1.4` would also rewrite every `1.4` in the changelog. Address that cell by coordinate with `set-cell`.

## Version and changelog

The CLI reads the bundled [CHANGELOG.md](../CHANGELOG.md):

```bash
python3 gdoc_surgical.py --version            # gdoc-surgical 1.0.0
python3 gdoc_surgical.py --changelog          # list of versions
python3 gdoc_surgical.py --changelog full     # the whole changelog
```
