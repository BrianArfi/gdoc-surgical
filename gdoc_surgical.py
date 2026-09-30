#!/usr/bin/env python3
"""gdoc-surgical - edit a Google Doc in place, without overwriting it.

Most tools that write to a Google Doc replace the whole document. So an edit
somebody made between your last read and your write is not merged, it is
deleted, and nothing warns them. They find out when they reopen the document
and their paragraph is gone.

This edits the parts you name and leaves the rest of the document alone:
hand edits, comments, suggestions, images, sharing, revision history.

    gdoc_surgical.py auth        --credentials client_secret.json
    gdoc_surgical.py read        --id DOC_ID
    gdoc_surgical.py list-tables --id DOC_ID
    gdoc_surgical.py replace     --id DOC_ID --find "old" --with "new"
    gdoc_surgical.py linkify     --id DOC_ID --find "Q3 Roadmap" --url "https://..."
    gdoc_surgical.py append      --id DOC_ID --text "## Heading\\n- a bullet"
    gdoc_surgical.py insert-table --id DOC_ID --rows "A|B" --rows "1|2"
    gdoc_surgical.py insert-row  --id DOC_ID --table 0 --cells "v1.3|2026-09-22|Brian|Added X"
    gdoc_surgical.py set-cell    --id DOC_ID --table 0 --row 2 --col 1 --with "text" --expect "old"
    gdoc_surgical.py delete-row  --id DOC_ID --table 0 --row 3 --expect "text in that row"
    gdoc_surgical.py --version | --changelog [list|full]

Rules of engagement:
  - Always `read` or `list-tables` first. Every destructive command targets an
    index, and indexes move when somebody else edits the document.
  - `replace` hits EVERY occurrence. If the find-string is short or common,
    widen it until it is unique.
  - `delete-row` and `set-cell` want `--expect`: text that must already be in
    the target. A shifted index then fails loudly instead of editing the wrong
    row.

Requires: google-api-python-client, google-auth-oauthlib.
"""
import argparse
import json
import os
import re
import signal
import sys
import time

__version__ = '1.0.0'
HERE = os.path.dirname(os.path.abspath(__file__))
CHANGELOG_PATH = os.path.join(HERE, 'CHANGELOG.md')
CHANGELOG_URL = 'https://github.com/BrianArfi/gdoc-surgical/blob/main/CHANGELOG.md'

SCOPES = ['https://www.googleapis.com/auth/drive']
CONFIG_DIR = os.environ.get(
    'GDOC_SURGICAL_HOME',
    os.path.join(os.path.expanduser('~'), '.config', 'gdoc-surgical'))
TIMEOUT_SECONDS = int(os.environ.get('GDOC_SURGICAL_TIMEOUT', '180'))


def _timeout(signum, frame):
    print('[ERROR] Timed out after %d seconds' % TIMEOUT_SECONDS, file=sys.stderr)
    sys.exit(1)


if os.name != 'nt' and hasattr(signal, 'SIGALRM'):
    signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(TIMEOUT_SECONDS)


# --------------------------------------------------------------------------
# write verification
# --------------------------------------------------------------------------

def assert_write(result, operation, id_keys=('documentId', 'id', 'fileId')):
    """Confirm a write actually produced a document id before reporting success.

    An API response with no identifier in it is a failure, not a quiet success.
    Never returns on failure.
    """
    found = None
    if isinstance(result, dict):
        for key in id_keys:
            if result.get(key):
                found = result[key]
                break
    elif result:
        found = result
    if not found:
        print("[ERROR] '%s' returned no document id. Treat this as a FAILURE. "
              "Open the document and check before assuming the write happened."
              % operation, file=sys.stderr)
        sys.exit(1)
    return found


# --------------------------------------------------------------------------
# version guard
# --------------------------------------------------------------------------

VERSION_RE = re.compile(r'^v?(\d+)\.(\d+)$', re.I)


