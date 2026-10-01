# Why gdoc-surgical

[Back to README](../README.md)

Most tools that write to a Google Doc replace the whole document. An edit somebody made since your last read is not merged, it is deleted, and nobody gets a warning. gdoc-surgical changes only the sentence, table row or cell you name, and leaves everything outside that part alone: other people's edits, comments, suggestions, images and sharing. A comment anchored to the exact text you change can still come loose.

## The shift: AI now writes your documents

PRDs, proposals, SOPs. You say what changed, and AI does the writing. That works well in a file only you own. A shared Google Doc is different: people edit it between the moment AI reads it and the moment AI writes. So the AI needs a way to change one part, not the whole document.

| Task | What AI now does | What you say |
| :--- | :--- | :--- |
| Update a PRD | AI rewrites the section you asked about | "Move the launch to Q4 and add a v1.3 row" |
| Keep a sign-off table | AI marks each approval as it comes in | "Mark the design review as Approved" |
| Link tickets across a doc | AI adds the link wherever the ticket is named | "Link every mention of the Q3 Roadmap" |
| Log a decision | AI adds the entry at the end of the doc | "Add today's decision to the decision log" |

## The gap: AI rewrites the whole shared doc

- AI updates the PRD in the morning. In the afternoon a teammate asks, "Where did my edit go?"
- Your review comments come loose from the text they were on.
- An image in the document is gone after the update. Nobody gets a warning.
- AI says "done", but the word it looked for was not in the document.
- A revision table gets a v1.2 row under v1.3, and nobody notices.

The faster AI updates a shared document, the more of other people's work it can remove.

## The fix: edit only the part you name

gdoc-surgical sends small, targeted edits through the Google Docs API. It never uploads a new copy of the document. The commands that target a position have a guard: set-cell and delete-row check the expected text, and insert-row and set-cell refuse a version that goes backwards. replace and linkify fail with exit code 2 when nothing matched. When a guard fails, nothing changes and the command exits with a non-zero code.

| Before | After |
| :--- | :--- |
| AI rewrites the whole document | AI changes only the part you name |
| Yesterday's edits from a teammate get overwritten | Other people's writing stays intact |
| AI says "done", but the text it looked for was not there | Zero matches is reported as a failure, exit code 2 |
| A version number goes backwards and nobody notices | Version numbers in a revision table can only go up |

## Who it is for

People who let an AI agent, such as Claude Code, keep shared Google Docs up to date: product managers with PRDs, team leads with SOPs, consultants with client proposals, anyone who keeps a revision table or a sign-off table. It also suits anyone who scripts changes to a live document that other people edit at the same time. You run a one-time setup in a terminal. After that, you ask your AI in plain words.
