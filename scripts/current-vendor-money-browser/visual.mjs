// A money-page adaptation of B luminance math: preserve 4.5 threshold and every
// visible text record, but measure actual alpha/opacity instead of refusing all
// disabled buttons. The qualified B comparator file is not changed.
import assert from 'node:assert/strict'

export function renderedTextContrast(foreground,layers){
 const rgba=c=>c.length===3?[...c,1]:c
 const over=(front,back)=>{
  const f=rgba(front),b=rgba(back),alpha=f[3]+b[3]*(1-f[3])
  return alpha?[...f.slice(0,3).map((x,i)=>(x*f[3]+b[i]*b[3]*(1-f[3]))/alpha),alpha]:[0,0,0,0]
 }
 let fg=rgba(foreground),bg=[0,0,0,0]
 for(const {color,opacity,backgroundImage='none'} of layers){
  if(backgroundImage!=='none'&&(fg[3]!==1||bg[3]!==1))throw Error('UNMEASURED_FINANCE_BACKGROUND_IMAGE')
  if(!Number.isFinite(opacity)||opacity<0||opacity>1)throw Error('INVALID_TEXT_SURFACE_OPACITY')
  fg=over(fg,color);bg=over(bg,color);fg[3]*=opacity;bg[3]*=opacity
 }
 if(fg[3]!==1||bg[3]!==1)throw Error('MISSING_OPAQUE_FINANCE_CANVAS')
 const lum=c=>c.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0)
 const a=lum(fg),b=lum(bg)
 return{foreground:fg.slice(0,3),background:bg.slice(0,3),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)}
}

export async function readable(panel){
 const raw=await panel.evaluate(root=>{
  const rgb=v=>{const c=v.match(/[\d.]+/g)?.map(Number);if(!c||![3,4].includes(c.length))throw Error('UNMEASURED_FINANCE_COLOR:'+v);return c},out=[]
  for(const el of[root,...root.querySelectorAll('*')]){
   const s=getComputedStyle(el),label=[...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join(' ').trim()
   if(!label||!el.getClientRects().length||s.visibility!=='visible')continue
   const layers=[]
   for(let p=el;p;p=p.parentElement){
    const style=getComputedStyle(p)
    if(style.mixBlendMode!=='normal'||style.filter!=='none')throw Error('UNMEASURED_FINANCE_TEXT_SURFACE:'+JSON.stringify({label:label.slice(0,90),tag:p.tagName,classes:p.className,backgroundImage:style.backgroundImage,mixBlendMode:style.mixBlendMode,filter:style.filter}))
    layers.push({color:rgb(style.backgroundColor),opacity:Number(style.opacity),backgroundImage:style.backgroundImage})
   }
   out.push({label:label.slice(0,90),color:rgb(s.color),layers})
   if(el.hasAttribute('data-label')){const pseudo=getComputedStyle(el,'::before');if(pseudo.display!=='none'&&pseudo.content!=='none')out.push({label:el.getAttribute('data-label'),color:rgb(pseudo.color),layers:[{color:rgb(pseudo.backgroundColor),opacity:Number(pseudo.opacity),backgroundImage:pseudo.backgroundImage},...layers]})}
  }return out
 })
 const rows=raw.map(({label,color,layers})=>({label,...renderedTextContrast(color,layers)}))
 assert.ok(rows.length>0&&rows.every(x=>x.ratio>=4.5),JSON.stringify(rows.filter(x=>x.ratio<4.5)))
 return rows
}
