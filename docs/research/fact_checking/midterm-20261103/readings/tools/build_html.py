"""Build the portable HTML reading guides from the Markdown beside this script's parent."""
from pathlib import Path
from urllib.parse import unquote
import base64
import html
import json
import re
import subprocess

from bs4 import BeautifulSoup

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent


def render(path, figures, css, script):
    is_index = path.name == 'README.md'
    content = path.read_text(encoding='utf-8')
    if is_index:
        # HTML readers follow the paper title; GitHub readers follow the Markdown title.
        content = re.sub(r'\[([^\]\n]+)\]\(([^\s()]+)\.md\) · \[HTML\]\(([^\s()]+)\.html\)',
                         r'[\1](\3.html) · [MD](\2.md)', content)
    else:
        content = content.replace('](README.md)', '](논문_읽기목록.html)')
    converted = subprocess.run(
        ['pandoc', '--from=markdown+raw_html', '--to=html5', '--wrap=none'],
        input=content, encoding='utf-8', capture_output=True, check=True,
    )
    page = BeautifulSoup(converted.stdout, 'html.parser')
    for img in page.select('img'):
        src = img['src']
        info = figures[src]
        figure = img.find_parent('figure') or img.parent
        figure.clear()
        caption = page.new_tag('figcaption')
        caption.string = info['caption'] + ' · 클릭하면 전체 페이지 확대'
        figure.append(caption)
        button = page.new_tag('button', attrs={'class':'scene', 'type':'button','aria-label':f"{info['page']}페이지 확대"})
        picture = page.new_tag('img',attrs={'alt':info['caption'], 'loading':'lazy'})
        picture['src'] = 'data:image/jpeg;base64,' + base64.b64encode((ROOT/unquote(src)).read_bytes()).decode()
        button.append(picture)
        if info['focus']:
            button.append(page.new_tag('i',attrs={'class':'focus','aria-hidden':'true','style':info['focus']}))
        figure.append(button)
    toc = ''.join(f'<a href="#{html.escape(node["id"])}">{html.escape(node.get_text())}</a>' for node in page.select('h2[id]'))
    title = html.escape(page.h1.get_text())
    output = f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{css}</style></head>
<body><header><a href="논문_읽기목록.html">NLP 5조 · 논문 읽기 목록</a><span>발표 32편 · 보충 4편</span></header>
<div class="layout"><aside><details open><summary>이 문서의 목차</summary><nav>{toc}</nav></details></aside><main>{page}</main></div>
<dialog id="zoom" aria-label="논문 원문 페이지"><div><button id="mark">영역 표시 전환</button><button id="size">원본 크기 전환</button><button id="close">닫기</button></div><div class="canvas"></div></dialog><script>{script}</script></body></html>'''
    target = ROOT/'논문_읽기목록.html' if is_index else path.with_suffix('.html')
    target.write_text(output,encoding='utf-8')


if __name__ == '__main__':
    figures = json.loads((TOOLS/'figures.json').read_text(encoding='utf-8'))
    css = (TOOLS/'reading.css').read_text(encoding='utf-8')
    js = (TOOLS/'reading.js').read_text(encoding='utf-8')
    for source in [ROOT/'README.md', *sorted(ROOT.glob('D*.md'))]:
        render(source, figures, css, js)
