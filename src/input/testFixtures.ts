import { deflateSync } from "zlib";

function chunk(type: string, data: Uint8Array): Uint8Array {
  const out = new Uint8Array(12 + data.length);
  const view = new DataView(out.buffer);
  view.setUint32(0, data.length);
  for (let i = 0; i < 4; i++) {
    out[4 + i] = type.charCodeAt(i);
  }
  out.set(data, 8);
  let crc = 0xffffffff;
  const table = makeCrcTable();
  for (let i = 4; i < 8 + data.length; i++) {
    crc = table[(crc ^ out[i]) & 0xff] ^ (crc >>> 8);
  }
  view.setUint32(8 + data.length, (crc ^ 0xffffffff) >>> 0);
  return out;
}

let cachedTable: Uint32Array | null = null;
function makeCrcTable(): Uint32Array {
  if (cachedTable) {
    return cachedTable;
  }
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    table[n] = c >>> 0;
  }
  cachedTable = table;
  return table;
}

function concat(parts: Uint8Array[]): Uint8Array {
  const total = parts.reduce((n, p) => n + p.length, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}

export function makeTestPng(width: number, height: number): Uint8Array {
  const signature = Uint8Array.from([137, 80, 78, 71, 13, 10, 26, 10]);
  const ihdr = new Uint8Array(13);
  const view = new DataView(ihdr.buffer);
  view.setUint32(0, width);
  view.setUint32(4, height);
  ihdr[8] = 8;
  ihdr[9] = 2;
  const raw = new Uint8Array(height * (1 + width * 3));
  for (let row = 0; row < height; row++) {
    raw[row * (1 + width * 3)] = 0;
    for (let col = 0; col < width; col++) {
      const v = (row + col) % 2 === 0 ? 255 : 0;
      raw[row * (1 + width * 3) + 1 + col * 3] = v;
      raw[row * (1 + width * 3) + 1 + col * 3 + 1] = (col * 32) % 256;
      raw[row * (1 + width * 3) + 1 + col * 3 + 2] = (row * 40) % 256;
    }
  }
  const compressed = deflateSync(raw);
  return concat([
    signature,
    chunk("IHDR", ihdr),
    chunk("IDAT", new Uint8Array(compressed.buffer, compressed.byteOffset, compressed.byteLength)),
    chunk("IEND", new Uint8Array(0)),
  ]);
}

export function makeCorruptBytes(): Uint8Array {
  return new TextEncoder().encode("this is not an image file at all");
}

export function makeClientFile(name: string, bytes: Uint8Array, mimeType = "") {
  return { name, size: bytes.length, mimeType, bytes };
}
