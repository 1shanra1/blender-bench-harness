import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import sharp from 'sharp'

test('previews bound decoded sizes, preserve originals and statistics, and are repeatable', async () => {
  const directory = await mkdtemp(path.join(tmpdir(), 'meshmatch-previews-'))
  try {
    const image = await sharp({ create: { width: 2560, height: 1280, channels: 3, background: '#ffaa00' } }).png().toBuffer()
    await writeFile(path.join(directory, 'render.png'), image)
    const run = { render: 'render.png', elapsed_seconds: 5400, usage: { tokens: 12345 }, evolution: [{ src: 'render.png', final: true, elapsed_seconds: 5400 }] }
    await writeFile(path.join(directory, 'results.json'), JSON.stringify({ experiments: [{ reference: 'render.png', runs: [run] }] }))
    const prepare = () => execFileSync(process.execPath, [fileURLToPath(new URL('./prepare-previews.mjs', import.meta.url)), directory])
    prepare()
    const first = await readFile(path.join(directory, 'results.json'), 'utf8')
    const experiment = JSON.parse(first).experiments[0]
    const result = experiment.runs[0]
    assert.equal(result.render, run.render)
    assert.equal(result.elapsed_seconds, run.elapsed_seconds)
    assert.deepEqual(result.usage, run.usage)
    assert.deepEqual(await readFile(path.join(directory, 'render.png')), image)
    assert.equal((await sharp(path.join(directory, result.render_preview)).metadata()).width, 960)
    assert.equal((await sharp(path.join(directory, result.evolution[0].src)).metadata()).width, 640)
    assert.equal(result.evolution[0].elapsed_seconds, 5400)
    prepare()
    assert.equal(await readFile(path.join(directory, 'results.json'), 'utf8'), first)
  } finally {
    await rm(directory, { recursive: true, force: true })
  }
})
