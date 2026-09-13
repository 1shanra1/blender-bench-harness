import { createHash } from 'node:crypto'
import { readFile, writeFile, mkdir, access } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import sharp from 'sharp'

const directory = path.resolve(process.argv[2] ?? fileURLToPath(new URL('../public/data/', import.meta.url)))
const cataloguePath = path.join(directory, 'results.json')
const catalogue = JSON.parse(await readFile(cataloguePath, 'utf8'))
await mkdir(path.join(directory, 'previews'), { recursive: true })
const cache = new Map()

async function preview(source, size) {
  if (!source) return null
  const key = `${source}:${size}`
  if (cache.has(key)) return cache.get(key)
  const sourcePath = path.resolve(directory, source)
  if (!sourcePath.startsWith(directory + path.sep)) throw new Error(`Non-local image: ${source}`)
  const bytes = await readFile(sourcePath)
  const hash = createHash('sha256').update(bytes).digest('hex').slice(0, 24)
  const destination = `previews/${hash}-${size}.webp`
  const output = path.join(directory, destination)
  try {
    await access(output)
  } catch {
    await sharp(bytes).rotate().resize(size, size, {
      fit: 'inside', withoutEnlargement: true,
    }).webp({ quality: 88 }).toFile(output)
  }
  cache.set(key, destination)
  return destination
}

// Originals remain available for enlargement. Decode only card-sized images
// during navigation, and bound every evolution frame (including final renders).
for (const experiment of catalogue.experiments) {
  experiment.reference_preview = await preview(experiment.reference, 960)
  for (const run of experiment.runs) {
    run.render_preview = await preview(run.render, 960)
    for (const frame of run.evolution ?? []) {
      frame.original_src ??= frame.src
      frame.src = await preview(frame.original_src, 640)
    }
  }
}
await writeFile(cataloguePath, `${JSON.stringify(catalogue, null, 2)}\n`)
console.log(`Prepared ${cache.size} bounded image previews; originals preserved.`)
