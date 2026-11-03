import assert from 'node:assert/strict';

// Solid surfaces only. CSS opacity applies to the rendered group, including
// its background; it is not merely another alpha value on the text colour.
// https://www.w3.org/TR/css-color-4/#transparency
// https://www.w3.org/TR/compositing-1/#simplealphacompositing
export function measureSolidText(root) {
 const rgba=value=>{
  if(!/^rgba?\([\d.,\s]+\)$/.test(value))throw Error('UNMEASURED_CSS_COLOR:'+value);
  const c=value.match(/[\d.]+/g).map(Number);if(c.length===3)c.push(1);
  if(c.length!==4||c.some(x=>!Number.isFinite(x)))throw Error('INVALID_CSS_COLOR:'+value);
  return c;
 };
 const over=(a,b)=>{
  const alpha=a[3]+b[3]*(1-a[3]);
  return alpha===0?[0,0,0,0]:[...a.slice(0,3).map((x,i)=>(x*a[3]+b[i]*b[3]*(1-a[3]))/alpha),alpha];
 };
 const opacity=(c,n)=>[c[0],c[1],c[2],c[3]*n];
 const lum=c=>c.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((sum,x,i)=>sum+x*[.2126,.7152,.0722][i],0);
 const rows=[],exempt=[];
 for(const el of[root,...root.querySelectorAll('*')]){
  const style=getComputedStyle(el),text=[...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join(' ').trim();
  const label=text||(/^(INPUT|TEXTAREA)$/.test(el.tagName)?el.value:'');
  if(!label||!el.getClientRects().length||style.visibility!=='visible'||el.tagName==='OPTION')continue;
  if(el.closest(':disabled,[aria-disabled="true"]')){exempt.push({label:label.slice(0,100),reason:'INACTIVE_CONTROL_WCAG_CONTRAST_EXEMPTION'});continue;}
  let foreground=rgba(style.color),background=[0,0,0,0];const layers=[];
  for(let p=el;p;p=p.parentElement){
   const s=getComputedStyle(p),alpha=Number(s.opacity);
   if(s.backgroundImage!=='none'||s.filter!=='none'||s.mixBlendMode!=='normal'||(s.backdropFilter&&s.backdropFilter!=='none')||!Number.isFinite(alpha)||alpha<0||alpha>1)
    throw Error('UNMEASURED_SKU_TEXT_SURFACE:'+JSON.stringify({label:label.slice(0,100),tag:p.tagName,classes:p.className,backgroundImage:s.backgroundImage,opacity:s.opacity,filter:s.filter,mixBlendMode:s.mixBlendMode}));
   const color=rgba(s.backgroundColor);
   foreground=opacity(over(foreground,color),alpha);background=opacity(over(background,color),alpha);
   layers.push({tag:p.tagName,background:s.backgroundColor,opacity:alpha});
  }
  // Refuse an unspecified canvas instead of guessing white behind the page.
  if(background[3]!==1||foreground[3]!==1)throw Error('MISSING_OPAQUE_SKU_TEXT_SURFACE:'+label);
  const a=lum(foreground),b=lum(background);
  rows.push({label:label.slice(0,100),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05),foreground:foreground.slice(0,3),background:background.slice(0,3),layers});
 }
 return{rows,exempt};
}

export async function readable(panel){
 const observed=await panel.evaluate(measureSolidText);
 assert.ok(observed.rows.length>0,'NO_VISIBLE_SKU_TEXT_MEASURED');
 assert.deepEqual(observed.rows.filter(row=>row.ratio<4.5),[],'SKU_TEXT_CONTRAST_BELOW_4_5');
 return observed;
}
