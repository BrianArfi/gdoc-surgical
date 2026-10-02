# Changelog

All notable changes to gdoc-surgical are recorded here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/).

`python3 gdoc_surgical.py --changelog` lists the versions below;
`--changelog full` prints this file.

## [Unreleased]
<!-- source: branch feat/changelog, this change set. -->

### Added
- `--version` prints the version, and `--changelog` prints this changelog (a list of versions, or `full` for the whole file).
- This `CHANGELOG.md`, backfilled from the git history.
- `read` prints the rows of each table under its `<TABLE #n>` line, so table text can be checked before a write.

### Changed
- README: a concrete problem scenario, who it is for and not for, a Before / After table, an animated hero, before/after and how-it-works GIFs, and a second real recording that shows the guards refusing (`docs/guards.gif`). Sources and one-command re-render scripts are in `docs/src/`.
- `replace` counts matches in table cells too before it writes, and reports the split: `Found 'X' 3 time(s): 1 in paragraphs, 2 in table cells.`

## [1.0.0] - 2026-09-22
<!-- source: git commit 29c8b59 "gdoc-surgical: edit a Google Doc in place instead of overwriting it" (2026-09-22 13:18 +0700), the initial and only commit. No git tag or GitHub release exists; 1.0.0 labels this first public cut. -->

### Added
- Targeted, in-place edits to a Google Doc, so hand edits, comments, images and sharing survive: `read`, `list-tables`, `replace`, `linkify`, `append`, `insert-table`, `insert-row`, `set-cell` and `delete-row`.
- `auth` command and named token profiles (`--account`, `--token`, `GDOC_SURGICAL_TOKEN`).
- Guards against a shifted index: `--expect` on `delete-row` and `set-cell`, and an occurrence count before `replace` writes (exit 2 on zero matches).
- A revision table cannot go backwards: a version at or below one already present is refused unless `--allow-version-regression` is passed.
- A write is reported as success only once a document id comes back.
- `SKILL.md` for agent harnesses, offline tests in `tests/test_gdoc_surgical.py`, MIT license.

[Unreleased]: https://github.com/BrianArfi/gdoc-surgical/compare/29c8b59...feat/changelog
[1.0.0]: https://github.com/BrianArfi/gdoc-surgical/commit/29c8b59
