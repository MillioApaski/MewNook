import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import ts from 'typescript'
const source=await readFile(new URL('../src/inochi/characterSettings.ts',import.meta.url),'utf8')
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ES2022}}).outputText
const {characterDefaults,migrateCharacterSettings}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'))
test('new and old installations receive the approved source character',()=>{
 assert.equal(characterDefaults.inochiModel,'v4')
 assert.equal(characterDefaults.inochiTestMode,true)
 const next=migrateCharacterSettings({inochiModel:'v3',inochiTestMode:false,scene:'rain',nickname:'test'})
 assert.equal(next.inochiModel,'v4');assert.equal(next.inochiTestMode,true)
 assert.equal(next.scene,'rain');assert.equal(next.nickname,'test')
})
test('the once-only migration preserves subsequent user opt-out and model choices',()=>{
 const saved={...characterDefaults,inochiTestMode:false,inochiModel:'v3',inochiScale:.4}
 assert.equal(migrateCharacterSettings(saved),saved)
})
