"""Build offline team guide from Markdown. Requires Markdown==3.11.2.

Use --public-dir PATH to export with official paper links instead of local PDFs.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
import markdown
from lxml import html as lh
from lxml import etree

esc=html.escape
papers=json.loads((ROOT/'paper_library.json').read_text(encoding='utf-8'))['papers']
by_id={p['id']:p for p in papers}
cards=json.loads((ROOT/'tools'/'team_paper_cards.json').read_text(encoding='utf-8'))
task_names={'T1':'수치 검증','T2':'복합 주장','T3':'시점 검증','T4':'근거 탐색','T5':'왜곡 위치','T6':'후속 업무','2x2':'진짜·가짜 2×2'}
groups={1:'주장 선별·분해',2:'대조 평가·편향',3:'검색·재순위화',4:'Agent·적응 제어',5:'시간·수치·표',6:'한국어·다국어',7:'평가·인용·보류',8:'충돌·오염·누출',9:'멀티모달',
 'survey':'분야 개관','agent':'Agent·적응 제어','benchmark':'벤치마크·데이터','decomposition':'주장 선별·분해','evaluation':'평가·인용','korean':'한국어·다국어','multimodal':'멀티모달','retrieval':'검색·재순위화','temporal_numeric':'시간·수치·표','DOCX':'기반·확장 방법'}

def pdf_url(p):
    if p.get('bundled'):
        return 'https://raw.githubusercontent.com/CJI0718/uos-nlp-2026-team5/main/docs/research/fact_checking/team_guide/'+quote(p['file'],safe='/')
    return p.get('download_url')

def md_pdf_link(p):
    url=pdf_url(p)
    return (' · [PDF]('+url+')') if url else ''

def paper_links(p,public=False):
    source=p.get('corrected_url',p['url'])
    links=f'<a href="{esc(source,quote=True)}" target="_blank" rel="noreferrer">공식 서지·원문 ↗</a>'
    url=pdf_url(p)
    if url:
        label='저장소 PDF' if p.get('bundled') else '원출처 PDF'
        links=f'<a href="{esc(url,quote=True)}" target="_blank" rel="noreferrer">{label} · {p["pages"]}쪽 ↗</a>'+links
    return '<div class="paper-links">'+links+'</div>'

def guide_md(public=False):
    lines=['### 먼저 읽을 공통 6편','','AVeriTeC → ReAct → Fathom → FIRE → Sufficient Context → ALCE. **데이터·실행·기준선·적응·오류·평가** 순으로 프로젝트 한 바퀴를 읽는다.','','### 관심 태스크에서 고르는 논문','']
    for c in cards:
        p=by_id[c['id']]
        lines += [f"#### {c['id']} · {c['short']} — {c['hook']}",'',f"**{p['title']}** · {c['kind']} · {', '.join(c['tasks'])}",'',
          f"- **논의:** {c['question']}",f"- **구조:** {c['architecture']}",f"- **논문 결과:** {c['result']}",f"- **우리 적용:** {c['meaning']}",f"- **읽을 곳:** {c['read']}",f"- **읽고 남길 것:** {c['take']}",'',
          f"[공식 서지·원문]({p.get('corrected_url',p['url'])})"+md_pdf_link(p),'']
    return '\n'.join(lines)

def library_md(public=False):
    lines=['<details>','<summary>전체 111편 목록 펼치기</summary>','','| ID | 제목 | 원문 |','|---|---|---|']
    for p in papers:
        link=f"[서지·원문]({p.get('corrected_url',p['url'])})"
        link+=md_pdf_link(p)
        lines.append(f"| {p['id']} | {p['title']} | {link} |")
    return '\n'.join(lines+['','</details>'])

def set_block(text,name,value):
    block=f'<!-- {name}_BEGIN -->\n{value}\n<!-- {name}_END -->'
    pattern=rf'<!-- {name}_BEGIN -->.*?<!-- {name}_END -->'
    if re.search(pattern,text,flags=re.S):return re.sub(pattern,lambda _:block,text,flags=re.S)
    assert f'<!-- {name} -->' in text,name
    return text.replace(f'<!-- {name} -->',block)

def card_html(public=False):
    buttons=''.join(f'<button class="filter-btn" data-reading-filter="{k}" aria-pressed="false">{k} {v}</button>' for k,v in task_names.items())
    out=['<div class="reading-intro"><h3>공통 6편으로 프로젝트 한 바퀴 읽기</h3><p>데이터 → 실행 → 기준선 → 적응 → 오류 → 평가. 여섯 소개를 훑고, 관심 태스크에 맞춰 두 편을 골라 원문의 그림과 표를 읽자.</p></div>',
      '<div class="reading-filters" role="group" aria-label="읽을 논문 범위"><button class="filter-btn selected" data-reading-filter="core" aria-pressed="true">공통 6편</button>'+buttons+'<button class="filter-btn" data-reading-filter="all" aria-pressed="false">소개 28편 전체</button></div><p class="count" id="reading-count" aria-live="polite">6편 표시</p><div class="paper-grid">']
    for c in cards:
        p=by_id[c['id']];cid=c['id'];hidden='' if c.get('core') else ' hidden'
        out.append(f'''<article class="paper-card" id="intro-{cid}" data-tags="{' '.join(c['tasks'])}" data-core="{str(bool(c.get('core'))).lower()}"{hidden}>
<div class="card-meta"><span>{cid} · {esc(c['kind'])}</span><span>{esc(c['short'])}</span></div>
<h3>{esc(c['hook'])}</h3><p>{esc(c['question'])}</p>
<div class="architecture"><span>구조</span>{esc(c['architecture'])}</div>
<div class="paper-result"><strong>논문 결과</strong><p>{esc(c['result'])}</p></div>
<div class="paper-apply"><strong>우리 적용</strong><p>{esc(c['meaning'])}</p></div>
<details class="read-details"><summary>원문에서 읽을 곳과 가져올 것</summary><p><b>읽을 곳</b> {esc(c['read'])}</p><p><b>읽고 남길 것</b> {esc(c['take'])}</p><p class="full-title">{esc(p['title'])}</p></details>
{paper_links(p,public)}</article>''')
    return '\n'.join(out+['</div>'])

def library_html(public=False):
    options=''.join(f'<option>{esc(g)}</option>' for g in sorted(set(groups.values())))
    out=['<details class="library-drawer"><summary><span>전체 문헌 자료실</span><b>111편</b><small>제목·ID·용도로 찾기</small></summary><div class="library-content"><div class="library-filters"><label>검색<input type="search" id="paper-search" placeholder="예: LoCal, 한국어, CrossAug"></label><label>용도<select id="paper-group"><option value="all">모든 용도</option>'+options+'</select></label></div><p id="library-count" aria-live="polite">111편 표시</p><div id="library-list">']
    for p in papers:
        group=groups.get(p.get('group'),'기반·확장 방법')
        search=' '.join([p['id'],*p.get('aliases',[]),p['title'],*p.get('previous_titles',[]),p.get('file_title',''),group,p.get('paper','')]).lower()
        out.append(f'<details class="library-row" id="paper-{p["id"]}" data-search="{esc(search,quote=True)}" data-group="{esc(group)}"><summary><span>{p["id"]}</span>{esc(p["title"])}</summary><div class="library-body"><p class="tag">{esc(group)}</p>')
        if p.get('paper'):out.append('<p>'+esc(p['paper'])+'</p>')
        if not public:out.append(f'<p class="filename">{esc(Path(p["file"]).name)}</p>')
        out.append(paper_links(p,public)+'</div></details>')
    return '\n'.join(out+['</div><p id="library-empty" hidden>검색어 또는 용도를 바꾸어 보자.</p></div></details>'])

def make_html(md,public=False):
    md=re.sub(r'<!-- PAPER_GUIDE_BEGIN -->.*?<!-- PAPER_GUIDE_END -->','<!-- GUIDE_HTML -->',md,flags=re.S)
    md=re.sub(r'<!-- PAPER_LIBRARY_BEGIN -->.*?<!-- PAPER_LIBRARY_END -->','<!-- LIBRARY_HTML -->',md,flags=re.S)
    rendered=markdown.markdown(md,extensions=['tables','fenced_code','attr_list'])
    rendered=rendered.replace('<!-- GUIDE_HTML -->',card_html(public)).replace('<!-- LIBRARY_HTML -->',library_html(public))
    doc=lh.fragment_fromstring(rendered,create_parent='div');main=lh.Element('div');section=None
    for node in list(doc):
        if node.tag=='h2':
            sid=node.get('id');node.attrib.pop('id',None);section=etree.SubElement(main,'section',id=sid);section.append(node)
        elif section is not None:section.append(node)
    tasks=[];task_section=main.xpath('.//section[@id="tasks"]')[0]
    children=list(task_section);i=0;rebuilt=[]
    while i<len(children):
        node=children[i]
        if node.tag=='h3' and node.get('id','').startswith('task-'):
            tid=node.get('id').split('-')[1];title=node.text_content();nodes=[];i+=1
            while i<len(children) and children[i].tag!='h3':nodes.append(children[i]);i+=1
            data={'id':tid,'title':title,'fields':{}}
            for sub in nodes:
                if sub.tag=='p' and 'definition' not in data:data['definition']=sub.text_content()
                if sub.tag=='ul':
                    for li in sub:
                        pair=re.split(r'[:：]',li.text_content(),maxsplit=1)
                        if len(pair)==2:data['fields'][pair[0].strip()]=pair[1].strip()
            tasks.append(data)
            article=lh.Element('article',{'class':'task-card','id':'task-'+tid,'data-task':tid})
            node.attrib.pop('id',None);article.append(node)
            if nodes:article.append(nodes.pop(0))
            quick=etree.SubElement(article,'div',{'class':'task-preview'})
            for k in ['입력','출력','주 지표']:
                if k in data['fields']:
                    p=etree.SubElement(quick,'p');b=etree.SubElement(p,'b');b.text=k+' ';b.tail=data['fields'][k]
            detail=etree.SubElement(article,'details',{'class':'task-detail'});etree.SubElement(detail,'summary').text='Agent 행동 · 50개 구성 · 비교군 · 구현 규모'
            for sub in nodes:detail.append(sub)
            btn=etree.SubElement(article,'button',{'class':'task-reading','data-select-task':tid});btn.text='이 태스크의 논문 보기'
            rebuilt.append(article)
        else:rebuilt.append(node);i+=1
    for n in list(task_section):task_section.remove(n)
    for n in rebuilt:task_section.append(n)
    opts=''.join(f'<option value="{t["id"]}">{esc(t["title"])}</option>' for t in tasks)
    compare=lh.fragment_fromstring('<div class="compare-box"><h3>두 후보를 나란히 비교하기</h3><div class="compare-selects"><label>후보 1<select id="compare-a">'+opts+'</select></label><label>후보 2<select id="compare-b">'+opts+'</select></label></div><div id="task-comparison"></div></div>')
    task_section.append(compare)
    for table in main.xpath('.//table'):
        parent=table.getparent();index=parent.index(table);wrap=lh.Element('div',{'class':'table-wrap'});parent.insert(index,wrap);wrap.append(table)
    four=main.xpath('.//section[@id="four-cases"]')[0]
    four.insert(2,lh.fragment_fromstring('''<div class="matrix-demo"><h3>네 조합을 눌러 보기</h3><div class="matrix-options" role="group" aria-label="주장과 근거 조합"><button data-case="tt" class="selected" aria-pressed="true">① 진짜 주장 · 진짜 근거</button><button data-case="tf" aria-pressed="false">② 진짜 주장 · 가짜 근거</button><button data-case="ff" aria-pressed="false">③ 가짜 주장 · 가짜 근거</button><button data-case="ft" aria-pressed="false">④ 가짜 주장 · 진짜 근거</button></div><div id="case-output" aria-live="polite"></div></div>'''))
    content=''.join(lh.tostring(n,encoding='unicode',method='html') for n in main)
    template=(ROOT/'tools'/'team_template_v2.html').read_text(encoding='utf-8')
    out=template.replace('__CONTENT__',content).replace('__TASK_DATA__',json.dumps(tasks,ensure_ascii=False).replace('</','<\\/'))
    out=out.replace('__EDITION__','팀 저장소 공유본')
    assert not re.search(r'__[A-Z_]+__',out)
    assert len(tasks)==6
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--public-dir');args=ap.parse_args()
    public=bool(args.public_dir);dest=Path(args.public_dir) if public else ROOT;dest.mkdir(parents=True,exist_ok=True)
    md=(ROOT/'팀공유.md').read_text(encoding='utf-8')
    md=set_block(md,'PAPER_GUIDE',guide_md(public));md=set_block(md,'PAPER_LIBRARY',library_md(public))
    (dest/'팀공유.md').write_text(md,encoding='utf-8')
    (dest/'팀공유_논문가이드.md').write_text('# 태스크와 연결해서 읽는 논문 28편\n\n'+guide_md(public),encoding='utf-8')
    (dest/'팀공유.html').write_text(make_html(md,public),encoding='utf-8')
    if not public:(ROOT/'팩트체크_연구지도.md').write_text(md,encoding='utf-8')
    print('Built',dest,'| candidates=6, matrix=4, paper introductions=28, library=111')

if __name__=='__main__':main()
