/* One-time source migration of shared CSS; never imported by the app.
 * Every changed declaration is retained in the source receipt. Remaining
 * module families and visual acceptance stay explicitly pending. */
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import postcss from 'postcss'

const root = process.cwd()
const base = JSON.parse(fs.readFileSync('docs/cp7/d17-14/ui-reference-20261103/UI_INVENTORY.json','utf8'))
const businessPagesOnly=process.argv.includes('--business-pages')
const files = businessPagesOnly ? ['src/business-pages.css'] : [
  'src/styles.css','src/auth/auth.css','src/brand-books.css','src/movement-book.css',
  'src/global-readability.css','src/procurement.css','src/laundry.css','src/workspace-refinements.css',
  'src/ux-corrections.css','src/wip-control.css','src/layout-resilience.css',
  'src/cutting-reminders.css','src/quick-ui-layout-fixes.css','src/wip-roll-operational.css',
  'src/enterprise-select.css','src/procurement-connected.css','src/payroll-connected.css',
  'src/mandor-shop.css','src/cp7/shell.css',
]
const hash = raw => crypto.createHash('sha256').update(raw).digest('hex')
const changes = []
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

for(const file of files) {
  const before=fs.readFileSync(file)
  const original=base.stylesheets.find(row=>row.path===file)
  if(!original||hash(before)!==original.sha256)throw Error('Theme migration requires exact inventoried source: '+file)
  const sheet=postcss.parse(before.toString(),{from:file})
  if(file==='src/styles.css')sheet.nodes.find(n=>n.type==='rule'&&n.selector===':root').walkDecls(d=>{if(d.prop.startsWith('--'))d.remove()})
  sheet.walkDecls(d=>{
    const selector=d.parent.type==='rule'?d.parent.selector:''
    const old=d.value
    if(d.prop==='color'&&/^(#|rgb|white|black)/i.test(old)) {
      const role=hueRole(old)
      d.value=primary(selector)||sidebar(selector)&&selected(selector)?'var(--on-accent)'
        :role?`var(--${role})`:/muted|hint|helper|caption|reference|small|note|label|placeholder|\bspan\b/.test(selector)?'var(--muted)':'var(--text)'
    } else if((d.prop==='background'||d.prop==='background-color')&&!sidebar(selector))d.value=background(old,selector)
    else if((d.prop==='background'||d.prop==='background-color')&&sidebar(selector)&&selected(selector))d.value='var(--blue)'
    else if(/^(border|border-(?:top|right|bottom|left)|border-color|border-(?:top|right|bottom|left)-color)$/.test(d.prop))d.value=old.replace(color,'var(--line)')
    else if(d.prop==='outline'||d.prop==='outline-color')d.value=old.replace(color,'var(--focus)')
    else if(d.prop==='box-shadow'&&old!=='none')d.value=/focus|\.open\b/.test(selector)?'0 0 0 3px var(--accent-bg)':'var(--shadow)'
    else if(d.prop==='font-size'&&/^\d*\.?\d+px$/.test(old)&&parseFloat(old)<13)d.value='13px'
    else if(d.prop==='font-size'&&/^\d*\.?\d+rem$/.test(old)&&parseFloat(old)<.8125)d.value='.8125rem'
    else if(d.prop==='opacity'&&/:disabled/.test(selector)&&Number(old)<1)d.value='1'
    if(d.prop.startsWith('--text-'))d.value=d.prop==='--text-body'?'15px':d.prop==='--text-control'||d.prop==='--text-number'?'14px':'13px'
    if(d.prop.startsWith('--line'))d.value=d.prop==='--line-strong'?'#cbd5e1':'#edf1f6'
    if(d.prop==='--cp7-muted')d.value='var(--muted)'
    if(d.prop==='--cp7-border')d.value='var(--line)'
    if(d.value!==old)changes.push({file,line:d.source.start.line,selector,property:d.prop,before:old,after:d.value,important:d.important===true})
  })
  const set=(selector,values)=>sheet.walkRules(r=>{if(r.selector===selector)for(const [prop,value]of Object.entries(values)){
    const old=r.nodes.find(n=>n.type==='decl'&&n.prop===prop)
    if(old){if(old.value!==value){changes.push({file,line:old.source.start.line,selector,property:prop,before:old.value,after:value});old.value=value}}
    else {r.append({prop,value});changes.push({file,selector,property:prop,before:null,after:value})}
  }})
  if(file==='src/styles.css') {
    set(':root',{color:'var(--text)',background:'var(--bg)','font-size':'16px','line-height':'1.5'})
    set('body',{background:'var(--bg)','font-size':'15px'})
    set('.sidebar',{background:'var(--sidebar-bg)','overflow-y':'auto','overscroll-behavior':'contain'})
    set('.topbar',{background:'var(--panel)','backdrop-filter':'none'})
    set('h1',{'font-size':'clamp(24px, 2.3vw, 32px)','line-height':'1.25'})
    set('.hero-copy.compact h1',{'font-size':'clamp(24px, 2.3vw, 32px)'})
    set('.primary-btn',{'min-height':'44px',background:'var(--blue)',color:'var(--on-accent)','box-shadow':'none'})
    set('.soft-btn',{'min-height':'44px'})
    set('.primary-btn:disabled',{background:'var(--disabled-bg)',color:'var(--muted)',opacity:'1'})
    set('.page-wrap',{padding:'28px clamp(16px, 3vw, 40px) 48px'})
  }
  if(file==='src/cp7/shell.css') {
    set('.cp7-shell',{color:'var(--text)',background:'var(--bg)'})
    set('.cp7-sidebar',{background:'var(--sidebar-bg)'})
  }
  if(file==='src/business-pages.css') {
    set('.biz-hero h1',{'font-size':'clamp(24px, 2.3vw, 32px)','line-height':'1.2'})
    set('.biz-search',{'height':'44px'})
    set('.biz-chart i.sales,.biz-performance footer i.sales',{background:'var(--blue)'})
    set('.biz-chart i.hpp,.biz-performance footer i.hpp',{background:'var(--cyan)'})
    sheet.walkDecls('color-scheme',d=>{if(d.value!=='light'){
      changes.push({file,line:d.source.start.line,selector:d.parent.selector,property:d.prop,before:d.value,after:'light'})
      d.value='light'
    }})
  }
  fs.writeFileSync(file,sheet.toString())
}
const main='src/main.tsx',before=fs.readFileSync(main,'utf8')
if(!businessPagesOnly){
  if(before.includes("import './theme.css'"))throw Error('Theme import already exists')
  fs.writeFileSync(main,before.replace("import './styles.css'","import './theme.css'\nimport './styles.css'"))
}
const receipt={contract:businessPagesOnly?'cp7.UI.business-pages-theme-source-migration.v1':'cp7.UI.shared-theme-source-migration.v1',
  status:businessPagesOnly?'BUSINESS_PAGES_THEME_IMPLEMENTED_VISUAL_RECHECK_PENDING':'SHARED_THEME_IMPLEMENTED_VISUAL_AND_REMAINING_FAMILIES_PENDING',
  base_head:base.base_head,files,changed_declarations:changes,source_only:true,new_important_declarations:0,
  existing_specificity_retained:true,financial_or_RPC_or_permission_changes:0,actual_visual_acceptance:false,CP7_complete:false,production_go:false}
fs.writeFileSync(businessPagesOnly?'docs/cp7/d17-14/ui-reference-20261103/BUSINESS_PAGES_THEME_SOURCE_CHANGES.json':
  'docs/cp7/d17-14/ui-reference-20261103/SHARED_THEME_SOURCE_CHANGES.json',JSON.stringify(receipt,null,2)+'\n')
console.log(JSON.stringify({status:receipt.status,stylesheets:files.length,changed_declarations:changes.length,new_important_declarations:0,financial_source_changes:0}))
