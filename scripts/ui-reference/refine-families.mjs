/* B continuation of A's semantic CSS migration. Offline, exact 4620 inputs only. */
import fs from 'node:fs'
import crypto from 'node:crypto'
import {execFileSync} from 'node:child_process'
import postcss from 'postcss'
import {gzipSync} from 'node:zlib'
const base='462099c6cc59fa93766c81db66ec820b6cd54055'
const inventory=JSON.parse(fs.readFileSync('docs/cp7/d17-14/ui-reference-20261103/UI_INVENTORY.json'))
const prior=JSON.parse(execFileSync('git',['show',base+':docs/cp7/d17-14/ui-reference-20261103/UI_SOURCE.json']))
const files=inventory.stylesheets.map(x=>x.path).filter(x=>!prior.existing_UI_derivations[x])
if(files.length!==49)throw Error('B_REQUIRES_EXACT_REMAINING49_STYLESHEETS')
const changes=[],hash=raw=>crypto.createHash('sha256').update(raw).digest('hex')
const color = /#[\da-f]{3,8}\b|rgba?\([^)]*\)|\b(?:white|black)\b/gi
const status = selector => /error|danger|negative|critical|refus|fail|\.neg\b|overdue/.test(selector) ? 'danger'
  : /warn|pending|stale|blocked|caution|\bhold\b/.test(selector) ? 'warning'
  : /success|positive|\.good\b|\.pos\b|\.ok\b|\.paid\b|\.ready\b/.test(selector) ? 'success' : null
