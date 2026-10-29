"""Offline checks for the published reading guide, file links, and PDF integrity."""
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs/research/fact_checking/team_guide'


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links, self.classes = [], [], []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids.append(a['id'])
        if a.get('href'):
            self.links.append(a['href'])
        self.classes.extend(a.get('class', '').split())


def main():
    papers = json.loads((DOC / 'paper_library.json').read_text(encoding='utf-8'))['papers']
    assert len(papers) == len({p['id'] for p in papers}) == 111
    included = [p for p in papers if p['bundled']]
    assert len(included) == 90
    assert len(list((DOC / 'papers').glob('*.pdf'))) == len(included)
    for p in included:
        f = DOC / p['file']
        assert f.read_bytes().startswith(b'%PDF-'), p['id']
        assert hashlib.sha256(f.read_bytes()).hexdigest() == p['sha256'], p['id']
        assert p['license'] and p['license_source'] and not p['modified'], p['id']
    page = Page()
    page.feed((DOC / '팀공유.html').read_text(encoding='utf-8'))
    assert len(page.ids) == len(set(page.ids)), 'Duplicate HTML IDs'
    for name, count in [('task-card', 6), ('paper-card', 28), ('library-row', 111)]:
        assert page.classes.count(name) == count, name
    links = [(DOC / '팀공유.html', x) for x in page.links]
    for f in list(DOC.rglob('*.md')) + [ROOT / 'docs/documentation-guidelines.md']:
        text = f.read_text(encoding='utf-8')
        assert not re.search(r'(?:[CD]:[\\/]Users|D:[\\/]Vaults|file:///|sk-or-v1-[A-Za-z0-9]+|scholar\.liner\.com/\S*threads/)', text), f
        links.extend((f, x) for x in re.findall(r'\]\(([^\s)]+)\)', text))
    for f, link in links:
        parsed = urlsplit(link)
        if parsed.scheme or parsed.netloc:
            continue
        target = (f.parent / unquote(parsed.path)).resolve() if parsed.path else f
        assert target.is_relative_to(ROOT) and target.exists(), (f.name, link)
        if f.suffix == '.html' and not parsed.path and parsed.fragment:
            assert unquote(parsed.fragment) in page.ids, link
    print(json.dumps({'papers': 111, 'verified_PDFs': 90, 'source_link_only': 21,
                      'task_cards': 6, 'paper_introductions': 28,
                      'links_inspected': len(links), 'status': 'pass'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
