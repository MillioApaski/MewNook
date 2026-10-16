import test from 'node:test'
import assert from 'node:assert/strict'
import {readFile} from 'node:fs/promises'
import ts from 'typescript'

const source = await readFile(new URL('../src/inochi/companionActivity.ts', import.meta.url), 'utf8')
const js = ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.ES2022}}).outputText
const {companionActivity, speechDuration} = await import('data:text/javascript;base64,' + Buffer.from(js).toString('base64'))

test('new text temporarily overrides activity, then resumes the underlying state', () => {
  for (const [phase,running,night,expected] of [
    ['focus',true,false,'focus'], ['focus',true,true,'focus'],
    ['short',false,true,'rest'], ['long',true,false,'rest'],
    ['focus',false,true,'sleepy'], ['focus',false,false,'idle']
  ]) {
    assert.equal(companionActivity({phase,running,night,speaking:true}), 'chat')
    assert.equal(companionActivity({phase,running,night,speaking:false}), expected)
  }
})

test('viewing chat history does not imply speaking', () => {
  assert.equal(companionActivity({phase:'focus',running:true,night:false,speaking:false,chatExpanded:true}), 'focus')
})

test('text delivery has a bounded duration and ignores empty replies', () => {
  assert.equal(speechDuration('  '), 0)
  assert.equal(speechDuration('你好'), 1200)
  assert.equal(speechDuration('猫'.repeat(20)), 2200)
  assert.equal(speechDuration('🐈'.repeat(20)), 2200)
  assert.equal(speechDuration('猫'.repeat(1600)), 6500)
})
