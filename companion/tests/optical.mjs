import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import QRCode from 'qrcode';
import jsQR from 'jsqr';

export async function fixtureCamera(context) {
  await context.addInitScript(() => {
    window.__testQRImages = [];
    window.__testTracks = [];
    if (!navigator.mediaDevices) return;
    Object.defineProperty(navigator.mediaDevices, 'enumerateDevices', { configurable: true, value: async () => [{ kind: 'videoinput', deviceId: 'pixels', label: 'QR pixel stream', groupId: 'test' }] });
    Object.defineProperty(navigator.mediaDevices, 'getUserMedia', { configurable: true, value: async () => {
      if (!window.__testQRImages.length) throw Error('No test QR pixels supplied.');
      const images = await Promise.all(window.__testQRImages.map(source => new Promise(resolve => { const image = new Image(); image.onload = () => resolve(image); image.src = source; })));
      const canvas = document.createElement('canvas'); canvas.width = canvas.height = 512;
      const ctx = canvas.getContext('2d'); let index = 0;
      const draw = () => { ctx.fillStyle = 'white'; ctx.fillRect(0, 0, 512, 512); ctx.drawImage(images[index++ % images.length], 0, 0, 512, 512); };
      draw(); const timer = setInterval(draw, 350); const stream = canvas.captureStream(15);
      for (const track of stream.getTracks()) { const stop = track.stop.bind(track); track.stop = () => { clearInterval(timer); stop(); }; window.__testTracks.push(track); }
      return stream;
    } });
  });
}
export async function opticalFromPixels(page, options = {}) {
    await page.locator(`${options.dialog ?? '#operation'}[open]`).waitFor();
    const chunks = new Map(), encoded = new Map(); let id, total;
    for (let attempt = 0; attempt < 360; attempt++) {
      const pixels = await page.locator(options.canvas ?? '#request-qr').evaluate(canvas => ({ data: [...canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data], width: canvas.width, height: canvas.height }));
      const qr = jsQR(Uint8ClampedArray.from(pixels.data), pixels.width, pixels.height);
      if (qr && qr.data.split(':')[1] !== options.previousDigest) {
        const parts = qr.data.split(':'); assert.equal(parts[0], 'ns');
        id ??= parts[1]; total ??= Number(parts[3]); assert.equal(parts[1], id); assert.equal(Number(parts[3]), total);
        chunks.set(Number(parts[2]), Buffer.from(parts[4], 'base64url'));
        encoded.set(Number(parts[2]), qr.data);
        if (chunks.size === total) {
          const message = Buffer.concat(Array.from({ length: total }, (_, index) => chunks.get(index)));
          assert.equal(createHash('sha256').update(message).digest('hex'), id);
          return { request: JSON.parse(message.toString('utf8')), frames: Array.from({ length: total }, (_, index) => encoded.get(index)) };
        }
      }
      await page.waitForTimeout(150);
    }
    throw Error('Could not decode the displayed request pixels.');
  }
export async function requestFromPixels(page) { return (await opticalFromPixels(page)).request; }
export async function scanResponse(page, request, result) {
    const message = Buffer.from(JSON.stringify({ id: request.id, result: typeof result === 'string' ? result : JSON.stringify(result) }));
    const digest = createHash('sha256').update(message).digest('hex'), count = Math.ceil(message.length / 384);
    return scanFrames(page, Array.from({ length: count }, (_, index) => `ns:${digest}:${index}:${count}:${message.subarray(index * 384, (index + 1) * 384).toString('base64url')}`));
  }
export async function scanFrames(page, frames, button = 'Scan device response') {
    const codes = await Promise.all(frames.map(frame => QRCode.toDataURL(frame, { width: 512, margin: 4, errorCorrectionLevel: 'M' })));
    await page.evaluate(images => { window.__testQRImages = images; }, codes);
    await page.getByRole('button', { name: button, exact: true }).click();
    // A private-message chain can immediately open its next request.
    await page.locator('#camera').waitFor({ state: 'hidden', timeout: 60000 });
    assert.equal(await page.evaluate(() => window.__testTracks.every(track => track.readyState === 'ended')), true);
  }
