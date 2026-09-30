#!/usr/bin/env python3
"""Offline tests for gdoc-surgical.

Everything here runs without the Google APIs: the request builders and the
guards are pure functions over plain dicts, which is why they are pure
functions. A fake document stands in for a real one.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import gdoc_surgical as gs  # noqa: E402

FAILURES = []


def check(label, condition, detail=''):
    if condition:
        print('  ok   %s' % label)
    else:
        print('  FAIL %s %s' % (label, detail))
        FAILURES.append(label)


def paragraph(text, start):
    return {'startIndex': start, 'endIndex': start + len(text),
            'paragraph': {'elements': [{'textRun': {'content': text}}]}}


def cell(text, start):
    return {'startIndex': start, 'endIndex': start + len(text) + 2,
            'content': [paragraph(text, start + 1)]}


def fake_doc():
    """Two paragraphs and a 3x2 revision table, with plausible indexes."""
    p1 = paragraph('The Q3 Roadmap is here.\n', 1)
    p2 = paragraph('See the Q3 Roadmap section.\n', 25)
    rows = [['v1.0', 'first cut'], ['v1.1', 'fixed the Q3 Roadmap link'],
            ['v1.2', 'third']]
    idx = 60
    table_rows = []
    for r in rows:
        cells = []
        for value in r:
            cells.append(cell(value, idx))
            idx += len(value) + 2
        table_rows.append({'tableCells': cells})
    table = {'startIndex': 55, 'endIndex': idx,
             'table': {'rows': 3, 'columns': 2, 'tableRows': table_rows}}
    return {'title': 'Test doc',
            'body': {'content': [p1, p2, table,
                                 paragraph('\n', idx)]}}


def main():
    print('version guard')
    rows = [['v1.0', 'x'], ['v1.1', 'y'], ['v1.2', 'z']]
    check('a higher version passes', gs.check_new_version('v1.3', rows) is None)
    for bad in ('v1.2', 'v1.1', 'v0.9'):
        try:
            gs.check_new_version(bad, rows)
            check('%s is refused' % bad, False, 'no error raised')
        except ValueError as exc:
            check('%s is refused' % bad, True)
            if bad == 'v1.2':
                check('says it is a duplicate', 'already appears' in str(exc), str(exc))
            if bad == 'v0.9':
                check('says it is below the highest', 'is below' in str(exc), str(exc))
    check('a non-version cell passes through',
          gs.check_new_version('Draft', rows) is None)
    check('an empty table passes through', gs.check_new_version('v1.0', []) is None)
    check('a table with no versions passes through',
          gs.check_new_version('v1.0', [['Author', 'Notes']]) is None)
    check('bare numbers parse as versions', gs.parse_version('2.4') == (2, 4))
    check('major bumps beat minors',
          gs.check_new_version('v2.0', [['v1.99', 'x']]) is None)

    print('append builder')
    reqs = gs.build_append_requests('## Heading\\n- a bullet\\nplain line', 100)
    inserts = [r for r in reqs if 'insertText' in r]
    check('one insert per line', len(inserts) == 3, str(len(inserts)))
    check('the escaped newline is honoured',
          inserts[0]['insertText']['text'] == 'Heading\n',
          inserts[0]['insertText']['text'])
    check('the heading marker is stripped from the text',
          '#' not in inserts[0]['insertText']['text'])
    check('the heading level is applied',
          any(r.get('updateParagraphStyle', {}).get('paragraphStyle', {})
              .get('namedStyleType') == 'HEADING_2' for r in reqs))
    check('the bullet marker is stripped',
          inserts[1]['insertText']['text'] == 'a bullet\n',
          inserts[1]['insertText']['text'])
    check('the bullet becomes a list item',
          any('createParagraphBullets' in r for r in reqs))
    check('plain text stays normal',
          any(r.get('updateParagraphStyle', {}).get('paragraphStyle', {})
              .get('namedStyleType') == 'NORMAL_TEXT' for r in reqs))
    # The cursor must advance by exactly what was inserted, or line 2 styles
    # line 1's text.
    positions = [r['insertText']['location']['index'] for r in inserts]
    check('the cursor advances by the inserted length',
          positions == [100, 108, 117], str(positions))

    print('linkify builder')
    doc = fake_doc()
    reqs = gs.build_linkify_requests(doc['body']['content'], 'Q3 Roadmap', 'https://x')
    check('finds every occurrence, table cells included', len(reqs) == 3, str(len(reqs)))
    check('every request only touches the link',
          all(r['updateTextStyle']['fields'] == 'link' for r in reqs))
    widths = {r['updateTextStyle']['range']['endIndex']
              - r['updateTextStyle']['range']['startIndex'] for r in reqs}
    check('every range is exactly the match width', widths == {len('Q3 Roadmap')},
          str(widths))
    check('a phrase that is not there yields nothing',
          gs.build_linkify_requests(doc['body']['content'], 'nope', 'https://x') == [])

    print('table fill builder')
    table = {'tableRows': [
        {'tableCells': [cell('', 10), cell('', 20)]},
        {'tableCells': [cell('', 30), cell('', 40)]}]}
    reqs = gs.build_cell_fill_requests(table, [['a', 'b'], ['c', '']])
    check('blank cells are skipped', len(reqs) == 3, str(len(reqs)))
    order = [r['insertText']['location']['index'] for r in reqs]
    check('fills bottom-right first so indexes never shift under it',
          order == sorted(order, reverse=True), str(order))

    print('structure helpers')
    doc = fake_doc()
    check('finds the table', len(gs.tables_in(doc)) == 1)
    check('reads the table as text',
          gs.table_rows_text(gs.tables_in(doc)[0])[0] == ['v1.0', 'first cut'],
          str(gs.table_rows_text(gs.tables_in(doc)[0])[0]))
    check('builds the doc url',
          gs.doc_url('abc') == 'https://docs.google.com/document/d/abc/edit')

    print('write verification')
    for bad in (None, {}, '', {'replies': []}):
        try:
            gs.assert_write(bad, 'test')
            check('%r is treated as failure' % (bad,), False, 'returned instead')
        except SystemExit as exc:
            check('%r is treated as failure' % (bad,), exc.code == 1)
    check('a documentId counts as success',
          gs.assert_write({'documentId': 'abc'}, 'test') == 'abc')

    print('argument validation')
    parser = gs.build_parser()
    for argv, why in [
        (['delete-row', '--id', 'x', '--table', '0', '--row', '2'], 'no --expect'),
        (['delete-row', '--id', 'x', '--expect', 'y'], 'no explicit --row'),
        (['set-cell', '--id', 'x', '--with', 'y'], 'no explicit --row'),
        (['replace', '--id', 'x', '--find', 'y'], 'no --with'),
        (['linkify', '--id', 'x', '--find', 'y'], 'no --url'),
        (['insert-row', '--id', 'x'], 'no --cells'),
        (['read'], 'no --id'),
    ]:
        try:
            gs.validate(parser, parser.parse_args(argv))
            check('refuses %s' % why, False, 'accepted %s' % argv)
        except SystemExit:
            check('refuses %s' % why, True)

    ok = ['set-cell', '--id', 'x', '--row', '0', '--with', '']
    try:
        gs.validate(parser, parser.parse_args(ok))
        check('an empty --with is a real value, not a missing one', True)
    except SystemExit:
        check('an empty --with is a real value, not a missing one', False)

    print('token resolution')
    args = parser.parse_args(['read', '--id', 'x', '--account', 'work'])
    check('a named account maps to its own token file',
          gs.token_path(args).endswith(os.path.join('gdoc-surgical', 'work.json')),
          gs.token_path(args))
    args = parser.parse_args(['read', '--id', 'x', '--token', '/tmp/t.json'])
    check('--token wins over --account', gs.token_path(args) == '/tmp/t.json')

    print('version and changelog')
    heads = [l for l in open(gs.CHANGELOG_PATH, encoding='utf-8').read().splitlines()
             if l.startswith('## [') and not l.startswith('## [Unreleased]')]
    check('newest CHANGELOG release matches __version__',
          heads and heads[0].startswith('## [%s]' % gs.__version__), heads[:1])
    listing = gs.changelog_text('list')
    check('--changelog lists every version heading', '1.0.0' in listing, listing)
    check('--changelog full prints the file',
          gs.changelog_text('full').startswith('# Changelog'))

    print()
    if FAILURES:
        print('%d failure(s): %s' % (len(FAILURES), ', '.join(FAILURES)))
        return 1
    print('all gdoc-surgical tests passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
