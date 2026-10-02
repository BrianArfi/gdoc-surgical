# gdoc-surgical

**Let your AI update a shared Google Doc without wiping your teammates' edits and comments.**

For people who let an AI agent, such as Claude Code, keep PRDs, plans and sign-off tables in Google Docs up to date.

[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Version 1.0.0](https://img.shields.io/badge/version-1.0.0-green.svg)](CHANGELOG.md)
[![Made for Claude Code](https://img.shields.io/badge/made%20for-Claude%20Code-orange.svg)](docs/setup.md#use-it-as-an-agent-skill)

![Animated illustration. Headline: Change one line. Keep everyone's work. You ask your AI to move the launch to Q4. Left panel, AI rewrites the whole doc: a red sweep passes over the launch plan, the whole page fades into a new copy, Dina's risk line is struck out, her comment comes loose and is crossed out, and the AI says Done. Right panel, gdoc-surgical edits only the target: the three Q3 2026 dates flip to Q4 2026 in lime, Dina's line stays, her comment stays pinned, and a terminal chip reads [OK] Replaced 3 occurrence(s).](docs/hero.gif)

<sub>Illustration. The real runs are under [See it run](#see-it-run).</sub>

## The problem

Monday morning, Sam and his AI draft the timeline in the shared launch plan. At 3 pm Dina adds a line to that plan, "Risk: payment partner sign-off may slip two weeks", and leaves a comment on the dates: "Check with finance before we move dates."

At 4 pm Sam asks the AI, in the same conversation, to move the launch from Q3 to Q4. The AI writes its new version from the copy it worked on this morning and says "Done". Most tools that write to a Google Doc replace the whole document, so this is what happened:

- **Dina's line is gone.** It was added after the AI last read the doc, so it was not in the copy the AI wrote back. Nothing warned anyone.
- **Her comment came loose** from the text it was pinned to, because that text was replaced.
- **"Done" was not true.** The AI reported success on a document it never checked again.
- **Nobody notices until later**, when Dina asks, "Where did my edit go?", and someone has to dig through version history.
- **The faster AI updates shared docs, the more of other people's work it can remove.**

gdoc-surgical fixes this by never writing a new copy. It sends small, targeted edits through the Google Docs API: this sentence, this table cell, this new row. Everything else in the doc stays as it was.

## Who it is for

**Good fit if you...**

- Let Claude Code or a similar agent update Google Docs that other people also edit: PRDs, launch plans, SOPs, client proposals.
- Keep a revision table or a sign-off table in a doc, and want the AI to add a row or mark one cell as Approved.
- Want an AI edit to fail loudly when the doc changed under it, instead of guessing.
- Script changes to a live doc, and need the same guards without an AI in the loop.
- Are fine with a one-time setup in a terminal (about 10 minutes for the Google sign-in).

**Not for you if...**

- You want AI to create new documents or rewrite a whole document. It only edits documents that already exist, one targeted change at a time.
- You need Google Sheets, Slides, Word or Notion. It works on Google Docs only.
- You want the AI's edits to show up as suggestions for someone to accept. Edits are written into the doc directly. Google Docs version history still keeps the earlier text.
- You need to read, reply to or resolve comments. That is a different API, and this tool does not touch it.
- You need to bring back an edit that another tool already deleted. It prevents the overwrite, it does not undo one.
- You want a hosted service with no install. It is one Python file that runs on your computer.

## Before / After

| Before: a tool that writes the whole doc | After: gdoc-surgical |
| :--- | :--- |
| AI writes a new copy of the whole document | AI changes only the sentence, cell or row you name |
| A teammate's edit from this afternoon is overwritten | Other people's edits, comments, images and sharing stay as they were |
| Comments come loose from their text | Comments stay pinned. Only a comment on the exact text you change can come loose |
| AI says "done" when the text it looked for was not there | Zero matches is a failure: exit code 2, and the AI is told to read again |
| A row index shifted, so the wrong row gets changed | `--expect` names text that must be in the target. If it is not, nothing changes |
| A revision table gets v1.2 under v1.3, and nobody notices | Version numbers in a revision table can only go up |

![Animated illustration of one launch plan with a sliding divider. Without: the doc is a faded new copy, Dina's risk line is struck out with a tag saying Dina's line: gone, her comment is detached and crossed out, and the footer says AI wrote a new copy of the whole doc, then said Done. The divider slides left to reveal With gdoc-surgical: the target date and both table dates read Q4 2026 in lime, Dina's line is tagged kept, her comment is still pinned, and the footer reads [OK] Replaced 3 occurrence(s). Nothing else changed. Then the divider slides back.](docs/before-after.gif)

<sub>Illustration of the same request, two ways.</sub>

## How it works

1. **Read the live doc.** Not a copy from earlier in the conversation, the one that is there now. `read` prints every paragraph and every table row, and `list-tables` prints each table with its header.
2. **Locate the exact target.** `replace` changes every occurrence, so it counts them first: `Found 'Q3 2026' 3 time(s): 1 in paragraphs, 2 in table cells.` Too many? Use longer text, or point at one cell with `set-cell`.
3. **Make the guarded edit.** One small request to the Docs API, never a new copy of the doc. `set-cell` and `delete-row` check `--expect` text first, and a revision table refuses a version that goes backwards. When a guard fails, nothing is written.
4. **Verify the answer.** Success is reported only when the API response carries a document id, and the `[OK]` line ends with the doc link. A `replace` or `linkify` that matched nothing exits 2.

![Animated illustration of the flow. Four cards draw in one by one, joined by arrows: 1 Read the live doc, read --id DOC_ID. 2 Find the exact target, Found 'Q3 2026' 3 time(s). 3 Change only that part, --expect "Q3 2026". 4 Check the answer, [OK] Replaced 3 occurrence(s). A Q3 2026 chip travels under the cards and turns into a lime Q4 2026 chip at step 3. Then a red arrow loops from step 3 back to step 1, labelled Guard fails? Nothing changed. Read the doc again.](docs/how-it-works.gif)

<sub>Illustration. The flow, the guards and the exit codes in detail: [docs/how-it-works.md](docs/how-it-works.md).</sub>

## See it run

The tool's real commands against an offline sample doc. [docs/src/offline_demo.py](docs/src/offline_demo.py) runs the same commands with no Google account, so you can repeat this yourself.

**One replace, three targets, Dina's line untouched:**

![A terminal runs three real gdoc-surgical commands against an offline sample doc. read lists every paragraph and the timeline table rows, with Q3 2026 outlined three times. replace reports 1 match in paragraphs and 2 in table cells, then "OK, Replaced 3 occurrence(s)". A second read shows Q4 2026 on the target line and in both table rows, tagged changed, and the risk line added by Dina, tagged kept](docs/demo.gif)

**The guards refusing to guess:**

![A terminal runs real gdoc-surgical commands against the offline sample doc. set-cell on table 0, row 1 with --expect "Q2 2026" prints ERROR: the cell does not contain the --expect text, expected Q2 2026, cell is Q3 2026, Nothing changed, and echo $? prints 2. A replace for the typo "Q3 2025" finds 0 matches, prints WARN Nothing replaced, and echo $? prints 2. A final read shows the doc unchanged: Q3 2026 is still on the target line and in both table rows, and Dina's risk line is kept.](docs/guards.gif)

<sub>Real output, recorded offline. Sources: [docs/src/render_demo.py](docs/src/render_demo.py) and the captured sessions next to it.</sub>

### On a real Google Doc

Three commands against a [live demo Doc](https://docs.google.com/document/d/1rPF-CNo-Qw7LVqTtNko7bOAbc3-yG3s7F2eLdFl8riw/edit) (anyone with the link can view it):

```text
$ python3 gdoc_surgical.py replace --id DOC_ID --find "beta" --with "closed beta"
[OK] Replaced 7 occurrence(s).
$ python3 gdoc_surgical.py set-cell --id DOC_ID --table 0 --row 1 --col 2 --with "Done" --expect "In progress"
[OK] Table #0 cell (1,2): 'In progress' -> 'Done'.
$ python3 gdoc_surgical.py insert-row --id DOC_ID --table 1 --cells "v1.2|2026-10-01|Status update via gdoc-surgical"
[OK] Row inserted into table #1 at row 3 with 3 cell(s).
```

![The live demo Doc before and after. Before: the plan says beta, Dina's onboarding row is In progress, and the revision table ends at v1.1. After: beta reads closed beta everywhere, Dina's row says Done, a v1.2 row is added, and nothing else in the Doc moved](docs/real-doc-before-after.png)

The comment pinned to the first paragraph is still there after all three edits. A whole-doc rewrite would have detached it.

## Quick start

Sign in to Google once with `client_secret.json` (needs a free Google Cloud OAuth client, about 10 minutes: [setup guide](docs/setup.md)).

```bash
# 1. Install
git clone https://github.com/BrianArfi/gdoc-surgical
cd gdoc-surgical
pip install -r requirements.txt

# 2. Sign in to Google once
python3 gdoc_surgical.py auth --credentials client_secret.json

# 3. Read the doc, then make one edit
python3 gdoc_surgical.py read --id DOC_ID
python3 gdoc_surgical.py replace --id DOC_ID --find "Q3 2026" --with "Q4 2026"
```

The doc id is the long string in the doc URL, between `/d/` and `/edit`. To let Claude Code run the commands for you, copy the folder into your skills folder: `cp -r gdoc-surgical ~/.claude/skills/` ([details](docs/setup.md#use-it-as-an-agent-skill)).

No Google account yet? Try it offline first:

```bash
python3 docs/src/offline_demo.py read --id DEMO_DOC
python3 docs/src/offline_demo.py replace --id DEMO_DOC --find "Q3 2026" --with "Q4 2026"
python3 docs/src/offline_demo.py reset                # put the sample doc back
python3 tests/test_gdoc_surgical.py                   # every guard, against a fake document
```

## Example

Move a launch from Q3 to Q4 in a shared launch plan, mark Dina's sign-off, and log the change, without touching the line she just added:

```text
$ python3 gdoc_surgical.py replace --id DOC_ID --find "Q3 2026" --with "Q4 2026"
[INFO] Found 'Q3 2026' 3 time(s): 1 in paragraphs, 2 in table cells.
[OK] Replaced 3 occurrence(s). Doc: https://docs.google.com/document/d/DOC_ID/edit
```

![A sample launch plan after the replace: the two Q3 2026 targets in the timeline table and the one in the paragraph now read Q4 2026, while a teammate's risk line and the comment pinned to it are unchanged](docs/gdoc-doc-after.png)

<sub>Illustration with a sample document; the output lines are the tool's real format.</sub>

More of what you can ask, and the command your AI runs for it:

| You say | The command |
| :--- | :--- |
| "Mark the design review as Approved" | `set-cell --table 0 --row 2 --col 1 --with "Approved" --expect "Pending"` |
| "Add a v1.3 row to the revision table" | `insert-row --table 0 --cells "v1.3\|2026-09-22\|Sam\|Added the refund rule"` |
| "Link every mention of the Q3 Roadmap" | `linkify --find "Q3 Roadmap" --url "https://..."` |
| "Add today's decision at the end" | `append --text '## Decision log\n- Launch moves to Q4'` |
| "Remove the old draft row" | `delete-row --table 0 --row 3 --expect "draft"` |

Every command and flag: [docs/commands.md](docs/commands.md).

---

## Documentation

- [Why gdoc-surgical](docs/why.md): the problem, the fix, and who it is for
- [How it works](docs/how-it-works.md): the read, check, edit flow, the guards, and what it does not do
- [Commands, flags and exit codes](docs/commands.md): all nine editing commands
- [Setup, auth and requirements](docs/setup.md): Google sign-in, several accounts, agent skill install, tests
- [SKILL.md](SKILL.md): the rules an AI agent follows when it uses this tool
- [Skill page with examples](https://brianarfi.com/skills/gdoc-surgical?utm_source=github&utm_medium=readme&utm_campaign=ai-skills)

## FAQ

**Do I need to code?**
A little, once. The setup is a few terminal commands. After that you can ask your AI, for example Claude Code, in plain words, and it runs the commands.

**Where does my document go?**
Nowhere new. The tool runs on your computer and talks directly to Google with your own account. It has no server of its own. Your token stays in a local file under `~/.config/gdoc-surgical/`.

**What access does it ask for?**
The Google Drive scope, so it can edit any document your account can edit. It only changes the documents and the parts you name in a command.

**What if someone edits while the AI is working?**
Positions in the document can shift. That is why `delete-row` must name text that is in the row, and `set-cell` can do the same. If the text is not there, nothing changes and the command exits 2. Read the document again and retry.

**Will comments survive?**
Yes, except a comment pinned to the exact text you replace: when that text changes, the comment can come loose. Everything else in the doc, including other comments, suggestions, images and sharing, stays as it was.

**Can it create a document, rewrite one, or handle comments?**
No. It only edits documents that already exist, one targeted change at a time. It does not create documents, rewrite a whole document, or read or resolve comments.

**Can it bring back an edit that another tool already deleted?**
No. It prevents the overwrite, it does not undo one. Google Docs keeps its own version history under **File, Version history**, and that is where to look.

**Is it free?**
Yes. It is open source under Apache-2.0, and the Google Cloud OAuth client it needs is free to create.

## Changelog

The full history is in [CHANGELOG.md](CHANGELOG.md), newest first. Latest release: 1.0.0 (2026-09-22). `python3 gdoc_surgical.py --changelog` prints the same list.

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

More AI skills: [BrianArfi.com/skills](https://BrianArfi.com/skills)
