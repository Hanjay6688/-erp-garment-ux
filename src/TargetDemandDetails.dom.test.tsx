// @vitest-environment jsdom
import {act} from 'react'
import {createRoot} from 'react-dom/client'
import {expect,it} from 'vitest'
import TargetDemandDetails from './TargetDemandDetails'
import {parseTargetDemand} from './nativeTargetDemand'
import sql from '../tests/fixtures/nativeTargetDemandSql.json'
import modelSql from '../tests/fixtures/nativeModelTargetSql.json'

it('shows own sales separately from reviewed analog demand and then cleared UNKNOWN',async()=>{
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host)
 try{
  await act(async()=>root.render(<TargetDemandDetails value={parseTargetDemand(sql.analog,{targetKey:sql.analog.target_key})}/>))
  expect(host.textContent).toContain('Penjualan asli produk ini saat stok tersedia: 0 PCS dari 0 hari')
  expect(host.textContent).toContain('SOURCE · Produk pembanding');expect(host.textContent).toContain('1 ÷ 3 PCS/hari')
  expect(host.textContent).toContain('Ukuran fisik sama; pola penjualan diperiksa');expect(host.textContent).toContain('Target rencana: 1 PCS')
  await act(async()=>root.render(<TargetDemandDetails value={parseTargetDemand(sql.cleared,{targetKey:sql.cleared.target_key})}/>))
  expect(host.textContent).toContain('Pilihan pembanding sudah dicabut');expect(host.textContent).toContain('Target rencana: belum diketahui')
  expect(host.textContent).not.toContain('Target rencana: 0 PCS')
 }finally{await act(async()=>root.unmount());host.remove()}
})

it('shows dated model demand, historical comparison and policy withdrawal without rewriting sales',async()=>{
 const host=document.createElement('div');document.body.append(host);const root=createRoot(host)
 const show=async(key:keyof typeof modelSql.rows)=>{const p=modelSql.rows[key].demand_provenance;await act(async()=>root.render(<TargetDemandDetails value={parseTargetDemand(p,{targetKey:p.target_key})}/>))}
 try{
  await show('projected')
  expect(host.textContent).toContain('Target memakai perkiraan model');expect(host.textContent).toContain('Metode NAIVE; perkiraan 7 hari')
  expect(host.textContent).toContain('Penjualan asli produk ini saat stok tersedia: 5050 PCS dari 100 hari')
  expect(host.textContent).toContain('Target tanpa model: 202 PCS');expect(host.textContent).toContain('Target rencana: 400 PCS')
  await show('statistical');expect(host.textContent).toContain('variasi penjualan historis');expect(host.textContent).toContain('belum bukti')
  await show('withdrawn');expect(host.textContent).toContain('Kebijakan model berubah');expect(host.textContent).toContain('Target rencana: 202 PCS');expect(host.textContent).not.toContain('Target memakai perkiraan model')
  await show('unknown');expect(host.textContent).toContain('Target rencana: belum diketahui');expect(host.textContent).not.toContain('Target rencana: 0 PCS')
 }finally{await act(async()=>root.unmount());host.remove()}
})
