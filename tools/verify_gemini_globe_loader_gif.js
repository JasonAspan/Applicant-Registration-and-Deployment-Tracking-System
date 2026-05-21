const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const gifPath = path.join(__dirname, "..", "static", "img", "globe-plane-loading.gif");
const outDir = path.join(__dirname, "..", "previews");

function readSubBlocks(buf, offset) {
  const chunks = [];
  let i = offset;
  while (buf[i] !== 0) {
    const len = buf[i];
    chunks.push(buf.subarray(i + 1, i + 1 + len));
    i += len + 1;
  }
  return { data: Buffer.concat(chunks), offset: i + 1 };
}

function lzwDecode(data, minCodeSize, expectedLength) {
  const clearCode = 1 << minCodeSize;
  const endCode = clearCode + 1;
  const codeSize = minCodeSize + 1;
  let bitPos = 0;
  const output = [];

  const readCode = () => {
    let code = 0;
    for (let b = 0; b < codeSize; b += 1) {
      const byteIndex = Math.floor(bitPos / 8);
      const bitIndex = bitPos % 8;
      if (byteIndex >= data.length) return null;
      code |= ((data[byteIndex] >> bitIndex) & 1) << b;
      bitPos += 1;
    }
    return code;
  };

  while (output.length < expectedLength) {
    const code = readCode();
    if (code === null || code === endCode) break;
    if (code === clearCode) continue;
    output.push(code);
  }

  return Buffer.from(output.slice(0, expectedLength));
}

function crc32(buf) {
  let c = ~0;
  for (const byte of buf) {
    c ^= byte;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  }
  return ~c >>> 0;
}

function pngChunk(type, data) {
  const name = Buffer.from(type, "ascii");
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([name, data])));
  return Buffer.concat([len, name, data, crc]);
}

function writePng(filePath, width, height, rgba) {
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;

  const raw = Buffer.alloc((width * 4 + 1) * height);
  for (let y = 0; y < height; y += 1) {
    const row = y * (width * 4 + 1);
    raw[row] = 0;
    rgba.copy(raw, row + 1, y * width * 4, (y + 1) * width * 4);
  }

  fs.writeFileSync(filePath, Buffer.concat([
    Buffer.from("89504e470d0a1a0a", "hex"),
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", zlib.deflateSync(raw)),
    pngChunk("IEND", Buffer.alloc(0)),
  ]));
}

const gif = fs.readFileSync(gifPath);
const width = gif.readUInt16LE(6);
const height = gif.readUInt16LE(8);
let offset = 13;
const palette = [];
if (gif[10] & 0x80) {
  const count = 2 ** ((gif[10] & 7) + 1);
  for (let i = 0; i < count; i += 1) {
    palette.push([gif[offset], gif[offset + 1], gif[offset + 2]]);
    offset += 3;
  }
}

let transparent = 0;
const frames = [];
while (offset < gif.length) {
  const block = gif[offset++];
  if (block === 0x3b) break;
  if (block === 0x21) {
    const label = gif[offset++];
    if (label === 0xf9) {
      offset += 1;
      const packed = gif[offset++];
      offset += 2;
      transparent = gif[offset++];
      offset += 1;
      if (!(packed & 1)) transparent = -1;
    } else {
      offset = readSubBlocks(gif, offset).offset;
    }
  } else if (block === 0x2c) {
    offset += 8;
    const packed = gif[offset++];
    if (packed & 0x80) offset += 3 * (2 ** ((packed & 7) + 1));
    const minCodeSize = gif[offset++];
    const result = readSubBlocks(gif, offset);
    offset = result.offset;
    const indices = lzwDecode(result.data, minCodeSize, width * height);
    const rgba = Buffer.alloc(width * height * 4);
    for (let i = 0; i < indices.length; i += 1) {
      const idx = indices[i];
      const [r, g, b] = palette[idx] || [0, 0, 0];
      rgba[i * 4] = r;
      rgba[i * 4 + 1] = g;
      rgba[i * 4 + 2] = b;
      rgba[i * 4 + 3] = idx === transparent ? 0 : 255;
    }
    frames.push(rgba);
  }
}

fs.mkdirSync(outDir, { recursive: true });
const frame0 = path.join(outDir, "globe-plane-loader-frame-00.png");
const frame12 = path.join(outDir, "globe-plane-loader-frame-12.png");
writePng(frame0, width, height, frames[0]);
writePng(frame12, width, height, frames[12]);

let changedPixels = 0;
for (let i = 0; i < frames[0].length; i += 4) {
  if (
    frames[0][i] !== frames[12][i] ||
    frames[0][i + 1] !== frames[12][i + 1] ||
    frames[0][i + 2] !== frames[12][i + 2] ||
    frames[0][i + 3] !== frames[12][i + 3]
  ) changedPixels += 1;
}

console.log(JSON.stringify({
  gifPath: path.resolve(gifPath),
  bytes: gif.length,
  width,
  height,
  frames: frames.length,
  changedPixelsBetweenFrame0And12: changedPixels,
  frame0: path.resolve(frame0),
  frame12: path.resolve(frame12),
}, null, 2));
