import { readdir, readFile, rename, rm, stat, writeFile } from 'node:fs/promises'
import { join } from 'node:path'

const outputDir = join(process.cwd(), 'out')

// Chromium extensions reserve every path segment starting with "_". Next.js
// emits assets under `_next`, so rename the folder and rewrite all references.
await rename(join(outputDir, '_next'), join(outputDir, 'next-assets'))

async function rewriteAssetPaths(directory) {
  for (const entry of await readdir(directory)) {
    const path = join(directory, entry)
    if ((await stat(path)).isDirectory()) {
      await rewriteAssetPaths(path)
      continue
    }
    if (!/\.(?:html|js|css|json)$/.test(entry)) continue
    const content = await readFile(path, 'utf8')
    const rewritten = content.replaceAll('/_next/', '/next-assets/').replaceAll('./_next/', './next-assets/')
    if (rewritten !== content) await writeFile(path, rewritten, 'utf8')
  }
}

await rewriteAssetPaths(outputDir)

for (const page of ['popup.html', 'sidepanel.html']) {
  const path = join(outputDir, page)
  let html = await readFile(path, 'utf8')
  let index = 0
  const scripts = []
  html = html.replace(/<script([^>]*)>([\s\S]*?)<\/script>/g, (match, attributes, content) => {
    if (/\bsrc=/.test(attributes) || !content.trim()) return match
    const filename = `next-inline-${page.replace('.html', '')}-${index++}.js`
    scripts.push(writeFile(join(outputDir, filename), content, 'utf8'))
    return `<script${attributes} src="./${filename}"></script>`
  })
  await Promise.all(scripts)
  await writeFile(path, html, 'utf8')
}

// Static export also emits RSC payloads and route folders which extension pages
// do not request. Some of them start with `_`, so remove them from the package.
for (const entry of await readdir(outputDir)) {
  if (entry.startsWith('_') || entry.endsWith('.txt') || ['popup', 'sidepanel'].includes(entry)) {
    await rm(join(outputDir, entry), { recursive: true, force: true })
  }
}

async function removeReservedPaths(directory) {
  for (const entry of await readdir(directory)) {
    const path = join(directory, entry)
    if (entry.startsWith('_')) {
      await rm(path, { recursive: true, force: true })
    } else if ((await stat(path)).isDirectory()) {
      await removeReservedPaths(path)
    }
  }
}

await removeReservedPaths(outputDir)

console.log('Extension package ready in browser-extension/out')
