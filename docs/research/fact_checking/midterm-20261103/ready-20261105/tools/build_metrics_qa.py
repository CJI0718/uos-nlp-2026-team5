from pathlib import Path
from bs4 import BeautifulSoup
import subprocess,re,json,math

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'평가지표_질의응답_산식과근거.md'
DEST=ROOT/'평가지표_질의응답_산식과근거.html'
fragment=subprocess.run(['pandoc',str(SOURCE),'--from','markdown','--to','html5','--mathml'],check=True,capture_output=True,encoding='utf-8').stdout
soup=BeautifulSoup(fragment,'html.parser')
out=BeautifulSoup('<main id="content"></main>','html.parser');main=out.main
section=None;body=None;toc=[];qcount=0
for node in list(soup.contents):
    if getattr(node,'name',None)=='h1':continue
    if getattr(node,'name',None)=='h2':
        sid='chapter-'+str(len(toc)+1)
        node['id']=sid
        section=out.new_tag('section',attrs={'class':'chapter','aria-labelledby':sid})
        main.append(section);section.append(node);body=section
        toc.append((sid,node.get_text()))
    elif getattr(node,'name',None)=='h3' and re.match(r'Q\d+',node.get_text()):
        qnum=int(re.match(r'Q(\d+)',node.get_text())[1]);qcount+=1
        d=out.new_tag('details',attrs={'class':'qa','id':f'q{qnum:02d}'})
        if qnum in (1,2,12,24,32):d['open']=''
        summary=out.new_tag('summary');summary.string=node.get_text();d.append(summary)
        body=out.new_tag('div',attrs={'class':'answer'});d.append(body);section.append(d)
    elif getattr(node,'name',None)=='h3':
        body=section;section.append(node)
    elif body is not None:body.append(node)
for table in main.find_all('table'):
    wrap=out.new_tag('div',attrs={'class':'table-wrap','tabindex':'0','role':'region','aria-label':'비교표 — 가로 스크롤 가능'})
    table.wrap(wrap)
for formula in main.select('span.math.display'):
    formula['class']=['math','display','formula']
for p in main.find_all('p'):
    for t in list(p.find_all(string=True)):
        if t.parent.name in ('math','annotation'):continue
        # Compact source references link to the bibliography; prose stays unchanged.
        if re.search(r'\[S[1-8](?:[^\]]*)\]',str(t)):
            replaced=re.sub(r'\[(S[1-8][^\]]*)\]',lambda m:'<a class="source-ref" href="#sources">['+m[1]+']</a>',str(t))
            t.replace_with(BeautifulSoup(replaced,'html.parser'))
