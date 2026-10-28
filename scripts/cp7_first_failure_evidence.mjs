import {writeFile} from 'node:fs/promises'

// Exclusive creation preserves the first writer. Other write errors stay visible.
export async function writeFirstFailure(path,bytes){
 try{await writeFile(path,bytes,{flag:'wx'});return true}
 catch(error){if(error?.code==='EEXIST')return false;throw error}
}
