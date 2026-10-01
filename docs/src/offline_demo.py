#!/usr/bin/env python3
"""Run the real gdoc_surgical commands against an in-memory sample doc.

No Google account and no network. The fake service answers documents().get
and documents().batchUpdate (replaceAllText) the way the Docs API does, so
the printed lines are the tool's real output. Used to record docs/demo.gif.

    python docs/src/offline_demo.py read --id DEMO_DOC
    python docs/src/offline_demo.py replace --id DEMO_DOC --find "Q3 2026" --with "Q4 2026"

The sample doc is persisted to a temp JSON file between calls, so a replace
followed by a read shows the change.
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..'))
import gdoc_surgical as gs  # noqa: E402

STATE = os.path.join(tempfile.gettempdir(), 'gdoc_surgical_demo_doc.json')


def paragraph(text, start, style=None):
    el = {'startIndex': start, 'endIndex': start + len(text),
          'paragraph': {'elements': [{'textRun': {'content': text}}]}}
    if style:
        el['paragraph']['paragraphStyle'] = {'namedStyleType': style}
    return el


def cell(text, start):
    return {'startIndex': start, 'endIndex': start + len(text) + 2,
            'content': [paragraph(text, start + 1)]}


def sample_doc():
    """A small launch plan: heading, three lines, a timeline table."""
    lines = [('Launch plan', 'HEADING_1'),
             ('Target: public launch in Q3 2026.\n', None),
             ('Owner: Sam. Reviewers: Dina, Leo.\n', None),
             ('Risk: payment partner sign-off may slip two weeks. (added by Dina)\n', None)]
    content, idx = [], 1
    for text, style in lines:
        text = text if text.endswith('\n') else text + '\n'
        content.append(paragraph(text, idx, style))
        idx += len(text)
    rows = [['Milestone', 'Target'], ['Beta', 'Q3 2026'], ['Launch', 'Q3 2026']]
    start, table_rows = idx, []
    idx += 1
    for r in rows:
        cells = []
        for value in r:
            cells.append(cell(value, idx))
            idx += len(value) + 2
        table_rows.append({'tableCells': cells})
    content.append({'startIndex': start, 'endIndex': idx,
                    'table': {'rows': 3, 'columns': 2, 'tableRows': table_rows}})
    content.append(paragraph('\n', idx))
    return {'title': 'Launch plan (sample)', 'body': {'content': content}}


def load():
    if os.path.exists(STATE):
        with open(STATE, encoding='utf-8') as fh:
            return json.load(fh)
    return sample_doc()


def save(doc):
    with open(STATE, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh)


def runs(doc):
    for el in doc['body']['content']:
        if 'paragraph' in el:
            yield from el['paragraph']['elements']
        elif 'table' in el:
            for row in el['table']['tableRows']:
                for c in row['tableCells']:
                    for p in c['content']:
                        yield from p['paragraph']['elements']


class _Call:
    def __init__(self, fn):
        self.fn = fn

    def execute(self):
        return self.fn()


class FakeDocuments:
    def get(self, documentId):
        return _Call(load)

    def batchUpdate(self, documentId, body):
        def run():
            doc, replies = load(), []
            for req in body['requests']:
                r = req['replaceAllText']
                find, new = r['containsText']['text'], r['replaceText']
                n = 0
                for run_ in runs(doc):
                    tr = run_['textRun']
                    n += tr['content'].count(find)
                    tr['content'] = tr['content'].replace(find, new)
                replies.append({'replaceAllText': {'occurrencesChanged': n}})
            save(doc)
            return {'documentId': documentId, 'replies': replies}
        return _Call(run)


class FakeService:
    def documents(self):
        return FakeDocuments()


if __name__ == '__main__':
    if sys.argv[1:] == ['reset']:
        if os.path.exists(STATE):
            os.remove(STATE)
        sys.exit(0)
    gs.docs_service = lambda args: FakeService()
    sys.exit(gs.main() or 0)
