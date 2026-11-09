import { drawCode } from './qr.ts';
import { Ceremony, groupRecord } from './threshold.ts';
import type { Group } from './threshold.ts';
import { Collector, frames } from './frames.ts';
import type { Operation, Owner } from './owner.ts';
import { npub } from './protocol.ts';

export function thresholdUI(owner: Owner, scan: () => Promise<void>, selectIdentity: (key: string) => void, closeCamera: () => void) {
  const get = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
  const modal = get<HTMLDialogElement>('threshold-operation');
  const collector = new Collector();
  const captured = new Set<string>();
  let group: Group | null = null, ceremony: Ceremony | null = null, importing = false, completing = false;
  let encoded: string[] = [], displayed = '', frame = 0, paused = false;
  const status = (message: string) => { get('group-status').textContent = message; };
  const error = (reason: unknown) => reason instanceof Error ? reason.message : 'Threshold operation failed.';
  const lock = () => { if (owner.operation || owner.reserved) throw Error('Finish or cancel the current operation first.'); collector.clear(); captured.clear(); owner.reserved = true; };
  function cancel(reason?: string, cancelOwner = true) {
    const repairing = ceremony?.mode === 'repair';
    reason ??= repairing ? 'Repair cancelled.' : 'Ceremony cancelled. Cancel it on every participating device before starting again.';
    if (repairing) {
      group = null; get('group-details').hidden = true; get<HTMLTextAreaElement>('group-record').value = '';
      reason += ' Keep all backups. Cancel on every device and compare public group records. If two agree, keep that pair loaded, load its record here and repair the inconsistent third with a fresh join. If all three agree, save new backups. See the companion guide if no matching pair remains.';
    }
    ceremony?.cancel(); ceremony = null; importing = false; collector.clear(); captured.clear(); encoded = []; displayed = '';
    owner.reserved = false; modal.close(); closeCamera();
    const canvas = get<HTMLCanvasElement>('threshold-qr'); canvas.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height);
    if (cancelOwner) owner.cancel(reason); status(reason);
  }
  function loadGroup(raw: string) {
    const record = groupRecord(raw); group = { group: record.group, pubkey: record.pubkey, descriptor: record.descriptor, members: record.members };
    get<HTMLTextAreaElement>('group-record').value = raw;
    const list = get('group-members'); list.replaceChildren();
    for (const { id, key } of group.members) {
      const label = document.createElement('label'), checkbox = document.createElement('input'), description = document.createElement('span');
      checkbox.type = 'checkbox'; checkbox.value = key; checkbox.checked = id < 3;
      description.textContent = `Member ${id} · ${key}`; label.append(checkbox, description); list.append(label);
    }
    get('group-details').hidden = false; selectIdentity(group.pubkey);
    status(`Group selected: ${npub(group.pubkey)}. Choose two available members before signing. Compare its fingerprint on the devices.`);
  }
  function draw() {
    if (!encoded.length) return;
    frame %= encoded.length;
    get('threshold-frame').textContent = `${frame + 1} / ${encoded.length}`;
    void drawCode(get<HTMLCanvasElement>('threshold-qr'), encoded[frame], encoded.length > 1).catch(reason => cancel(error(reason)));
  }
  function render() {
    if (!ceremony && !importing) return;
    if (!modal.open) modal.showModal();
    get('threshold-origin').textContent = ceremony?.mode === 'sign' ? owner.operation?.origin ?? '' : ceremony?.mode === 'repair' ? 'Local lost-share recovery' : 'Local group setup';
    const current = ceremony?.current;
    const raw = current?.raw ?? '';
    if (raw !== displayed) { displayed = raw; encoded = raw ? frames(raw) : []; frame = 0; paused = false; get('threshold-pause').textContent = 'Pause'; draw(); }
    get('threshold-code').hidden = !encoded.length;
    get('threshold-delivered').hidden = !ceremony?.delivering;
    get('threshold-scan').hidden = !!ceremony?.delivering;
    get('threshold-fingerprint').textContent = ceremony && ceremony.phase !== 'joins' ? `Compare on devices: ${ceremony.fingerprint}` : '';
    const title = get('threshold-title'), instruction = get('threshold-instruction'), progress = get('threshold-progress');
    if (importing) {
      title.textContent = 'Load a public group'; instruction.textContent = 'Scan the public group record from a participant device. Never scan a share backup into this computer.'; progress.textContent = ''; return;
    }
    const c = ceremony!;
    title.textContent = c.mode === 'setup' ? 'Create a 2-of-3 group' : c.mode === 'repair' ? `Replace lost member ${c.lost}` : 'Sign with two devices';
    if (c.delivering) {
      const index = c.memberNumber(current!.recipient!);
      instruction.textContent = `On member ${index}, scan this packet. Check that the device accepts it, then choose Next packet. A click here only records your progress.`;
      progress.textContent = `${c.phase}: packet ${c.deliveryNumber} of ${c.expected} · recipient ${current!.recipient}`;
    } else if (c.phase === 'joins') {
      instruction.textContent = c.mode === 'repair' ? 'Keep the two surviving shares loaded. On the replacement, choose Tools → Restore a group share → Repair lost share → Join repair. Scan its public join code here. Old copies of the lost share remain valid; this does not revoke a stolen share.' : 'On each of three devices, choose Tools → 2-of-3 signing group → Start group. Scan each device’s public join code here. Keep all three devices ready.';
      progress.textContent = c.mode === 'repair' ? 'One fresh replacement join code required.' : `${c.count} of 3 distinct join codes collected.`;
    } else if (c.phase === 'setup1') {
      instruction.textContent = 'Scan this setup request on all three devices. Compare the complete fingerprint and approve on each device. Then scan both encrypted outputs from every device here.'; progress.textContent = `${c.count} of 6 signed setup packets collected.`;
    } else if (c.phase === 'setup2') {
      instruction.textContent = 'Scan both new encrypted outputs from each of the three devices. All six are required before routing the next phase.'; progress.textContent = `${c.count} of 6 signed setup packets collected.`;
    } else if (c.phase === 'groups') {
      instruction.textContent = c.mode === 'repair' ? 'Scan the new public group record from the replacement and both helpers. All three must agree and preserve the same npub. Keep old backups until this completes, then save new backups from all three devices.' : 'Scan the final public group record from each device. All three must agree on the identity, fingerprint and membership. Back up each share directly from its device.'; progress.textContent = `${c.count} of 3 matching public group records collected.`;
    } else if (c.phase === 'repair_delta') {
      instruction.textContent = 'Scan this repair request on the replacement. On both surviving devices, choose Scan a request and scan it too. Compare the complete fingerprint and approve on all three. Scan the encrypted output from each helper here; the replacement waits for contributions.'; progress.textContent = `${c.count} of 2 signed helper packets collected.`;
    } else if (c.phase === 'repair_sigma') {
      instruction.textContent = 'Scan the new encrypted output from each helper. Both contributions must be collected before routing them to the replacement.'; progress.textContent = `${c.count} of 2 signed contribution packets collected.`;
    } else if (c.phase === 'repair_ready') {
      instruction.textContent = 'Scan both encrypted confirmation packets from the replacement. Its third output is the public group record; keep it for the next step. Route both confirmations before collecting final records.'; progress.textContent = `${c.count} of 2 signed replacement packets collected.`;
    } else if (c.phase === 'commitment') {
      instruction.textContent = 'Scan this exact event request on both selected devices. Review the event and cosigner on each. Then scan each device’s encrypted commitment here.'; progress.textContent = `${c.count} of 2 signed commitments collected.`;
    } else if (c.phase === 'share') {
      instruction.textContent = 'Scan each selected device’s new encrypted share packet. Both authenticated packets are required before continuing.'; progress.textContent = `${c.count} of 2 signed share packets collected.`;
    } else {
      instruction.textContent = 'Scan the final signed-event response from either participating device. It must match the original request, group identity and exact event.'; progress.textContent = 'Both authenticated commitment and share phases were routed.';
    }
  }
  const action = (id: string, run: () => unknown) => get(id).addEventListener('click', () => { Promise.resolve().then(run).catch(reason => { if (ceremony || importing) cancel(error(reason)); else status(error(reason)); }); });
  action('group-create', () => { lock(); ceremony = new Ceremony(); render(); });
  action('group-load', () => { lock(); importing = true; render(); });
  action('group-repair', () => { if (!group) throw Error('Load the current public group record first.'); const next = new Ceremony({ group, lost: Number(get<HTMLSelectElement>('group-lost').value) }); lock(); ceremony = next; render(); });
  action('group-clear', () => { if (ceremony || importing) cancel(); group = null; get('group-details').hidden = true; get<HTMLTextAreaElement>('group-record').value = ''; status('Group routing removed. Select the ordinary identity you want to use.'); });
  action('threshold-scan', scan);
  action('threshold-delivered', () => { ceremony!.delivered(); collector.clear(); render(); });
  action('threshold-cancel', () => cancel());
  action('threshold-pause', () => { paused = !paused; get('threshold-pause').textContent = paused ? 'Play' : 'Pause'; });
  action('threshold-next', () => { frame++; draw(); });
  action('threshold-previous', () => { frame = Math.max(0, frame - 1); draw(); });
  modal.addEventListener('cancel', event => { event.preventDefault(); cancel(); });
  window.addEventListener('resize', draw);
  setInterval(() => {
    if (ceremony && Date.now() >= ceremony.deadline) { cancel(ceremony.mode === 'repair' ? 'Repair expired.' : 'Ceremony expired. Cancel it on every device and start a fresh session.'); return; }
    get('threshold-time').textContent = ceremony ? `Session ends in ${Math.max(0, Math.ceil((ceremony.deadline - Date.now()) / 1000))} seconds.` : '';
    if (encoded.length && !paused) { frame++; draw(); }
  }, 500);
  return {
    cancel,
    intercept(operation: Operation | null): boolean {
      if (completing && operation) return true;
      if (!operation) { if (ceremony?.mode === 'sign') cancel('The original signing request ended.', false); return false; }
      if (ceremony?.mode === 'sign') return true;
      if (!group || owner.key !== group.pubkey) return false;
      if (operation.request.method.startsWith('nip44_')) { queueMicrotask(() => owner.cancel('This threshold group cannot perform NIP44 encryption or decryption.')); return true; }
      if (operation.request.method !== 'sign_event') return false;
      try {
        const selected = [...get('group-members').querySelectorAll<HTMLInputElement>('input:checked')].map(input => input.value).sort();
        collector.clear(); captured.clear(); ceremony = new Ceremony({ group, selected, request: operation.request }); owner.reserved = true; render();
      } catch (reason) { queueMicrotask(() => owner.cancel(error(reason))); status(error(reason)); }
      return true;
    },
    capture(frame: string): { done: boolean; status: string } {
      try {
        // A displayed packet keeps repeating after completion; do not reopen it.
        const digest = /^ns:([a-f0-9]{64}):/.exec(frame)?.[1];
        if (digest && captured.has(digest)) return { done: false, status: 'This output is already collected. Show the next device output.' };
        const raw = collector.add(frame);
        if (raw === null) return { done: false, status: `Collected ${collector.progress.received} of ${collector.progress.total} QR frames.` };
        collector.clear();
        if (captured.size >= 32) throw Error('Too many distinct ceremony outputs. Start a fresh ceremony.');
        if (digest) captured.add(digest);
        if (importing) { importing = false; owner.reserved = false; modal.close(); loadGroup(raw); return { done: true, status: 'Public group loaded.' }; }
        if (!ceremony) throw Error('There is no active ceremony.');
        const previous = ceremony.phase; ceremony.ingest(raw);
        if (ceremony.phase === 'complete') {
          const result = ceremony.resultWire, mode = ceremony.mode;
          ceremony = null; owner.reserved = false; modal.close(); encoded = []; displayed = '';
          if (mode !== 'sign') {
            loadGroup(raw);
            if (mode === 'repair') status('Lost share recovered. The npub is unchanged. Save a new share backup from every device and keep the new public group record. Old share copies remain valid; repair does not revoke them.');
          }
          else {
            completing = true;
            try { for (const part of frames(result)) owner.scan(part); }
            finally { completing = false; }
            status('Group signature independently verified and returned to the original request.');
          }
          return { done: true, status: mode !== 'sign' ? 'Matching group records collected.' : 'Signature verified.' };
        }
        render(); return { done: ceremony.delivering || previous !== ceremony.phase, status: `Accepted ${ceremony.count} output(s) for ${ceremony.phase}. Scan the next device output.` };
      } catch (reason) { cancel(error(reason)); throw reason; }
    },
  };
}
