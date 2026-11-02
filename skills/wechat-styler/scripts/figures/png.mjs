// 截图比对用的最小 PNG 解码：只支持 Chromium 截图产出的 8-bit、非隔行 RGB/RGBA。
import zlib from 'node:zlib';

export function decodePng(buffer) {
  if (buffer.toString('hex', 0, 8) !== '89504e470d0a1a0a') throw new Error('不是 PNG');
  let width = 0;
  let height = 0;
  let channels = 0;
  const chunks = [];
  for (let at = 8; at < buffer.length;) {
    const length = buffer.readUInt32BE(at);
    const type = buffer.toString('latin1', at + 4, at + 8);
    if (type === 'IHDR') {
      width = buffer.readUInt32BE(at + 8);
      height = buffer.readUInt32BE(at + 12);
      channels = { 2: 3, 6: 4 }[buffer[at + 17]] || 0;
      if (buffer[at + 16] !== 8 || !channels || buffer[at + 20] !== 0) throw new Error('只支持 8-bit 非隔行 RGB/RGBA PNG');
    } else if (type === 'IDAT') {
      chunks.push(buffer.subarray(at + 8, at + 8 + length));
    }
    at += length + 12;
  }
  const raw = zlib.inflateSync(Buffer.concat(chunks));
  const stride = width * channels;
  const data = Buffer.alloc(stride * height);
  for (let y = 0; y < height; y += 1) {
    const filter = raw[y * (stride + 1)];
    const line = y * (stride + 1) + 1;
    for (let i = 0; i < stride; i += 1) {
      const a = i >= channels ? data[y * stride + i - channels] : 0;
      const b = y ? data[(y - 1) * stride + i] : 0;
      const c = y && i >= channels ? data[(y - 1) * stride + i - channels] : 0;
      let pred = 0;
      if (filter === 1) pred = a;
      else if (filter === 2) pred = b;
      else if (filter === 3) pred = (a + b) >> 1;
      else if (filter === 4) {
        const p = a + b - c;
        const [pa, pb, pc] = [Math.abs(p - a), Math.abs(p - b), Math.abs(p - c)];
        pred = pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
      }
      data[y * stride + i] = (raw[line + i] + pred) & 0xff;
    }
  }
  return { width, height, channels, data };
}

/** 灰度差不低于 24 的像素占比。 */
export function diffRatio(a, b) {
  const width = Math.min(a.width, b.width);
  const height = Math.min(a.height, b.height);
  let changed = 0;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const ai = (y * a.width + x) * a.channels;
      const bi = (y * b.width + x) * b.channels;
      const luma = (19595 * Math.abs(a.data[ai] - b.data[bi]) + 38470 * Math.abs(a.data[ai + 1] - b.data[bi + 1])
        + 7471 * Math.abs(a.data[ai + 2] - b.data[bi + 2]) + 0x8000) >> 16;
      if (luma >= 24) changed += 1;
    }
  }
  return changed / (a.width * a.height);
}