def parse_version(text):
    """(major, minor), or None when this is not a version token."""
    m = VERSION_RE.match((text or '').strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


def versions_in_column(rows):
    """Version tokens in the first column of a revision table, in order."""
    found = []
    for row in rows:
        if not row:
            continue
        v = parse_version(row[0])
        if v:
            found.append((v, row[0].strip()))
    return found


def check_new_version(new_version, existing_rows, where='the document'):
    """Raise ValueError unless new_version is strictly above every existing one.

    Returns None when there is nothing to check, so a table that is not a
    revision table passes straight through.

    This exists because a revision number that goes backwards is invisible: the
    row looks right, the document looks edited, and the reader trusts a version
    that is older than the text above it.
    """
    new = parse_version(new_version)
    if not new:
        return None
    existing = versions_in_column(existing_rows)
    if not existing:
        return None
    highest, highest_raw = max(existing, key=lambda pair: pair[0])
    if new > highest:
        return None
    dupes = [raw for v, raw in existing if v == new]
    detail = ('v%d.%d already appears in %s' % (new[0], new[1], where) if dupes else
              'v%d.%d is below %s, the highest version in %s'
              % (new[0], new[1], highest_raw, where))
    raise ValueError(
        'version regression refused: %s. Existing: %s. Re-read the document, '
        'then bump from its last row (next would be at least v%d.%d). Override '
        'with --allow-version-regression only when the duplicate is intentional.'
        % (detail, ', '.join(raw for _, raw in existing), highest[0], highest[1] + 1))


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------

def token_path(args):
    if getattr(args, 'token', None):
        return args.token
    if os.environ.get('GDOC_SURGICAL_TOKEN'):
        return os.environ['GDOC_SURGICAL_TOKEN']
    return os.path.join(CONFIG_DIR, '%s.json' % (getattr(args, 'account', None) or 'default'))


def authenticate(args):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    path = token_path(args)
    if not os.path.exists(path):
        print("[ERROR] No token at %s. Run:\n"
              "    %s auth --credentials client_secret.json --account %s"
              % (path, os.path.basename(sys.argv[0]),
                 getattr(args, 'account', None) or 'default'), file=sys.stderr)
        sys.exit(1)
    creds = Credentials.from_authorized_user_file(path, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(path, 'w', encoding='utf-8') as f:
                f.write(creds.to_json())
        else:
            print('[ERROR] Token at %s is invalid and cannot be refreshed. '
                  'Run the auth command again.' % path, file=sys.stderr)
            sys.exit(1)
    return creds


def cmd_auth(args):
    """One-time browser sign-in, storing a reusable token."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not os.path.exists(args.credentials):
        print('[ERROR] No OAuth client file at %s. Create one in Google Cloud '
              'Console under APIs and Services, Credentials, OAuth client ID, '
              'Desktop app, then download the JSON.' % args.credentials,
              file=sys.stderr)
        return 1
    flow = InstalledAppFlow.from_client_secrets_file(args.credentials, SCOPES)
    creds = flow.run_local_server(port=0)
    path = token_path(args)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(creds.to_json())
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    print('[OK] Token written to %s' % path)
    return 0


def docs_service(args):
    from googleapiclient.discovery import build
    return build('docs', 'v1', credentials=authenticate(args))


# --------------------------------------------------------------------------
# document structure
# --------------------------------------------------------------------------

def get_doc(docs, doc_id):
    return docs.documents().get(documentId=doc_id).execute()


def batch(docs, doc_id, requests):
    if not requests:
        print('[INFO] Nothing to do.')
        return None
    return docs.documents().batchUpdate(
        documentId=doc_id, body={'requests': requests}).execute()


def para_text(element):
    return ''.join(run.get('textRun', {}).get('content', '')
                   for run in element.get('paragraph', {}).get('elements', []))


def cell_text(cell):
    return ''.join(para_text(c) for c in cell.get('content', [])
                   if 'paragraph' in c).strip()


def walk_body(doc):
    """Yield (kind, element) for top-level body elements."""
    for el in doc.get('body', {}).get('content', []):
        if 'paragraph' in el:
            yield 'paragraph', el
        elif 'table' in el:
            yield 'table', el
        else:
            yield 'other', el


def tables_in(doc):
    return [el for kind, el in walk_body(doc) if kind == 'table']


def table_rows_text(table_element):
    return [[cell_text(c) for c in row['tableCells']]
            for row in table_element['table']['tableRows']]


def resolve_table(doc, index):
    tables = tables_in(doc)
    if index < 0 or index >= len(tables):
        print('[ERROR] Table #%d not found (this doc has %d). Run list-tables.'
              % (index, len(tables)), file=sys.stderr)
        sys.exit(1)
    return tables[index]


# --------------------------------------------------------------------------
# request builders, kept free of any API object so they can be tested offline
# --------------------------------------------------------------------------

HEADING_RE = re.compile(r'^(#{1,4})\s+(.*)$')
BULLET_RE = re.compile(r'^[-*]\s+(.*)$')


def build_append_requests(text, end_index):
    """Markdown-ish text to insert requests, starting at end_index.

    Headings and bullets are recognised; everything else becomes normal text.
    Each line is inserted at a cursor that advances by exactly the length
    inserted, so the styling range for line N is still correct after line N-1.
    """
    requests = []
    cursor = end_index
    for line in text.replace('\\n', '\n').split('\n'):
        heading = HEADING_RE.match(line)
        bullet = BULLET_RE.match(line)
        content = (heading.group(2) if heading else
                   bullet.group(1) if bullet else line) + '\n'
        requests.append({'insertText': {'location': {'index': cursor},
                                        'text': content}})
        span = {'startIndex': cursor, 'endIndex': cursor + len(content)}
        if heading:
            requests.append({'updateParagraphStyle': {
                'range': span,
                'paragraphStyle': {'namedStyleType': 'HEADING_%d' % len(heading.group(1))},
                'fields': 'namedStyleType'}})
        elif bullet:
            requests.append({'createParagraphBullets': {
                'range': span, 'bulletPreset': 'BULLET_DISC_CIRCLE_SQUARE'}})
        else:
            requests.append({'updateParagraphStyle': {
                'range': span, 'paragraphStyle': {'namedStyleType': 'NORMAL_TEXT'},
                'fields': 'namedStyleType'}})
        cursor += len(content)
    return requests


def build_linkify_requests(content, find, url):
    """Hyperlink every occurrence of `find`, including inside table cells.

    updateTextStyle never changes text length, so every index stays valid
    against the document as read, whatever order the requests run in.
    """
    requests = []

    def walk(elements):
        for el in elements:
            if 'paragraph' in el:
                text = para_text(el)
                start = 0
                while True:
                    idx = text.find(find, start)
                    if idx == -1:
                        break
                    abs_start = el['startIndex'] + idx
                    requests.append({'updateTextStyle': {
                        'range': {'startIndex': abs_start,
                                  'endIndex': abs_start + len(find)},
                        'textStyle': {'link': {'url': url}},
                        'fields': 'link'}})
                    start = idx + len(find)
            elif 'table' in el:
                for row in el['table']['tableRows']:
                    for cell in row['tableCells']:
                        walk(cell.get('content', []))

    walk(content)
    return requests


def build_cell_fill_requests(table, rows):
    """Fill a freshly created table, bottom-right to top-left.

    Every insertion shifts the indexes after it, so filling in reverse order
    means a target is never moved before it is written.
    """
    requests = []
    for r_i in range(len(rows) - 1, -1, -1):
        cells = rows[r_i]
        for c_i in range(len(cells) - 1, -1, -1):
            value = cells[c_i].strip()
            if not value:
                continue
            cell = table['tableRows'][r_i]['tableCells'][c_i]
            requests.append({'insertText': {
                'location': {'index': cell['startIndex'] + 1}, 'text': value}})
    return requests


def doc_url(doc_id):
    return 'https://docs.google.com/document/d/%s/edit' % doc_id


def guard_version(args, table_element, new_cells):
    if getattr(args, 'allow_version_regression', False) or not new_cells:
        return
    try:
        check_new_version(new_cells[0], table_rows_text(table_element),
                          where='this document')
    except ValueError as exc:
        print('[BLOCKED] %s' % exc, file=sys.stderr)
        sys.exit(1)


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

STYLE_PREFIX = {'HEADING_1': '# ', 'HEADING_2': '## ', 'HEADING_3': '### ',
                'HEADING_4': '#### ', 'TITLE': '=== '}


def cmd_read(docs, args):
    doc = get_doc(docs, args.id)
    print('# %s  (docId: %s)\n' % (doc.get('title'), args.id))
    t_idx = 0
    for kind, el in walk_body(doc):
        if kind == 'paragraph':
            text = para_text(el).rstrip('\n')
            if text.strip():
                style = el['paragraph'].get('paragraphStyle', {}).get('namedStyleType', '')
                print('[%d-%d] %s%s' % (el['startIndex'], el['endIndex'],
                                        STYLE_PREFIX.get(style, ''), text))
        elif kind == 'table':
            print('[%d-%d] <TABLE #%d: %sx%s>'
                  % (el['startIndex'], el['endIndex'], t_idx,
                     el['table'].get('rows'), el['table'].get('columns')))
            t_idx += 1
    return 0


def cmd_list_tables(docs, args):
    doc = get_doc(docs, args.id)
    tables = tables_in(doc)
    for i, el in enumerate(tables):
        rows = el['table'].get('tableRows') or []
        header = [cell_text(c) for c in rows[0].get('tableCells', [])] if rows else []
        print('TABLE #%d: %sx%s @ startIndex %d | header: %s'
              % (i, el['table'].get('rows'), el['table'].get('columns'),
                 el['startIndex'], ' | '.join(header)))
    if not tables:
        print('[INFO] No tables in this doc.')
    return 0


def cmd_replace(docs, args):
    doc = get_doc(docs, args.id)
    body = ''.join(para_text(el) for kind, el in walk_body(doc) if kind == 'paragraph')
    flags = 0 if args.match_case else re.IGNORECASE
    n = len(re.findall(re.escape(args.find), body, flags))
    print("[INFO] '%s' found %dx in body paragraphs. Table cells are not counted "
          'here, and the replace does hit those too.' % (args.find, n))
    result = batch(docs, args.id, [{'replaceAllText': {
        'containsText': {'text': args.find, 'matchCase': bool(args.match_case)},
        'replaceText': getattr(args, 'with')}}])
    assert_write(result, 'replace')
    changed = result['replies'][0].get('replaceAllText', {}).get('occurrencesChanged', 0)
    print('[OK] Replaced %d occurrence(s). Doc: %s' % (changed, doc_url(args.id)))
    if changed == 0:
        print('[WARN] Nothing replaced. Check the exact wording and case with `read`.')
        return 2
    return 0


def cmd_linkify(docs, args):
    doc = get_doc(docs, args.id)
    requests = build_linkify_requests(doc['body']['content'], args.find, args.url)
    if not requests:
        print('[WARN] %r is not in this doc, nothing linked.' % args.find)
        return 2
    assert_write(batch(docs, args.id, requests), 'linkify')
    print('[OK] Linked %d occurrence(s) of %r to %s. Doc: %s'
          % (len(requests), args.find, args.url, doc_url(args.id)))
    return 0


def cmd_append(docs, args):
    doc = get_doc(docs, args.id)
    end_index = doc['body']['content'][-1]['endIndex'] - 1  # before the final newline
    requests = build_append_requests(args.text, end_index)
    assert_write(batch(docs, args.id, requests), 'append')
    print('[OK] Appended %d line(s). Doc: %s'
          % (len(args.text.replace('\\n', '\n').split('\n')), doc_url(args.id)))
    return 0


def cmd_insert_table(docs, args):
    rows = [r.split('|') for r in args.rows]
    n_rows, n_cols = len(rows), max(len(r) for r in rows)
    assert_write(batch(docs, args.id, [{'insertTable': {
        'endOfSegmentLocation': {}, 'rows': n_rows, 'columns': n_cols}}]),
        'insert-table')

    time.sleep(1)  # the new table is not always in the next read immediately
    doc = get_doc(docs, args.id)
    tables = tables_in(doc)
    batch(docs, args.id, build_cell_fill_requests(tables[-1]['table'], rows))
    print('[OK] Table %dx%d appended as table #%d. Doc: %s'
          % (n_rows, n_cols, len(tables) - 1, doc_url(args.id)))
    return 0


def cmd_insert_row(docs, args):
    doc = get_doc(docs, args.id)
    table_el = resolve_table(doc, args.table)
    n_rows, n_cols = table_el['table']['rows'], table_el['table']['columns']
    cells = args.cells.split('|')
    guard_version(args, table_el, cells)
    row_idx = args.row if args.row >= 0 else n_rows - 1

    # The row insert is the write that matters. Filling it can legitimately be a
    # no-op when every value is blank, so verify here rather than on the fill.
    assert_write(batch(docs, args.id, [{'insertTableRow': {
        'tableCellLocation': {
            'tableStartLocation': {'index': table_el['startIndex']},
            'rowIndex': row_idx, 'columnIndex': 0},
        'insertBelow': True}}]), 'insert-row')

    if len(cells) > n_cols:
        print('[WARN] %d cell values for %d columns, the extra values are dropped.'
              % (len(cells), n_cols))
        cells = cells[:n_cols]

    time.sleep(1)
    doc = get_doc(docs, args.id)
    new_row = tables_in(doc)[args.table]['table']['tableRows'][row_idx + 1]
    requests = []
    for cell, value in reversed(list(zip(new_row['tableCells'], cells))):
        if value.strip():
            requests.append({'insertText': {
                'location': {'index': cell['startIndex'] + 1}, 'text': value.strip()}})
    batch(docs, args.id, requests)
    print('[OK] Row inserted into table #%d at row %d with %d cell(s). Doc: %s'
          % (args.table, row_idx + 1, len(cells), doc_url(args.id)))
    return 0


def cmd_set_cell(docs, args):
    """Replace the text of ONE cell, addressed by coordinate.

    `replace` is global, so it cannot safely target a cell whose whole content is
    a common string: a version cell reading "1.4" would rewrite every "1.4" in
    the document.
    """
    doc = get_doc(docs, args.id)
    table_el = resolve_table(doc, args.table)
    table = table_el['table']
    if args.row < 0 or args.row >= table['rows']:
        print('[ERROR] Row %d out of range, table #%d has %d rows.'
              % (args.row, args.table, table['rows']), file=sys.stderr)
        return 1
    if args.col < 0 or args.col >= table['columns']:
        print('[ERROR] Column %d out of range, table #%d has %d columns.'
              % (args.col, args.table, table['columns']), file=sys.stderr)
        return 1

    cell = table['tableRows'][args.row]['tableCells'][args.col]
    current = cell_text(cell)
    value = getattr(args, 'with')
    if args.col == 0:
        guard_version(args, table_el, [value or ''])
    if args.expect is not None and args.expect not in current:
        print('[ERROR] Cell (%d,%d) of table #%d does not contain the --expect text.\n'
              '        expected: %r\n        cell is:  %r\n        Nothing changed.'
              % (args.row, args.col, args.table, args.expect, current[:300]),
              file=sys.stderr)
        return 2

    text_start, text_end = cell['startIndex'] + 1, cell['endIndex'] - 1
    requests = []
    if text_end > text_start:
        requests.append({'deleteContentRange': {
            'range': {'startIndex': text_start, 'endIndex': text_end}}})
    if value:
        requests.append({'insertText': {'location': {'index': text_start},
                                        'text': value}})
    assert_write(batch(docs, args.id, requests), 'set-cell')
    print('[OK] Table #%d cell (%d,%d): %r -> %r. Doc: %s'
          % (args.table, args.row, args.col, current[:60], value[:60], doc_url(args.id)))
    return 0


def cmd_delete_row(docs, args):
    doc = get_doc(docs, args.id)
    table_el = resolve_table(doc, args.table)
    table = table_el['table']
    if args.row < 0 or args.row >= table['rows']:
        print('[ERROR] Row %d out of range, table #%d has %d rows.'
              % (args.row, args.table, table['rows']), file=sys.stderr)
        return 1

    row_text = ' | '.join(cell_text(c)
                          for c in table['tableRows'][args.row].get('tableCells', []))
    # Deleting a row cannot be undone from here, and row indexes move under any
    # concurrent edit. So the caller names text they expect to find in the row,
    # and a shifted index fails loudly instead of deleting somebody else's work.
    if args.expect not in row_text:
        print('[ERROR] Row %d of table #%d does not contain the --expect text.\n'
              '        expected: %r\n        row is:   %r\n'
              '        Nothing deleted. Re-run list-tables and check the index.'
              % (args.row, args.table, args.expect, row_text[:300]), file=sys.stderr)
        return 2

    print('[INFO] Deleting table #%d row %d: %s' % (args.table, args.row, row_text[:200]))
    assert_write(batch(docs, args.id, [{'deleteTableRow': {
        'tableCellLocation': {
            'tableStartLocation': {'index': table_el['startIndex']},
            'rowIndex': args.row, 'columnIndex': 0}}}]), 'delete-row')
    print('[OK] Row %d deleted from table #%d (%d -> %d rows). Doc: %s'
          % (args.row, args.table, table['rows'], table['rows'] - 1, doc_url(args.id)))
    return 0


# --------------------------------------------------------------------------

COMMANDS = {
    'read': cmd_read, 'list-tables': cmd_list_tables, 'replace': cmd_replace,
    'linkify': cmd_linkify, 'append': cmd_append, 'insert-table': cmd_insert_table,
    'insert-row': cmd_insert_row, 'set-cell': cmd_set_cell, 'delete-row': cmd_delete_row,
}


def changelog_text(mode='list'):
    """The bundled CHANGELOG.md: a list of version headings, or the full text."""
    try:
        with open(CHANGELOG_PATH, encoding='utf-8') as f:
            text = f.read()
    except OSError:
        return ('gdoc-surgical %s. CHANGELOG.md is not next to this file; '
                'read it at %s' % (__version__, CHANGELOG_URL))
    if mode == 'full':
        return text.rstrip('\n')
    heads = [line[3:].strip() for line in text.splitlines() if line.startswith('## [')]
    return '\n'.join(['gdoc-surgical %s' % __version__] + heads +
                     ['', 'Full text: --changelog full'])


def build_parser():
    p = argparse.ArgumentParser(
        prog='gdoc_surgical', description='Surgical in-place Google Doc edits',
        epilog='Always read the document before you write to it.')
    p.add_argument('--version', action='version', version='gdoc-surgical ' + __version__)
    p.add_argument('--changelog', nargs='?', const='list', choices=['list', 'full'],
                   help='print the bundled changelog: version list, or full text')
    p.add_argument('command', choices=['auth'] + sorted(COMMANDS))
    p.add_argument('--id', help='Google Doc id, the long string in the doc URL')
    p.add_argument('--account', default='default',
                   help='named token profile under ~/.config/gdoc-surgical')
    p.add_argument('--token', help='path to a token file, overrides --account')
    p.add_argument('--credentials', default='client_secret.json',
                   help='auth: OAuth client JSON from Google Cloud Console')
    p.add_argument('--find', help='replace, linkify: exact text to find')
    p.add_argument('--with', dest='with', help='replace, set-cell: the new text')
    p.add_argument('--url', help='linkify: URL to link --find to')
    p.add_argument('--match-case', action='store_true', help='replace: case sensitive')
    p.add_argument('--text', help=r'append: text to add, \n for newlines, # for a '
                                  'heading, - for a bullet')
    p.add_argument('--table', type=int, default=0, help='table index, see list-tables')
    p.add_argument('--row', type=int, default=-1,
                   help='insert-row: insert below this 0-based row (-1 = last). '
                        'set-cell, delete-row: the 0-based target row')
    p.add_argument('--col', type=int, default=0, help='set-cell: 0-based column')
    p.add_argument('--cells', help='insert-row: pipe-separated values "A|B|C"')
    p.add_argument('--rows', action='append',
                   help='insert-table: one pipe-separated row per flag, repeated')
    p.add_argument('--expect',
                   help='set-cell, delete-row: text that must already be in the '
                        'target before it is changed')
    p.add_argument('--allow-version-regression', action='store_true',
                   help='permit a revision number at or below one already present')
    return p


def validate(parser, args):
    need = {
        'replace': ('--find and --with', lambda a: a.find and getattr(a, 'with') is not None),
        'linkify': ('--find and --url', lambda a: a.find and a.url),
        'append': ('--text', lambda a: a.text),
        'insert-row': ('--cells', lambda a: a.cells),
        'insert-table': ('at least one --rows "a|b|c"', lambda a: a.rows),
        'set-cell': ('--with and an explicit --row',
                     lambda a: getattr(a, 'with') is not None and a.row >= 0),
        'delete-row': ('an explicit --row and --expect',
                       lambda a: a.row >= 0 and a.expect),
    }
    if args.command != 'auth' and not args.id:
        parser.error('%s requires --id' % args.command)
    if args.command in need:
        label, ok = need[args.command]
        if not ok(args):
            parser.error('%s requires %s' % (args.command, label))


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    if '--changelog' in argv:
        i = argv.index('--changelog')
        mode = argv[i + 1] if i + 1 < len(argv) and argv[i + 1] in ('list', 'full') else 'list'
        print(changelog_text(mode))
        return 0
    args = parser.parse_args(argv)
    validate(parser, args)
    if args.command == 'auth':
        return cmd_auth(args)
    return COMMANDS[args.command](docs_service(args), args)


if __name__ == '__main__':
    sys.exit(main() or 0)
