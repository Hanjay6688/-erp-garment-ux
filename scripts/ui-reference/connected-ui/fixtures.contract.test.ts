// @vitest-environment jsdom
import {describe,it,expect} from 'vitest'
import {parsePocketWorkspace,parsePocketPreview} from '../../../src/ConnectedPocketFabricPage'
import {parseInitialImportWorkspace} from '../../../src/ConnectedInitialImportPage'
import {parseCutoverWorkspace} from '../../../src/cutoverContract'
import {states,pocketData,importData,cutoverData,periodPreview} from './data'
describe('connected UI doubles use unchanged public parsers',()=>{
 it('all ready/long/empty fixture payloads satisfy both real workspace contracts',()=>{for(const state of states){expect(()=>parsePocketWorkspace(pocketData(state))).not.toThrow();for(const selected of [false,true])expect(()=>parseInitialImportWorkspace(importData(state,selected))).not.toThrow()}})
 it('period preview and cutover satisfy real closed contracts',()=>{expect(parsePocketPreview(periodPreview).per_piece).toBe('1.125000');expect(parseCutoverWorkspace(cutoverData).version).toBe(1)})
 it('missing required import collections and non-string stock remain refused',()=>{const batch=importData('ready',true).batch!;const broken={...batch,cash_advances:undefined};expect(()=>parseInitialImportWorkspace({recent:[],batch:broken})).toThrow();const pocket=pocketData('ready');expect(()=>parsePocketWorkspace({...pocket,rolls:[{...pocket.rolls[0],qty:20}]})).toThrow()})
})
