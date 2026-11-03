import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {measureSolidText,readable} from './contrast.mjs';

function panel(html){
 const dom=new JSDOM(`<html style="background:white"><body>${html}</body></html>`);
 globalThis.Node=dom.window.Node;
 globalThis.getComputedStyle=element=>{
  const style=dom.window.getComputedStyle(element);
  // jsdom has no layout and omits initial values; these explicit test defaults
  // are never used in the browser measurement.
  return{color:style.color||'rgb(0, 0, 0)',backgroundColor:style.backgroundColor||'rgba(0, 0, 0, 0)',visibility:style.visibility||'visible',opacity:style.opacity||'1',backgroundImage:style.backgroundImage||'none',filter:style.filter||'none',mixBlendMode:style.mixBlendMode||'normal',backdropFilter:style.backdropFilter||'none'};
 };
 for(const el of dom.window.document.querySelectorAll('*'))el.getClientRects=()=>[{}];
 return dom.window.document.body;
}
const near=(a,b)=>a.forEach((x,i)=>assert(Math.abs(x-b[i])<1e-8,JSON.stringify({a,b})));
let root=panel('<span style="color:black;opacity:.8">Fisik</span>');
let row=measureSolidText(root).rows[0];near(row.foreground,[51,51,51]);near(row.background,[255,255,255]);assert(row.ratio>12);
root=panel('<div style="background:black;opacity:.5"><span style="color:white;opacity:.5">Nested group</span></div>');
row=measureSolidText(root).rows[0];near(row.foreground,[191.25,191.25,191.25]);near(row.background,[127.5,127.5,127.5]);assert(row.ratio<4.5);
await assert.rejects(()=>readable({evaluate:fn=>fn(root)}),/SKU_TEXT_CONTRAST_BELOW_4_5/);
root=panel('<span style="color:rgba(0,0,0,.5);background:rgba(255,0,0,.5);opacity:.5">Alpha</span>');
row=measureSolidText(root).rows[0];near(row.foreground,[191.25,159.375,159.375]);near(row.background,[255,191.25,191.25]);
root=panel('<span style="background:linear-gradient(white,black);color:black">Gradient</span>');
assert.throws(()=>measureSolidText(root),/UNMEASURED_SKU_TEXT_SURFACE/);
root=panel('<span style="filter:blur(1px);color:black">Filtered</span>');
assert.throws(()=>measureSolidText(root),/UNMEASURED_SKU_TEXT_SURFACE/);
root=panel('<span style="color:black;opacity:0">Invisible</span>');
await assert.rejects(()=>readable({evaluate:fn=>fn(root)}),/SKU_TEXT_CONTRAST_BELOW_4_5/);
console.log(JSON.stringify({status:'PASS',controls:6,actual_browser_cases:0,actual_ERP_cases:0}));
