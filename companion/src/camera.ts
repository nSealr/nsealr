import jsQR from 'jsqr';

export class Camera {
  private stream: MediaStream | null = null;
  private generation = 0;
  private canvas = document.createElement('canvas');
  private video: HTMLVideoElement;
  private onCode: (code: string) => void;
  private status: (message: string) => void;
  constructor(video: HTMLVideoElement, onCode: (code: string) => void, status: (message: string) => void) { this.video = video; this.onCode = onCode; this.status = status; }
  async start(deviceId?: string) {
    this.stop(); const generation = this.generation;
    if (!navigator.mediaDevices?.getUserMedia) throw Error('Camera access requires localhost or HTTPS.');
    const stream = await navigator.mediaDevices.getUserMedia({ video: deviceId ? { deviceId: { exact: deviceId } } : { facingMode: 'environment', width: { ideal: 1280 } }, audio: false });
    if (generation !== this.generation) { stream.getTracks().forEach(track => track.stop()); return; }
    this.stream = stream; this.video.srcObject = stream; await this.video.play();
    if (generation !== this.generation) return;
    this.status('Hold the response QR inside the camera view.');
    const context = this.canvas.getContext('2d', { willReadFrequently: true })!;
    let last = 0;
    const tick = (now: number) => {
      if (generation !== this.generation) return;
      if (now - last >= 120 && this.video.readyState >= 2) {
        last = now; const scale = Math.min(1, 1280 / this.video.videoWidth);
        this.canvas.width = Math.round(this.video.videoWidth * scale); this.canvas.height = Math.round(this.video.videoHeight * scale);
        context.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);
        const pixels = context.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const code = jsQR(pixels.data, pixels.width, pixels.height, { inversionAttempts: 'dontInvert' });
        if (code) this.onCode(code.data);
      }
      requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  stop() {
    this.generation++; this.stream?.getTracks().forEach(track => track.stop()); this.stream = null;
    this.video.srcObject = null; this.canvas.width = this.canvas.height = 0;
  }
}
