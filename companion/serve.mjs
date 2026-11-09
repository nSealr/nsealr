import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname } from 'node:path';
const root = resolve(import.meta.dirname, 'dist');
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.woff2': 'font/woff2', '.txt': 'text/plain; charset=utf-8' };
createServer(async (request, response) => {
  try {
    if (request.method !== 'GET' || !['localhost:8787', '127.0.0.1:8787'].includes(request.headers.host)) throw Error();
    const path = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const file = resolve(root, `.${path === '/' ? '/index.html' : path}`);
    if (!file.startsWith(`${root}/`)) throw Error();
    const body = await readFile(file);
    response.writeHead(200, { 'Content-Type': types[extname(file)] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store', 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; media-src 'self' blob:; connect-src 'self' wss:; frame-ancestors 'none'; base-uri 'none'" });
    response.end(body);
  } catch { response.writeHead(404); response.end('Not found'); }
}).listen(8787, '127.0.0.1', () => console.log('nSealr companion: http://127.0.0.1:8787'));
