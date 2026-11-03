import path from 'node:path'
import fs from 'node:fs'
import {defineConfig} from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig(({command,mode})=>{
  if(command!=='serve'||mode!=='writer-b-connected-ui-fixture')throw Error('FIXTURE_CONFIG_SERVE_ONLY')
  const root=process.cwd(),dir=path.join(root,'scripts/ui-reference/connected-ui')
  const targets=new Map([[path.join(root,'src/auth/AuthProvider'),path.join(dir,'auth.ts')],[path.join(root,'src/lib/supabase'),path.join(dir,'client.ts')]])
  return {plugins:[{name:'explicit-ui-fixture-only',enforce:'pre',resolveId(source,importer){if(!importer||!source.startsWith('.'))return;return targets.get(path.resolve(path.dirname(importer.split('?')[0]),source).replace(/\.(tsx?|jsx?)$/,''))},configureServer(server){server.middlewares.use((req,res,next)=>{if(['/src/auth/AuthProvider.tsx','/src/lib/supabase.ts'].includes((req.url??'').split('?')[0])||((req.url??'').split('?')[0]!=='/tests/fixtures/productionRecovery.ts'&&!['/scripts/ui-reference/connected-ui/','/src/','/node_modules/','/@vite/','/@react-refresh','/@fs/'].some(prefix=>(req.url??'').startsWith(prefix)))){res.statusCode=403;res.end('Fixture entry only; product root unavailable.');return}next()})}},react()],optimizeDeps:{entries:[path.join(dir,'fixture.html')]},server:{host:'127.0.0.1',strictPort:true,fs:{allow:[root,fs.realpathSync(path.join(root,'node_modules'))]}},base:'/'}
})
