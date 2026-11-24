import {initialImportCatalog as catalog, initialImportTemplate, parseInitialImportCsv, MAX_IMPORT_BYTES, MAX_IMPORT_ROWS} from './initialImport';

const legibleError = message => { throw new Error(message) };
const organs = (xml,name) => Array.from(xml.getElementsByTagNameNS('*',name));
const clean = value => String(value ?? '').trim().toLocaleLowerCase('id-ID');
const quoted = value => '"' + value.replaceAll('"','""') + '"';
function excelColumn(ref) {
  const m=/^([A-Z]{1,3})[1-9]\d*$/.exec(ref);
  if(!m) return legibleError('Alamat sel Excel tidak dikenal.');
  return [...m[1]].reduce((n,c)=>n*26+c.charCodeAt(0)-64,0)-1;
}
function readXML(text) {
  const doc=new DOMParser().parseFromString(text,'application/xml');
  if(organs(doc,'parsererror').length) legibleError('Bagian isi Excel rusak.');
  return doc;
}
function stringText(node) {
  if(!node) return '';
  return organs(node,'t').filter(el=>!el.closest('rPh')).map(el=>el.textContent).join('');
}
function readCell(cell,strings) {
  const type=cell.getAttribute('t')||'n';
  const value=organs(cell,'v')[0]?.textContent??'';
  if(organs(cell,'f').length || type==='e') legibleError('ada rumus atau nilai galat. Tempel hasilnya sebagai nilai.');
  if(type==='s') {
    if(!/^\d+$/.test(value)||Number(value)>=strings.length) legibleError('referensi teks Excel rusak.');
    return {value:strings[Number(value)],type:'text'};
  }
  if(type==='inlineStr')return {value:stringText(cell),type:'text'};
  if(type==='b')return {value:value==='1'?'true':'false',type:'text'};
  return {value,type};
}
function workbookDate(value,system1904) {
  if(!/^\d+$/.test(value))legibleError('gunakan tanggal tanpa waktu, misalnya 2026-11-24.');
  const serial=Number(value);
  if(serial<0 || serial>2957003 || (!system1904 && serial===60))legibleError('tanggal Excel di luar rentang.');
  const base=system1904?Date.UTC(1904,0,1):Date.UTC(1899,11,serial<60?31:30);
  return new Date(base+serial*86400000).toISOString().slice(0,10);
}
function normalizedValue(cell,key,system1904) {
  let {value,type}=cell;value=value.trim();
  if(!value) return '';
  if(/(^|_)date$/.test(key)) {
    if(type==='n')return workbookDate(value,system1904);
    if(type==='d' && /^\d{4}-\d{2}-\d{2}T00:00:00(\.0+)?Z?$/.test(value))value=value.slice(0,10);
    const d=new Date(value+'T00:00:00Z');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(value)||Number.isNaN(d.valueOf())||d.toISOString().slice(0,10)!==value)legibleError('gunakan tanggal YYYY-MM-DD.');
  }
  const ident=/(^sku$|_sku$|_code$|_key$|_id$|^phone$|_number$)/.test(key) && !/(^|_)line_number$/.test(key);
  if(ident && type==='n')legibleError('kode atau nomor tersimpan sebagai angka. Cocokkan dengan sumber dan tempel sebagai teks agar nol depan terjaga.');
  if(type==='n' && /e/i.test(value))legibleError('angka dalam notasi ilmiah. Tempel angka persis sebagai teks.');
  if(/^[=\u0001-\u0008\u000b\u000c\u000e-\u001f]/u.test(value))legibleError('nilai menyerupai rumus atau berisi karakter kontrol.');
  return value;
}
export async function convertWorkbook(input,mapping,zipLib) {
  const zip=await zipLib.loadAsync(input);
  const objects=Object.values(zip.files);
  if(objects.length>1500 || objects.reduce((s,f)=>s+(f._data?.uncompressedSize??0),0)>160*1024*1024)legibleError('Workbook terlalu besar untuk pemeriksaan lokal. Gunakan salinan dengan data yang diperlukan.');
  async function xmlAt(name){
    const entry=zip.file(name);
    if(!entry)legibleError('Bagian workbook tidak ditemukan. Gunakan file XLSX dari template.');
    return readXML(await entry.async('string'));
  }
  const workbook=await xmlAt('xl/workbook.xml'), rels=await xmlAt('xl/_rels/workbook.xml.rels');
  const date1904=['1','true'].includes(organs(workbook,'workbookPr')[0]?.getAttribute('date1904'));
  const relationships=new Map(organs(rels,'Relationship').filter(e=>e.getAttribute('TargetMode')!=='External').map(e=>[e.getAttribute('Id'),new URL(e.getAttribute('Target'),'https://xlsx.local/xl/workbook.xml').pathname.slice(1)]));
  const strings=zip.file('xl/sharedStrings.xml')?organs(await xmlAt('xl/sharedStrings.xml'),'si').map(stringText):[];
  const byTab=new Map(Object.entries(mapping).map(([k,[tab]])=>[clean(tab),k]));
  const errors=[],files=[],seen=new Set();
  let errorCount=0, recognized=0;
  function issue(message){errorCount++;if(errors.length<30)errors.push(message)}
  for(const node of organs(workbook,'sheet')){
    const name=node.getAttribute('name'),key=byTab.get(clean(name));
    if(['mulai','daftar tab'].includes(clean(name)))continue;
    const rid=node.getAttributeNS('http://schemas.openxmlformats.org/officeDocument/2006/relationships','id')??node.getAttribute('r:id');
    const sheet=await xmlAt(relationships.get(rid)), rows=organs(sheet,'row');
    if(!key){
      if(rows.some(r=>organs(r,'c').some(c=>organs(c,'v').length||organs(c,'is').length||organs(c,'f').length)))issue('Tab “'+name+'” belum dipetakan. Salin data ke tab template yang sesuai.');
      continue;
    }
    recognized++;
    if(seen.has(key)){issue('Nama tab “'+name+'” ganda.');continue}seen.add(key);
    const spec=catalog[key], fields=Object.keys(spec.fields);
    const aliases=new Map(Object.entries(spec.fields).flatMap(([k,l])=>[[clean(k),k],[clean(l),k]]));
    const headers=new Map(), headerKeys=new Set(), lines=[], firstError=errorCount;
    const csvRows=[],exact=new Map();
    const header=rows.find(r=>r.getAttribute('r')==='1');
    if(!header){issue(name+' · judul kolom baris 1 belum ada.');continue;}
    for(const c of organs(header,'c')){
      try{
        const label=readCell(c,strings).value.trim();if(!label)continue;
        const field=aliases.get(clean(label));
        if(!field||headerKeys.has(field))throw Error('judul kolom tidak dikenal atau ganda ('+label+').');
        headers.set(excelColumn(c.getAttribute('r')),field);headerKeys.add(field);
      }catch(e){issue(name+' · '+c.getAttribute('r')+' · '+e.message)}
    }
    for(const k of spec.required)if(!headerKeys.has(k))issue(name+' · judul wajib “'+spec.fields[k]+'” belum ada.');
    if(errorCount!==firstError)continue;
    for(const row of rows){
      const line=Number(row.getAttribute('r'));if(line===1)continue;
      let used=false; const values={}; const before=errorCount;
      for(const c of organs(row,'c')){
        const ref=c.getAttribute('r');
        try{
          const val=readCell(c,strings);if(!val.value.trim())continue;
          used=true;const field=headers.get(excelColumn(ref));
          if(!field)throw Error('ada nilai di luar kolom template.');
          values[field]=normalizedValue(val,field,date1904);
        }catch(e){issue(name+' · '+ref+' · '+e.message)}
      }
      if(!used || errorCount!==before)continue;
      const missing=spec.required.filter(k=>!values[k]);
      if(missing.length){issue(name+' · baris '+line+' · wajib diisi: '+missing.map(k=>spec.fields[k]).join(', ')+'.');continue}
      const encoded=fields.map(k=>quoted(values[k]??'')).join(',');
      if(exact.has(encoded)){issue(name+' · baris '+line+' sama persis dengan baris '+exact.get(encoded)+'. Cocokkan kedua baris dengan sumber.');continue}
      exact.set(encoded,line);lines.push(line);csvRows.push(encoded);
      if(csvRows.length>MAX_IMPORT_ROWS){issue(name+' · lebih dari 5.000 baris. Satu unggahan ERP mengganti seluruh jenis ini. Perlu jalur volume besar sebelum dimuat.');break}
    }
    if(errorCount!==firstError || !csvRows.length)continue;
    const csv=initialImportTemplate(key)+csvRows.join('\r\n')+'\r\n';
    try{
      if(new TextEncoder().encode(csv).length>MAX_IMPORT_BYTES)throw Error('CSV melebihi 5 MiB untuk satu jenis.');
      const actual=parseInitialImportCsv(csv,key);
      if(actual.length!==lines.length)throw Error('jumlah baris berubah saat dibaca ERP.');
      files.push({key,name,rows:actual.length,csv,lines});
    }catch(e){issue(name+' · '+e.message)}
  }
  if(!recognized&&!errorCount)issue('Nama tab belum cocok dengan template.');
  return {files:errorCount?[]:files,errors,errorCount};
}
export async function pack(result,zipLib) {
  if(result.errorCount || !result.files.length)throw Error('Belum ada CSV yang siap diunduh.');
  const zip=new zipLib();
  for(const f of result.files)zip.file(f.key+'.csv',f.csv);
  zip.file('baris-asal.json',JSON.stringify(Object.fromEntries(result.files.map(f=>[f.key,{tab:f.name,baris_excel_dalam_urutan_csv:f.lines}])),null,2));
  return zip.generateAsync({type:'uint8array',compression:'DEFLATE'});
}
