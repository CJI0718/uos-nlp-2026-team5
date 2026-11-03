
const dialog=document.getElementById('viewer'), big=document.getElementById('viewer-img');let opener=null;
document.querySelectorAll('.image-open').forEach(b=>b.addEventListener('click',()=>{opener=b;big.src=b.querySelector('img').src;big.alt=b.dataset.caption;big.className='fit';document.getElementById('viewer-title').textContent=b.dataset.caption;document.getElementById('viewer-source').href=b.dataset.source;document.getElementById('zoom').textContent='원본 크기';dialog.showModal()}));
document.getElementById('close-viewer').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close()});
dialog.addEventListener('close',()=>{if(opener)opener.focus()});
document.getElementById('zoom').addEventListener('click',e=>{big.classList.toggle('fit');e.target.textContent=big.classList.contains('fit')?'원본 크기':'화면 맞춤'});
function progress(){const max=document.documentElement.scrollHeight-innerHeight;document.getElementById('progress').style.width=(max>0?scrollY/max*100:0)+'%'}
addEventListener('scroll',progress,{passive:true});addEventListener('resize',progress);progress();
const obs=new IntersectionObserver(es=>{for(const e of es){if(e.isIntersecting){document.querySelectorAll('.side a').forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id))}}},{rootMargin:'-10% 0px -65% 0px'});
document.querySelectorAll('.chapter').forEach(e=>obs.observe(e));
const menu=document.querySelector('.side details');const narrow=matchMedia('(max-width:740px)');if(narrow.matches)menu.open=false;narrow.addEventListener('change',e=>{menu.open=!e.matches});
if(document.getElementById('flip-lab')){
 const b=document.getElementById('base-count'),f=document.getElementById('flip-count'),out=document.getElementById('flip-output');
 function calc(){let n=Math.max(1,Math.min(100,Number(b.value)||1));let k=Math.max(0,Math.min(n,Number(f.value)||0));b.value=n;f.max=n;f.value=k;out.textContent='Flip rate = '+k+' ÷ '+n+' = '+(k/n*100).toFixed(1)+'% · 전체 100개 기준 손상 비율은 '+k.toFixed(1)+'%';}
 b.addEventListener('change',calc);f.addEventListener('change',calc);calc();
}
if(document.getElementById('crag-lab')){
 const sel=document.getElementById('score-case'),out=document.getElementById('crag-output');
 const examples={good:[.8,-.3,-.7],bad:[-1,-1,-1],middle:[.4,.1,-.8],edge:[.59,-.99,-.7],false:[.8,.2,-.1]};
 function route(){const x=examples[sel.value],max=Math.max(...x);let v=max>.59?'Correct → 기존 문서 정제 후 생성':max<-.99?'Incorrect → 웹 검색으로 대체':'Ambiguous → 기존 자료 정제 + 웹 근거 결합';out.textContent=v+(sel.value==='false'?' · 사실이 틀려도 이 점수라면 같은 Correct 분기':'');}
 sel.addEventListener('change',route);route();
}
