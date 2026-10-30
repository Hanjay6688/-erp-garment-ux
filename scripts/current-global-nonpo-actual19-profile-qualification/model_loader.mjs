/** Route only the frozen local model, never a product module or source reader. */
const frozen=new URL('../current-global-nonpo-native-graph-qualification/model.mjs',import.meta.url).href;
const successor=new URL('./model_profile.mjs',import.meta.url).href;
export async function resolve(specifier,context,nextResolve){
 const answer=await nextResolve(specifier,context);
 return answer.url===frozen?{...answer,url:successor}:answer;
}