sources=main.find('h3',string='출처 바로가기')
if sources:sources['id']='sources'
calculator='''<aside class="calculator" aria-label="가상 전이표 계산기"><h4>가상 전이표 계산기</h4><p>실험 결과가 아닙니다. 숫자를 바꾸며 서로 다른 분모를 확인하세요.</p><div class="calc-inputs"><label>a · 정답 유지<input id="ca" type="number" min="0" step="1" value="5"></label><label>b · 손상<input id="cb" type="number" min="0" step="1" value="1"></label><label>c · 회복<input id="cc" type="number" min="0" step="1" value="2"></label><label>d · 오답 유지<input id="cd" type="number" min="0" step="1" value="2"></label></div><output id="calc-out" aria-live="polite"></output></aside>'''
main.select_one('#q24 .answer').append(BeautifulSoup(calculator,'html.parser'))
CSS='''
:root{--bg:#f3f6fa;--paper:#fff;--ink:#152b43;--muted:#52677d;--line:#d5e0eb;--accent:#005eb8;--soft:#edf5fd;--fs:18px;color-scheme:light}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:160px}body{margin:0;background:var(--bg);color:var(--ink);font:var(--fs)/1.88 'Segoe UI','Malgun Gothic','Apple SD Gothic Neo',sans-serif;word-break:keep-all;overflow-wrap:anywhere}a{color:var(--accent);text-underline-offset:3px}button,input,select{font:inherit}button{cursor:pointer;background:var(--paper);color:var(--ink);border:1px solid var(--line);border-radius:6px;padding:7px 11px;font-size:14px}button:focus-visible,a:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #dc9d30;outline-offset:3px}[hidden]{display:none!important}
header{background:#005eb8;color:white;padding:50px max(5vw,22px) 40px}.eyebrow{letter-spacing:.13em;font-size:13px;font-weight:700}h1{font-size:clamp(28px,4vw,46px);line-height:1.3;max-width:1100px;margin:14px 0}header p{max-width:1050px;margin-bottom:0;color:#e5f1ff}.toolbar{position:sticky;top:0;z-index:9;background:var(--paper);border-bottom:1px solid var(--line);padding:12px 4vw;display:flex;gap:10px;align-items:center;flex-wrap:wrap}.search{flex:1;min-width:220px}.search input{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);font-size:16px}.counter{font-size:13px;color:var(--muted)}.layout{display:grid;grid-template-columns:235px minmax(0,1000px);gap:36px;max-width:1340px;margin:28px auto;padding:0 20px}.sidebar{position:sticky;top:100px;align-self:start;font-size:14px}.sidebar ol{padding:0;list-style:none}.sidebar li{margin:12px 0}.sidebar a{text-decoration:none}.sidebar .tip{background:var(--soft);padding:14px;border-left:3px solid var(--accent);font-size:13px}
main,.layout>div{min-width:0}.chapter{margin-bottom:36px}h2{font-size:26px;line-height:1.5;margin:0 0 16px;border-bottom:2px solid var(--accent);padding:14px 0}h3{font-size:22px;margin-top:30px}h4{margin:0;font-size:19px}.qa{margin:12px 0;background:var(--paper);border:1px solid var(--line);border-radius:8px;overflow:hidden}.qa>summary{font-weight:700;padding:20px 22px;cursor:pointer;line-height:1.55;list-style-position:outside;margin-left:20px}.qa[open]>summary{color:var(--accent);border-bottom:1px solid var(--line)}.answer{padding:8px 25px 24px}.answer p{margin:16px 0}.answer strong{color:var(--ink)}blockquote{margin:20px 0;padding:14px 20px;border-left:4px solid var(--accent);background:var(--soft)}blockquote p{margin:0!important}.table-wrap{overflow-x:auto;margin:22px 0;border:1px solid var(--line);border-radius:4px}table{border-collapse:collapse;width:100%;min-width:580px;font-size:.86em;line-height:1.7}th,td{padding:12px 14px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}th{background:var(--soft);font-weight:700}tr:last-child td{border:0}ol,ul{padding-left:1.5em}li{margin:9px 0}.formula{display:block;max-width:100%;overflow-x:auto;padding:22px 18px;background:var(--soft);border:1px solid var(--line);border-radius:5px;text-align:center;margin:20px 0;font-size:1.15em}math{font-family:'Latin Modern Math','Cambria Math','STIX Two Math',serif}math[display=block]{margin:0}.source-ref{font-size:.85em;white-space:nowrap}.calculator{margin-top:24px;padding:20px;background:var(--soft);border:1px solid var(--line);border-radius:6px}.calculator p{font-size:14px}.calc-inputs{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.calc-inputs label{font-size:14px}.calc-inputs input{width:100%;display:block;padding:8px;color:var(--ink);background:var(--paper);border:1px solid var(--line);border-radius:4px}output{display:block;margin-top:16px;font-size:16px}footer{padding:25px 4vw;color:var(--muted);font-size:14px}body.dark{--bg:#111e2b;--paper:#182a3a;--ink:#e7eff9;--muted:#afc1d4;--line:#3b5165;--accent:#88c4ff;--soft:#213b50;color-scheme:dark}#empty{padding:30px;background:var(--paper)}
@media(max-width:1000px){.layout{grid-template-columns:1fr;gap:12px;max-width:950px}.sidebar{position:static}.sidebar ol{display:flex;flex-wrap:wrap;gap:8px 18px}.sidebar li{margin:0}.sidebar .tip{display:none}.toolbar{padding:10px 18px}header{padding:30px 22px}html{scroll-padding-top:180px}}
@media(max-width:550px){:root{--fs:16px}.layout{padding:0 12px}.answer{padding:5px 16px 18px}.qa>summary{padding:17px 12px;font-size:17px}h2{font-size:22px}.calc-inputs{grid-template-columns:1fr 1fr}.toolbar button{padding:6px 9px}.counter{width:100%}.formula{font-size:1em;padding:15px 10px}header p{font-size:15px}}
@media print{.toolbar,.sidebar,.calculator,footer{display:none!important}header{background:white;color:black;padding:0 0 20px}header p{color:#333}.layout{display:block;padding:0;margin:0}.qa{break-inside:auto;border:0;border-bottom:1px solid #ccc}.qa>summary{margin:0;padding:14px 0}.answer{padding:0}.table-wrap,.formula{overflow:visible}table{min-width:0;font-size:10pt}.qa>summary::marker{content:''}body{background:white;color:black;font-size:11pt}h2{break-after:avoid}.formula{font-size:11pt}a{color:black}header .eyebrow{color:#333}}
'''
JS='''
const qs=[...document.querySelectorAll('.qa')],sections=[...document.querySelectorAll('.chapter')];
const search=document.querySelector('#search'),status=document.querySelector('#status');
function filter(){const term=search.value.trim().toLowerCase();let n=0;for(const q of qs){const hit=!term||q.textContent.toLowerCase().includes(term);q.hidden=!hit;if(hit){n++;if(term)q.open=true;}}for(const s of sections){const cards=[...s.querySelectorAll('.qa')];s.hidden=cards.length>0&&cards.every(q=>q.hidden);}status.textContent=n+' / '+qs.length+'개 문답';document.querySelector('#empty').hidden=n>0;}
search.addEventListener('input',filter);document.querySelector('#clear').onclick=()=>{search.value='';filter();};
document.querySelector('#expand').onclick=()=>qs.filter(q=>!q.hidden).forEach(q=>q.open=true);
document.querySelector('#collapse').onclick=()=>qs.forEach(q=>q.open=false);
document.querySelector('#theme').onclick=()=>{document.body.classList.toggle('dark');document.querySelector('#theme').setAttribute('aria-pressed',document.body.classList.contains('dark'));};
let fs=18;document.querySelector('#plus').onclick=()=>{fs=Math.min(24,fs+1);document.documentElement.style.setProperty('--fs',fs+'px');};document.querySelector('#minus').onclick=()=>{fs=Math.max(15,fs-1);document.documentElement.style.setProperty('--fs',fs+'px');};
document.querySelectorAll('.sidebar a').forEach(a=>a.addEventListener('click',()=>{search.value='';filter();}));
const vals=['ca','cb','cc','cd'].map(id=>document.getElementById(id));
function calc(){const v=vals.map(x=>Number(x.value));const out=document.querySelector('#calc-out');if(v.some((x,i)=>!Number.isFinite(x)||x<0||!Number.isInteger(x)||vals[i].value==='')){out.textContent='0 이상의 정수를 입력해 주세요.';return;}const[a,b,c,d]=v,N=a+b+c+d;const pct=(x,n)=>n?(100*x/n).toFixed(1)+'%':'N/A';out.textContent=`정상 쌍 N=${N} · C1 정확도 ${pct(a+b,N)} · C2 정확도 ${pct(a+c,N)} ｜ 회복 ${c}/${c+d} = ${pct(c,c+d)} · 손상 ${b}/${a+b} = ${pct(b,a+b)} ｜ 순 변화 ${N?((c-b)/N*100).toFixed(1)+'%포인트':'N/A'}`;}
vals.forEach(x=>x.addEventListener('input',calc));calc();filter();
let prior;addEventListener('beforeprint',()=>{prior=qs.map(q=>({open:q.open,hidden:q.hidden}));qs.forEach(q=>{q.open=true;q.hidden=false;});sections.forEach(s=>s.hidden=false);});addEventListener('afterprint',()=>{if(prior)qs.forEach((q,i)=>{q.open=prior[i].open;q.hidden=prior[i].hidden;});filter();});document.querySelector('#print').onclick=()=>window.print();
'''
nav=''.join(f'<li><a href="#{sid}">{title}</a></li>' for sid,title in toc)
html=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Fact Check Agent · 평가지표 질의응답</title><style>{CSS}</style></head><body><header><div class="eyebrow">NLP TEAM 5 · METRICS & EVALUATION · 2026-11-05</div><h1>평가지표, 어떻게 정의하고<br>어떻게 방어할까요?</h1><p>40개 질문 · 산식 · 가상 채점 예시 · 원문 근거<br><strong>판정 → 근거 → 오염 → 교정 → 비용</strong>을 한 흐름으로 읽는 Fact Check Agent 평가 매뉴얼입니다.</p></header><div class="toolbar"><label class="search"><input id="search" type="search" aria-label="문답 검색" placeholder="검색: GSR, 분모, 근거 부족, bootstrap…"></label><button id="clear">검색 지우기</button><button id="expand">모두 펼치기</button><button id="collapse">모두 접기</button><button id="minus" aria-label="글자 작게">A−</button><button id="plus" aria-label="글자 크게">A+</button><button id="theme" aria-pressed="false">화면 모드</button><button id="print">인쇄 / PDF</button><span class="counter" id="status" aria-live="polite"></span></div><div class="layout"><nav class="sidebar" aria-label="장별 목차"><strong>빠르게 찾아보기</strong><ol>{nav}</ol><div class="tip">먼저 Q01·Q02 → Q12–14 → Q24 → Q32를 읽으세요.<br><br>검색하면 해당 문답이 펼쳐집니다. 수식과 본문은 인터넷 없이 읽을 수 있습니다.</div></nav><div><p id="empty" hidden>검색 결과가 없습니다. 다른 단어로 검색해 주세요.</p>{main}</div></div><footer>Team 5 · 정헌수 · 이원준 · 최정일<br>Markdown 원본에서 생성한 단일 HTML · 논문 링크를 열 때만 인터넷이 필요합니다.</footer><script>{JS}</script></body></html>'''
DEST.write_text(html,encoding='utf-8')
check=BeautifulSoup(html,'html.parser')
ids=[x['id'] for x in check.select('[id]')]
assert len(ids)==len(set(ids))
assert len(check.select('details.qa'))==40
assert len(check.find_all('math'))>30
assert not check.select('script[src],link[href],img[src]')
assert not any(x.get('href','').startswith('#') and x['href'][1:] not in ids for x in check.select('a[href]'))
for a in check.find_all('annotation'):a.decompose()
assert '\\frac' not in check.get_text()
report={'qa_count':qcount,'chapters':len(toc),'mathml_count':len(check.find_all('math')),'bytes':DEST.stat().st_size,'external_asset_dependencies':0,'unresolved_local_anchors':0}
(Path(__file__).resolve().parent/'metrics_qa_checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))


