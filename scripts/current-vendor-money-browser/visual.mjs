// Reuse the qualified B comparator mathematics and 4.5 threshold; B source remains unchanged.
import assert from 'node:assert/strict'
async function readable(panel){
  const rows=await panel.evaluate(root=>{
    const rgb=v=>v.match(/[\d.]+/g).map(Number),lum=c=>c.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0),out=[]
    for(const el of[root,...root.querySelectorAll('*')]){
      const s=getComputedStyle(el),label=[...el.childNodes].filter(n=>n.nodeType===Node.TEXT_NODE).map(n=>n.textContent).join(' ').trim()
      if(!label||!el.getClientRects().length||s.visibility!=='visible')continue
      const layers=[];let bg=null
      for(let p=el;p;p=p.parentElement){const c=getComputedStyle(p),v=rgb(c.backgroundColor);if(c.backgroundImage!=='none'||c.opacity!=='1')throw Error('UNMEASURED_FINANCE_TEXT_SURFACE:'+JSON.stringify({label:label.slice(0,90),tag:p.tagName,classes:p.className,backgroundImage:c.backgroundImage,opacity:c.opacity}));if(v.length===3||v[3]===1){bg=v.slice(0,3);break}layers.push(v)}
      if(!bg)throw Error('MISSING_FINANCE_SURFACE')
      for(const v of layers.reverse())bg=bg.map((x,i)=>v[i]*(v[3]??1)+x*(1-(v[3]??1)))
      const record=(label,color)=>{const f=rgb(color),fg=bg.map((x,i)=>f[i]*(f[3]??1)+x*(1-(f[3]??1))),a=lum(fg),b=lum(bg);out.push({label:label.slice(0,90),ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)})}
      record(label,s.color)
      if(el.hasAttribute('data-label')){const pseudo=getComputedStyle(el,'::before');if(pseudo.display!=='none'&&pseudo.content!=='none')record(el.getAttribute('data-label'),pseudo.color)}
    }return out
  })
  assert.ok(rows.length>0&&rows.every(x=>x.ratio>=4.5),JSON.stringify(rows.filter(x=>x.ratio<4.5)))
  return rows
}
export {readable}
