"""Render editable Markdown into portable Korean reading guides (Pandoc + BeautifulSoup)."""
from pathlib import Path
import base64,html,json,re,subprocess,shutil
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
PANDOC=shutil.which('pandoc') or r'C:/Users/CJI/AppData/Local/Pandoc/pandoc.EXE'
FIG=json.loads((ROOT/'tools/figures.json').read_text(encoding='utf-8'))
CSS=(ROOT/'tools/reading.css').read_text(encoding='utf-8')
JS=(ROOT/'tools/reading.js').read_text(encoding='utf-8')
CSS+='\n.search-box{width:100%;padding:9px;margin:10px 0;border:1px solid #b9cccb;border-radius:6px} .chapter[hidden]{display:none} .side a[hidden]{display:none} #search-status{font-size:12px;color:#526875} .scope-label{font-size:13px;color:#526875}\n'
JS+='''
const search=document.getElementById('search');
function filterChapters(){const q=search.value.trim().toLowerCase();let count=0;document.querySelectorAll('.chapter').forEach(s=>{s.hidden=q&&!s.textContent.toLowerCase().includes(q);if(!s.hidden)count++;const a=document.querySelector('.side a[href="#'+s.id+'"]');if(a)a.hidden=s.hidden});document.getElementById('search-status').textContent=count+'개 절 표시';}
search.addEventListener('input',filterChapters);filterChapters();
document.querySelectorAll('a[href^="#"]').forEach(a=>a.addEventListener('click',()=>{search.value='';filterChapters()}));
'''
def figure(key):
 f=FIG[key];image=base64.b64encode((ROOT/f['file']).read_bytes()).decode();esc=html.escape
 return f'''<figure class="paper-scene"><div class="scene-top"><b>{esc(f['title'])}</b><span>원문 전체 페이지</span></div><div class="scene-grid"><button class="image-open" type="button" aria-label="{esc(f['title'])} 확대" data-caption="{esc(f['title'])}" data-source="{esc(f['url'])}"><img loading="lazy" src="data:image/png;base64,{image}" alt="{esc(f['title'])}"><span>눌러서 전체 페이지 확대 ↗</span></button><figcaption><p class="scene-label">논문 전체 전개에서의 위치</p><p>{esc(f['context'])}</p><p class="scene-label">읽을 부분</p><p>{esc(f['read'])}</p><p class="scene-label">우리 연구와의 연결</p><p>{esc(f['meaning'])}</p><a href="{esc(f['url'])}" target="_blank" rel="noreferrer">공식 원문 해당 페이지 ↗</a><p class="credit">원문 페이지를 변경 없이 인용했습니다. 설명은 한국어 해설입니다.</p></figcaption></div></figure>'''
def build(rel,title):
 file=ROOT/rel;source=file.read_text(encoding='utf-8')
 out=subprocess.run([PANDOC,'--from=markdown+raw_html','--to=html5','--wrap=none'],input=source,text=True,encoding='utf-8',capture_output=True,check=True).stdout
 out=re.sub(r'<!-- FIGURE:(\w+) -->',lambda m:figure(m[1]),out)
 soup=BeautifulSoup(out,'html.parser');intro=[];sections=[];current=None
 for table in soup.find_all('table'):table.wrap(soup.new_tag('div',attrs={'class':'table-scroll','tabindex':'0'}))
 for node in list(soup.contents):
  if getattr(node,'name',None)=='h2':
   sid='section-'+str(len(sections)+1);node['id']=sid+'-title';current=soup.new_tag('section',attrs={'class':'chapter','id':sid});sections.append((sid,node.get_text(),current))
  if current is None:intro.append(str(node))
  else:current.append(node)
 toc=''.join(f'<a href="#{sid}">{html.escape(t)}</a>' for sid,t,_ in sections)
 prefix='../' if rel.startswith('papers/') else ''
 nav=f'<a href="{prefix}팀논의_연구방향과_Task.html">팀 논의·Task</a><a href="{prefix}발표논문_읽기지도.html">32편 읽기 지도</a><a href="{prefix}NLP_Team5_Midterm_18slides.pptx">PPTX 18장</a>'
 page=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light"><title>{html.escape(title)} | NLP Team5</title><style>{CSS}</style></head><body id="top"><header class="top"><div class="top-inner"><a class="brand" href="{prefix}팀논의_연구방향과_Task.html">NLP TEAM 5 / MIDTERM</a><nav>{nav}</nav></div><div class="progress" id="progress"></div></header><div class="shell"><aside class="side"><label for="search">이 문서에서 찾기</label><input id="search" class="search-box" type="search" placeholder="예: C0, 회복, Q-network"><p id="search-status" aria-live="polite"></p><details open><summary>읽기 목차</summary><nav>{toc}</nav></details></aside><main><div class="hero"><p class="eyebrow">TEAM DISCUSSION · SOURCE-BASED READING</p>{''.join(intro)}</div>{''.join(str(s)for _,_,s in sections)}<footer class="bottom"><a href="{file.name}">Markdown 편집 원본</a> · 2026-11-03 논의 / 2026-11-04 공유본 · <a href="#top">맨 위로</a></footer></main></div><dialog id="viewer" aria-labelledby="viewer-title"><div class="viewer-head"><b id="viewer-title">원문 전체 페이지</b><a id="viewer-source" target="_blank" rel="noreferrer">공식 원문 ↗</a><button id="zoom" type="button">원본 크기</button><button id="close-viewer" type="button" aria-label="확대 닫기">닫기 ×</button></div><div class="viewer-body"><img id="viewer-img" alt="" class="fit"></div></dialog><script>{JS}</script></body></html>'''
 file.with_suffix('.html').write_text(page,encoding='utf-8')
 return {'file':str(file.relative_to(ROOT)),'chapters':len(sections),'images':len(BeautifulSoup(page,'html.parser').select('.image-open'))}
if __name__=='__main__':
 docs=[('팀논의_연구방향과_Task.md','현재 논의·연구 방향·Task'),('발표논문_읽기지도.md','발표 논문 32편 읽기 지도'),('papers/RAGuard_한국어_절별해설.md','RAGuard 절별 해설'),('papers/Stop_RAG_한국어_절별해설.md','Stop-RAG 절별 해설')]
 print(json.dumps([build(*d)for d in docs],ensure_ascii=False,indent=2))
