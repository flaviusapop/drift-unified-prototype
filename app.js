// Unified prototype: fold / unfold sections, fold-all per week, compact toggle
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
function setFold(src,folded){
  if(!src) return;
  src.dataset.fold = folded ? 'true':'false';
  const btn=src.querySelector('.srtoggle'), body=src.querySelector('.fold-wrap');
  if(btn) btn.setAttribute('aria-expanded', folded?'false':'true');
  if(body) body.inert = !!folded;
}
function syncAll(){
  $$('[data-fold-all]').forEach(b=>{
    const wk=b.closest('.wk'); if(!wk) return;
    const srcs=[...wk.querySelectorAll('.src')];
    b.textContent = srcs.some(x=>x.dataset.fold!=='true') ? 'Fold all' : 'Unfold all';
  });
}
document.addEventListener('click',e=>{
  const h=e.target.closest('.srch');
  if(h){ const src=h.closest('.src'); setFold(src, src.dataset.fold!=='true'); syncAll(); return; }
  const f=e.target.closest('[data-fold-all]');
  if(f){
    const wk=f.closest('.wk'), srcs=[...wk.querySelectorAll('.src')];
    const anyOpen=srcs.some(x=>x.dataset.fold!=='true');
    srcs.forEach(x=>setFold(x,anyOpen)); syncAll(); return;
  }
  if(e.target.closest('#dens')){
    const root=document.documentElement, on=root.dataset.kp!=='off';
    root.dataset.kp = on?'off':'on';
    const b=$('#dens'); b.textContent = on?'Key points':'Compact'; b.setAttribute('aria-pressed', String(on));
    try{localStorage.setItem('kp', on?'off':'on')}catch(_){}
  }
});
try{ if(localStorage.getItem('kp')==='off'){ document.documentElement.dataset.kp='off'; const b=$('#dens'); if(b){b.textContent='Key points';b.setAttribute('aria-pressed','true');} } }catch(_){}
// If linked with #learning / #reddit, ensure that section is unfolded
if(location.hash){
  const el=document.querySelector(location.hash);
  if(el && el.classList.contains('src')){ setFold(el,false); syncAll(); }
}
