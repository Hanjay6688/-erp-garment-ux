// Conservative bounds for this page's legacy sRGB CSS gradients. No pixel is
// sampled or guessed: every interpolated stop, group opacity and ancestor is
// enclosed. Unknown image/color/interpolation syntax remains an error.
// CSS Images 3 §3.4 and CSS Color 4 §12: legacy RGB uses premultiplied sRGB.
import assert from 'node:assert/strict'

const box=rgba=>{const a=rgba[3]??1;assert.ok(rgba.length>=3&&rgba.length<=4&&rgba.slice(0,3).every(x=>Number.isFinite(x)&&x>=0&&x<=255)&&Number.isFinite(a)&&a>=0&&a<=1,'INVALID_RGBA');const p=[...rgba.slice(0,3).map(x=>x*a),a];return{lo:p,hi:[...p]}}
const over=(f,b)=>({
 lo:[...f.lo.slice(0,3).map((x,i)=>x+b.lo[i]*(1-f.hi[3])),f.lo[3]+b.lo[3]*(1-f.lo[3])],
 hi:[...f.hi.slice(0,3).map((x,i)=>Math.min(255,x+b.hi[i]*(1-f.lo[3]))),f.hi[3]+b.hi[3]*(1-f.hi[3])],
})
function split(text){let depth=0,start=0,out=[];for(let i=0;i<text.length;i++){if(text[i]==='(')depth++;if(text[i]===')')depth--;if(depth<0)throw Error('UNMEASURED_FINANCE_BACKGROUND_IMAGE');if(text[i]===','&&depth===0){out.push(text.slice(start,i).trim());start=i+1}}if(depth!==0)throw Error('UNMEASURED_FINANCE_BACKGROUND_IMAGE');out.push(text.slice(start).trim());return out}
export function gradientBounds(image){
 const match=/^(?:linear|radial)-gradient\((.*)\)$/.exec(image)
 if(!match)throw Error('UNMEASURED_FINANCE_BACKGROUND_IMAGE')
 const parts=split(match[1])
 if(!/^rgba?\(/.test(parts[0])){
  // Direction/shape changes the position, not the enclosing color bounds.
  const direction=parts.shift()
  if(!/^[a-z\d.%+\s-]+$/i.test(direction)||direction.split(/[\s\d.%+-]+/).filter(Boolean).some(x=>!['deg','rad','turn','px','circle','ellipse','at','center','left','right','top','bottom','closest','farthest','side','corner','to'].includes(x)))throw Error('UNMEASURED_FINANCE_GRADIENT_DIRECTION')
 }
 if(parts.length<2)throw Error('UNMEASURED_FINANCE_BACKGROUND_IMAGE')
 const colors=parts.map(part=>{
  const m=/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)(?:\s+[-\d.]+(?:%|px)){0,2}$/.exec(part)
  if(!m)throw Error('UNMEASURED_FINANCE_GRADIENT_COLOR')
  return box([Number(m[1]),Number(m[2]),Number(m[3]),m[4]===undefined?1:Number(m[4])])
 })
 return{lo:[0,1,2,3].map(i=>Math.min(...colors.map(c=>c.lo[i]))),hi:[0,1,2,3].map(i=>Math.max(...colors.map(c=>c.hi[i])))}
}
const lum=c=>c.slice(0,3).map(x=>x/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4).reduce((s,x,i)=>s+x*[.2126,.7152,.0722][i],0)
export function boundedTextContrast(foreground,layers,solid){
 let fg=box(foreground),bg=box([0,0,0,0]),gradients=0
 for(const {color,opacity,backgroundImage='none'}of layers){
  if(!Number.isFinite(opacity)||opacity<0||opacity>1)throw Error('INVALID_TEXT_SURFACE_OPACITY')
  let surface=box(color)
  if(backgroundImage!=='none'&&(fg.lo[3]!==1||bg.lo[3]!==1)){
   // CSS paints the first listed image on top; `none` occupies one transparent
   // image layer. Preserve order and refuse every unknown contributing image.
   for(const image of split(backgroundImage).reverse())if(image!=='none'){surface=over(gradientBounds(image),surface);gradients++}
  }
  fg=over(fg,surface);bg=over(bg,surface)
  for(const v of[fg,bg])for(const key of['lo','hi'])v[key]=v[key].map(x=>x*opacity)
 }
 if(fg.lo[3]!==1||fg.hi[3]!==1||bg.lo[3]!==1||bg.hi[3]!==1)throw Error('MISSING_OPAQUE_FINANCE_CANVAS')
 if(!gradients)return solid(foreground,layers.map(layer=>({...layer,backgroundImage:split(layer.backgroundImage??'none').every(image=>image==='none')?'none':layer.backgroundImage})))
 // Account conservatively for 8-bit paint rounding at each contributing layer.
 const widen=v=>({min:v.lo.slice(0,3).map(x=>Math.max(0,x-layers.length)),max:v.hi.slice(0,3).map(x=>Math.min(255,x+layers.length))})
 const f=widen(fg),b=widen(bg),fl=lum(f.min),fh=lum(f.max),bl=lum(b.min),bh=lum(b.max)
 const ratio=fl>bh?(fl+.05)/(bh+.05):bl>fh?(bl+.05)/(fh+.05):1
 return{measurement:'CONSERVATIVE_ALL_GRADIENT_COLORS_LOWER_BOUND',foreground_range:f,background_range:b,ratio,
  ratio_upper_bound:Math.max((fh+.05)/(bl+.05),(bh+.05)/(fl+.05)),contributing_gradients:gradients}
}
