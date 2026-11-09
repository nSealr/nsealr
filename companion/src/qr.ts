import QRCode from 'qrcode';

export async function drawCode(canvas: HTMLCanvasElement, value: string, multipart: boolean): Promise<void> {
  const options = { version: multipart ? 19 : undefined, errorCorrectionLevel: 'M' as const, margin: 4 };
  const modules = QRCode.create(value, options).modules.size + 8;
  const container = canvas.closest('dialog')!, style = getComputedStyle(container);
  const available = Math.floor(container.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight));
  const scale = Math.max(1, Math.min(5, Math.floor(available / modules)));
  await QRCode.toCanvas(canvas, value, { ...options, scale, color: { dark: '#000000', light: '#ffffff' } });
  canvas.style.marginLeft = `${Math.max(0, Math.floor((available - canvas.width) / 2))}px`;
  canvas.style.marginRight = '0';
}