const sidebar = selector => /sidebar|nav-main|submenu|nav-caption|brand-row|brand-mark|env-card|env-dot|nav-close|cp7-brand|cp7-back/.test(selector)
const primary = selector => /primary-btn|cp7-primary|\.primary\b/.test(selector)
const selected = selector => /\.active\b|\.selected\b|sub-active|\[aria-selected/.test(selector)
const overlay = selector => /::backdrop|modal-backdrop|dialog-backdrop|nav-overlay|drawer-backdrop|^\.overlay\b/.test(selector)

function channels(value) {
  if (value.toLowerCase() === 'white') return [1,1,1]
  if (value.toLowerCase() === 'black') return [0,0,0]
  if (value[0] === '#') {
    let s=value.slice(1);if(s.length===3||s.length===4)s=[...s].map(x=>x+x).join('')
    return [0,2,4].map(i=>parseInt(s.slice(i,i+2),16)/255)
  }
  const parts=value.match(/[\d.]+/g)
  return parts && parts.length>=3 ? parts.slice(0,3).map(x=>Number(x)/255) : null
}

function hueRole(value) {
  const c=channels(value);if(!c)return null
  const [r,g,b]=c,max=Math.max(...c),min=Math.min(...c),d=max-min
  if(d<.15||max===0)return null
  let h=max===r?((g-b)/d)%6:max===g?(b-r)/d+2:(r-g)/d+4;h=(h*60+360)%360
  return h<25||h>=335?'red':h<90?'amber':h<175?'green':h<210?'cyan':'blue'
}

function background(value,selector) {
  if(overlay(selector)||/url\(/.test(value)||/^(none|transparent|inherit|initial|unset)$/.test(value))return value
  if(!color.test(value)){color.lastIndex=0;return value}color.lastIndex=0
  if(primary(selector)||sidebar(selector)&&selected(selector))return 'var(--blue)'
  if(selected(selector))return 'var(--accent-bg)'
  const kind=status(selector)
  if(kind)return `var(--${kind}-bg)`
  const colors=value.match(color)||[]
  const roles=colors.map(hueRole)
  if(roles.includes('green'))return 'var(--success-bg)'
  if(roles.includes('red'))return 'var(--danger-bg)'
  if(roles.includes('amber'))return 'var(--warning-bg)'
  return /hover/.test(selector)?'var(--panel-3)':'var(--panel)'
}


for(const file of files){
 const before=fs.readFileSync(file), original=execFileSync('git',['show',base+':'+file])
 if(hash(before)!==hash(original))throw Error('B_CSS_EXACT_4620_PREIMAGE_REQUIRED:'+file)
 const sheet=postcss.parse(before.toString(),{from:file})
 sheet.walkDecls(d=>{
  const selector=d.parent.type==='rule'?d.parent.selector:''
  const old=d.value, prop=d.prop
  if(prop==='color'&&['#352b26','#2f2723'].includes(old)&&file==='src/access-control-cp45.css'){
   // Retain the existing checked, dark readability colours on the access page.
  }else if(prop==='color'&&/^(#|rgb|white|black)/i.test(old)){
   const role=hueRole(old),kind=status(selector)
   d.value=primary(selector)?'var(--on-accent)':kind?`var(--${kind==='danger'?'red':kind==='warning'?'amber':'green'})`
    :/avatar|swatch|chip-icon/.test(selector)?'var(--on-accent)'
    :role&&/status|badge|pill|\.is-|\.active|\.selected|positive|negative|link|button|strong| em| svg/.test(selector)?`var(--${role})`
    :/muted|hint|helper|caption|reference|small|note|label|placeholder|meta/.test(selector)?'var(--muted)':'var(--text)'
  }else if(prop==='background'||prop==='background-color'){
   d.value=/avatar|swatch|chip-icon/.test(selector)&&color.test(old)?'var(--blue)':background(old,selector);color.lastIndex=0
  }else if(/^(border|border-(?:top|right|bottom|left)|border-color|border-(?:top|right|bottom|left)-color)$/.test(prop)){
   d.value=old.replace(color,/input|select|textarea|button|focus|\.open/.test(selector)?'var(--control-border)':'var(--line)')
  }else if(prop==='outline'||prop==='outline-color')d.value=old.replace(color,'var(--focus)')
  else if(prop==='box-shadow'&&old!=='none')d.value=/focus|\.open/.test(selector)?'0 0 0 3px var(--accent-bg)':'var(--shadow)'
  else if(prop==='font-family'&&/Georgia|serif/.test(old))d.value='inherit'
  else if(prop==='font-size'){
   const px=/^(\d*\.?\d+)(px|rem)$/.exec(old)
   if(px){const amount=Number(px[1])*(px[2]==='rem'?16:1)
    if(amount<13)d.value=/\btd\b|input|select|textarea/.test(selector)?'14px':'13px'
    else if(amount>32&&/h1/.test(selector))d.value='clamp(24px, 2.3vw, 32px)'
   }else if(/clamp\(/.test(old)&&/h1/.test(selector))d.value='clamp(24px, 2.3vw, 32px)'
  }else if(prop==='color-scheme')d.value='light'
  else if(prop==='opacity'&&/:disabled/.test(selector)&&Number(old)<1)d.value='1'
  else if(prop==='--surface')d.value='var(--panel)'
  else if(prop==='--border')d.value='var(--line)'
  else if(['--text','--soft','--muted','--line'].includes(prop))d.remove()
  if(d.value!==old||!d.parent)changes.push({file,line:d.source.start.line,selector,property:prop,before:old,after:d.parent?d.value:null,important:d.important===true})
 })
 fs.writeFileSync(file,sheet.toString())
}
fs.writeFileSync('docs/cp7/d17-14/ui-b-families-20261103/STYLE_CHANGES.json.gz',gzipSync(JSON.stringify({
 contract:'cp7.B.ui-family-source-migration.v1',base_head:base,files,changed_declarations:changes,
 source_migrated_files:files.length,new_important_declarations:0,actual_visual_acceptance:false,
 financial_or_RPC_or_permission_changes:0,production_go:false},null,2)+'\n',{mtime:0}))
console.log(JSON.stringify({migrated_files:files.length,declarations:changes.length,actual_visual_acceptance:false}))
