/* Pumpkin Ink & Gold 1.2 · 主題切換 ＋ 互動點格
   兩種點格模式，用 <body data-dots="…"> 或 <script data-dots="…"> 指定：
   - magnetic（預設，南瓜 2026-09-20 定案＝Pumpkin Notes 首頁的效果）：16px 細點，像被小磁鐵吸引，
       往游標靠、沿按鈕輪廓收攏，離開後回到原位。
   - glow（選用，Pumpkin Notes 報告頁舊版）：點不移動，游標靠近的點變亮、變大。
   兩種都不用金色、都尊重 prefers-reduced-motion。無外部相依。 */
(() => {
  'use strict';
  const body = document.body;
  if (!body || body.dataset.igUiReady) return;
  body.dataset.igUiReady = 'true';
  const externalTheme = document.currentScript?.dataset.theme === 'external';
  const mode = (body.dataset.dots || document.currentScript?.dataset.dots || 'magnetic') === 'glow' ? 'glow' : 'magnetic';
  body.dataset.dotsMode = mode;
  const toggles = [...document.querySelectorAll('[data-ig-theme-toggle]')];
  const moon = '<path d="M20.5 13a8.7 8.7 0 0 1-9.5-9.5A8.7 8.7 0 1 0 20.5 13Z"/>';
  const sun = '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/>';
  function updateButtons() {
    const night = body.dataset.theme === 'night';
    toggles.forEach(b => {
      b.setAttribute('aria-label', night ? '切換淺色模式' : '切換深色模式');
      b.setAttribute('title', night ? '切換淺色模式' : '切換深色模式');
      b.setAttribute('aria-pressed', String(night));
      b.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(night ? sun : moon)+'</svg>';
    });
  }
  if (!externalTheme) {
    let theme = 'day';
    try { if (localStorage.getItem('igTheme') === 'night') theme = 'night'; } catch (_) {}
    try { const q=new URLSearchParams(location.search).get('theme'); if (q==='night'||q==='day') theme=q; } catch (_) {}
    body.dataset.theme = theme;
    toggles.forEach(b => b.addEventListener('click', () => {
      body.dataset.theme = body.dataset.theme === 'night' ? 'day' : 'night';
      try { localStorage.setItem('igTheme', body.dataset.theme); } catch (_) {}
    }));
  }
  updateButtons();
  const canvas = document.querySelector('#pn-dots') || document.createElement('canvas');
  canvas.classList.add('ig-dotfield');
  canvas.setAttribute('aria-hidden','true');
  if (!canvas.isConnected) body.prepend(canvas);
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  body.classList.add('ig-has-dotfield');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const fine = matchMedia('(any-pointer: fine)');
  let width=0, height=0, scale=1, spacing=16, radius=.6, raf=0, last=0;
  let ink='45,43,44', opacity=.3;
  const pointer={x:-1000,y:-1000,tx:-1000,ty:-1000,p:0,target:0};
  let active=null, shapes=[];
  const smooth = v => { const t=Math.max(0,Math.min(1,v)); return t*t*(3-2*t); };
  const interactive = 'a,button,summary,[role="button"],select,input,textarea';
  function enabled(){return !reduce.matches && fine.matches && (mode==='glow' || width>768) && !document.hidden;}
  function color(){
    const dark=body.dataset.theme==='night';
    if(mode==='glow'){ink=dark?'255,255,255':'22,20,21'; opacity=dark?.06:.10;}
    else{ink=dark?'247,247,247':'45,43,44'; opacity=dark?.18:.3;}
  }
  function size(){
    width=innerWidth; height=innerHeight; scale=Math.min(devicePixelRatio||1,2);
    canvas.width=Math.round(width*scale);canvas.height=Math.round(height*scale);
    canvas.style.width=width+'px';canvas.style.height=height+'px';
    ctx.setTransform(scale,0,0,scale,0,0);
    const responsive=.8+.2*Math.max(0,Math.min(1,(width-360)/408));
    if(mode==='glow'){spacing=24;radius=1;}else{spacing=16*responsive;radius=.6*responsive;}
    if(!enabled()) reset(true); else wake();
    draw();
  }
  function rectangle(el){
    const b=el.getBoundingClientRect();
    const css=getComputedStyle(el);
    const value=css.borderTopLeftRadius;
    const corner=value.includes('%')?Math.min(b.width,b.height)*parseFloat(value)/100:parseFloat(value)||0;
    return {cx:b.x+b.width/2,cy:b.y+b.height/2,hw:b.width/2,hh:b.height/2,r:Math.min(corner,b.width/2,b.height/2)};
  }
  function distance(x,y,b){
    const qx=Math.abs(x-b.cx)-b.hw+b.r, qy=Math.abs(y-b.cy)-b.hh+b.r;
    return Math.hypot(Math.max(qx,0),Math.max(qy,0))+Math.min(Math.max(qx,qy),0)-b.r;
  }
  function select(el){
    if(el===active)return;
    shapes.forEach(s=>s.target=0); active=el;
    if(el)shapes.push({el,b:rectangle(el),p:0,target:1});
    shapes=shapes.slice(-2);
  }
  function hit(){
    if(mode==='glow'){select(null);return;}
    const el=document.elementFromPoint(pointer.tx,pointer.ty)?.closest(interactive);
    const b=el?.getBoundingClientRect();
    select(el && !el.closest('[data-dots-still]') && b.width*b.height<width*height*.4 ? el : null);
  }
  function draw(){
    ctx.clearRect(0,0,width,height);
    const startX=mode==='glow'?spacing/2:-((scrollX%spacing+spacing)%spacing),startY=mode==='glow'?spacing/2:-((scrollY%spacing+spacing)%spacing);
    const motion=enabled();
    for(let y=startY;y<height+spacing;y+=spacing){
      for(let x=startX;x<width+spacing;x+=spacing){
        let dx=0,dy=0,strength=0;
        if(mode==='glow'){
          const k=motion&&pointer.p>.001?Math.max(0,1-Math.hypot(x-pointer.x,y-pointer.y)/140)*pointer.p:0;
          ctx.beginPath();ctx.arc(x,y,radius*(1+.8*k),0,Math.PI*2);
          ctx.fillStyle=`rgba(${ink},${(opacity+(.45-opacity)*k).toFixed(3)})`;ctx.fill();
          continue;
        }
        if(motion && pointer.p>.001){
          const attraction=smooth(1-Math.hypot(x-pointer.x,y-pointer.y)/160)*pointer.p;
          dx=(pointer.x-x)*.26*attraction;dy=(pointer.y-y)*.26*attraction;strength=attraction;
        }
        if(motion){
          let best=0, chosen=null, dist=0;
          for(const s of shapes){
            if(s.p<.001)continue;
            const d=distance(x,y,s.b);
            const pull=smooth(1-Math.abs(d)/64)*smooth(1-Math.hypot(x-pointer.x,y-pointer.y)/260)*s.p;
            if(pull>best){best=pull;chosen=s.b;dist=d;}
          }
          if(chosen && best>.001){
            const gx=distance(x+.5,y,chosen)-distance(x-.5,y,chosen),gy=distance(x,y+.5,chosen)-distance(x,y-.5,chosen);
            const len=Math.hypot(gx,gy);
            if(len>.001){dx-=gx/len*dist*best;dy-=gy/len*dist*best;strength=Math.max(strength,best);}
          }
        }
        const r=radius*(1+.45*strength);
        ctx.beginPath();ctx.arc(x+dx,y+dy,r,0,Math.PI*2);
        ctx.fillStyle=`rgba(${ink},${opacity+.25*strength})`;ctx.fill();
      }
    }
  }
  function frame(time){
    raf=0;
    const dt=last?Math.min(32,time-last):16.67;last=time;
    const ease=1-Math.exp(-dt/110), shapeEase=1-Math.exp(-dt/150);
    pointer.x+=(pointer.tx-pointer.x)*ease;pointer.y+=(pointer.ty-pointer.y)*ease;
    const goal=active?0:pointer.target;
    pointer.p+=(goal-pointer.p)*ease;
    let moving=Math.hypot(pointer.tx-pointer.x,pointer.ty-pointer.y)>.2 || Math.abs(goal-pointer.p)>.002;
    shapes.forEach(s=>{
      s.p+=(s.target-s.p)*shapeEase;
      if(s.target && s.el.isConnected)s.b=rectangle(s.el);
      if(Math.abs(s.target-s.p)>.002)moving=true;
    });
    shapes=shapes.filter(s=>s.target||s.p>.002);
    draw();
    if(moving && enabled())raf=requestAnimationFrame(frame);else last=0;
  }
  function wake(){if(!raf && !document.hidden)raf=requestAnimationFrame(frame);}
  function reset(immediate=false){
    pointer.target=0;select(null);
    if(immediate){pointer.p=0;shapes=[];if(raf)cancelAnimationFrame(raf);raf=0;last=0;draw();}else wake();
  }
  window.addEventListener('pointermove',e=>{
    if(!enabled() || e.pointerType==='touch')return;
    if(!pointer.target){pointer.x=e.clientX;pointer.y=e.clientY;}
    pointer.tx=e.clientX;pointer.ty=e.clientY;pointer.target=1;hit();wake();
  },{passive:true});
  document.documentElement.addEventListener('pointerleave',()=>reset());
  window.addEventListener('blur',()=>reset());
  window.addEventListener('resize',size,{passive:true});
  window.addEventListener('scroll',()=>{if(enabled()&&pointer.target)hit();wake();},{passive:true});
  document.addEventListener('visibilitychange',()=>{if(document.hidden)reset(true);else draw();});
  reduce.addEventListener('change',()=>reset(true));fine.addEventListener('change',()=>reset(true));
  new MutationObserver(()=>{updateButtons();color();draw();}).observe(body,{attributes:true,attributeFilter:['data-theme']});
  color();size();
})();
