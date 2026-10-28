import assert from 'node:assert/strict'

// Retain every console error. Only the exact browser-generated network message
// paired with a deliberately lost response or verified denial is expected.
export function observeConsole(page){
 const errors=[]
 const listener=message=>{if(message.type()==='error')errors.push({text:message.text(),location:message.location()})}
 page.on('console',listener)
 return {errors,stop:()=>page.off('console',listener)}
}

export function requireConsoleEvidence(errors,expectedNetwork){
 const remaining=expectedNetwork.map(item=>({...item})),expected=[],unexpected=[]
 for(const error of errors){
  const index=remaining.findIndex(item=>item.url===error.location.url&&item.text===error.text)
  if(index<0)unexpected.push(error)
  else expected.push({...error,reason:remaining.splice(index,1)[0].reason})
 }
 assert.deepEqual(unexpected,[],'UNEXPECTED_BROWSER_CONSOLE_ERROR')
 return {observed:errors,expected_network_errors:expected,unexpected_errors:unexpected}
}
