const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const gifPath = path.join(__dirname, "..", "static", "img", "caves-loading.gif");
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
  let codeSize = minCodeSize + 1;
  let nextCode = endCode + 1;
  let bitPos = 0;
  let previous = null;
  let dict = [];
  const output = [];

  const reset = () => {
    dict = [];
    for (let i = 0; i < clearCode; i += 1) dict[i] = [i];
    dict[clearCode] = [];
    dict[endCode] = null;
    codeSize = minCodeSize + 1;
    nextCode = endCode + 1;
    previous = null;
  };

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

  reset();
  while (output.length < expectedLength) {
    const code = readCode();
    if (code === null || code === endCode) break;
    if (code === clearCode) {
      reset();
      continue;
    }

    let entry;
    if (dict[code]) entry = dict[code].slice();
    else if (code === nextCode && previous) entry = previous.concat(previous[0]);
    else throw new Error(`Bad LZW code: ${code}`);

    output.push(...entry);
    if (previous) {
      dict[nextCode] = previous.concat(entry[0]);
      nextCode += 1;
      if (nextCode === 1 << codeSize && codeSize < 12) codeSize += 1;
    }
    previous = entry;
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
const packed = gif[10];
let offset = 13;
let palette = [];
if (packed & 0x80) {
  const count = 2 ** ((packed & 7) + 1);
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
      const gcePacked = gif[offset++];
      offset += 2;
      transparent = gif[offset++];
      offset += 1;
      if (!(gcePacked & 1)) transparent = -1;
    } else {
      const result = readSubBlocks(gif, offset);
      offset = result.offset;
    }
  } else if (block === 0x2c) {
    offset += 8;
    const imagePacked = gif[offset++];
    if (imagePacked & 0x80) offset += 3 * (2 ** ((imagePacked & 7) + 1));
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
writePng(path.join(outDir, "caves-loader-frame-00.png"), width, height, frames[0]);
writePng(path.join(outDir, "caves-loader-frame-06.png"), width, height, frames[6]);

let changedPixels = 0;
for (let i = 0; i < frames[0].length; i += 4) {
  if (
    frames[0][i] !== frames[6][i] ||
    frames[0][i + 1] !== frames[6][i + 1] ||
    frames[0][i + 2] !== frames[6][i + 2] ||
    frames[0][i + 3] !== frames[6][i + 3]
  ) changedPixels += 1;
}

console.log(JSON.stringify({
  gifPath: path.resolve(gifPath),
  width,
  height,
  frames: frames.length,
  changedPixelsBetweenFrame0And6: changedPixels,
  frame0: path.resolve(outDir, "caves-loader-frame-00.png"),
  frame6: path.resolve(outDir, "caves-loader-frame-06.png"),
}, null, 2));
