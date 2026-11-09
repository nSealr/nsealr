import { build } from 'esbuild';
import { cp, mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
const root = new URL('.', import.meta.url);
const output = new URL('./dist/', root);
await mkdir(output, { recursive: true });
const bundled = await build({ entryPoints: ['src/app.ts', 'extension/background.ts', 'extension/content.ts', 'extension/injected.ts'], entryNames: '[name]', outdir: 'dist', bundle: true, minify: true, sourcemap: false, target: ['chrome120', 'firefox128'], format: 'iife', legalComments: 'linked', metafile: true });
const dependencies = new Set();
for (const file of Object.keys(bundled.metafile.inputs)) {
  const parts = file.split('/'), at = parts.lastIndexOf('node_modules');
  if (at >= 0) dependencies.add(parts.slice(0, at + (parts[at + 1].startsWith('@') ? 3 : 2)).join('/'));
}
let notices = 'Bundled third-party source notices\n';
for (const directory of [...dependencies].sort()) {
  const metadata = JSON.parse(await readFile(`${directory}/package.json`, 'utf8'));
  notices += `\n${metadata.name} ${metadata.version}\n`;
  const names = (await readdir(directory)).filter(name => /^(licen[cs]e|copying|notice)(\.|$)/i.test(name));
  if (!names.length) throw Error(`Missing license notice: ${metadata.name}`);
  for (const name of names) notices += `\n${await readFile(`${directory}/${name}`, 'utf8')}\n`;
}
await writeFile('dist/THIRD_PARTY_LICENSES.txt', notices);
await cp('index.html', 'dist/index.html'); await cp('style.css', 'dist/app.css');
await cp('fonts', 'dist/fonts', { recursive: true });
const manifest = {
  manifest_version: 3, name: 'nSealr', version: '1.0.0', description: 'Review and sign Nostr requests on your offline nSealr.',
  action: { default_title: 'Open nSealr companion' },
  background: { service_worker: 'background.js' },
  content_scripts: [
    { matches: ['http://*/*', 'https://*/*'], js: ['injected.js'], world: 'MAIN', run_at: 'document_end', all_frames: false },
    { matches: ['http://*/*', 'https://*/*'], js: ['content.js'], run_at: 'document_end', all_frames: false },
  ],
  content_security_policy: { extension_pages: "script-src 'self'; object-src 'none'; base-uri 'none'" },
};
await writeFile('dist/manifest.json', JSON.stringify(manifest, null, 2) + '\n');
await mkdir('dist/firefox', { recursive: true });
for (const name of ['app.js', 'background.js', 'content.js', 'injected.js', 'index.html', 'app.css', 'fonts', 'THIRD_PARTY_LICENSES.txt']) await cp(`dist/${name}`, `dist/firefox/${name}`, { recursive: true });
for (const name of ['app.js.LEGAL.txt', 'background.js.LEGAL.txt', 'content.js.LEGAL.txt', 'injected.js.LEGAL.txt']) {
  try { await cp(`dist/${name}`, `dist/firefox/${name}`); } catch (error) { if (error.code !== 'ENOENT') throw error; }
}
await writeFile('dist/firefox/manifest.json', JSON.stringify({ ...manifest,
  background: { scripts: ['background.js'] },
  browser_specific_settings: { gecko: { id: 'companion@nsealr.com', strict_min_version: '128.0', data_collection_permissions: { required: ['none'] } } },
}, null, 2) + '\n');
const readme = await readFile('README.md', 'utf8');
const escaped = readme.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const help = `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>nSealr companion help</title><link rel="stylesheet" href="app.css"><main><a href="index.html">Back to companion</a><pre style="white-space:pre-wrap;font:14px/1.8 Inter,sans-serif">${escaped}</pre></main></html>`;
await writeFile('dist/README.html', help); await writeFile('dist/firefox/README.html', help);
console.log('Built browser app and Chromium/Firefox extension packages in dist/.');
