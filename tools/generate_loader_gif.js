const fs = require("fs");
const path = require("path");

const width = 160;
const height = 160;
const frames = 24;
const delayCs = 4;
const transparentIndex = 0;

const outPath = path.join(__dirname, "..", "static", "img", "loading-screen.gif");

function byte(n) {
  return Buffer.from([n & 0xff]);
}

function word(n) {
  return Buffer.from([n & 0xff, (n >> 8) & 0xff]);
}

function colorTable() {
  const colors = [[0, 0, 0]];

  // Applicant tracking themed blue-to-green accent ramp.
  for (let i = 0; i < 16; i += 1) {
    const t = i / 15;
    colors.push([
      Math.round(34 + 18 * t),
      Math.round(100 + 72 * t),
      Math.round(214 - 94 * t),
    ]);
  }

  colors.push([245, 248, 252]);
  colors.push([30, 41, 59]);

  while (colors.length < 256) colors.push([0, 0, 0]);
  return Buffer.from(colors.flat());
}

function setPixel(pixels, x, y, index) {
  if (x < 0 || y < 0 || x >= width || y >= height) return;
  pixels[y * width + x] = index;
}

function drawCircle(pixels, cx, cy, r, index) {
  const minX = Math.floor(cx - r);
  const maxX = Math.ceil(cx + r);
  const minY = Math.floor(cy - r);
  const maxY = Math.ceil(cy + r);
  const rr = r * r;

  for (let y = minY; y <= maxY; y += 1) {
    for (let x = minX; x <= maxX; x += 1) {
      const dx = x + 0.5 - cx;
      const dy = y + 0.5 - cy;
      if (dx * dx + dy * dy <= rr) setPixel(pixels, x, y, index);
    }
  }
}

function drawRoundedRect(pixels, x, y, w, h, r, index) {
  for (let yy = y; yy < y + h; yy += 1) {
    for (let xx = x; xx < x + w; xx += 1) {
      const left = xx < x + r;
      const right = xx >= x + w - r;
      const top = yy < y + r;
      const bottom = yy >= y + h - r;

      if ((left || right) && (top || bottom)) {
        const ccx = left ? x + r : x + w - r - 1;
        const ccy = top ? y + r : y + h - r - 1;
        const dx = xx - ccx;
        const dy = yy - ccy;
        if (dx * dx + dy * dy > r * r) continue;
      }

      setPixel(pixels, xx, yy, index);
    }
  }
}

function makeFrame(frameIndex) {
  const pixels = Buffer.alloc(width * height, transparentIndex);
  const cx = width / 2;
  const cy = height / 2;
  const orbit = 46;

  drawRoundedRect(pixels, 55, 58, 50, 42, 7, 17);
  drawRoundedRect(pixels, 63, 51, 34, 13, 6, 18);
  drawRoundedRect(pixels, 64, 71, 32, 5, 2, 18);
  drawRoundedRect(pixels, 64, 82, 23, 5, 2, 18);

  for (let i = 0; i < 12; i += 1) {
    const angle = ((i / 12) * Math.PI * 2) - Math.PI / 2;
    const x = cx + Math.cos(angle) * orbit;
    const y = cy + Math.sin(angle) * orbit;
    const freshness = (i - frameIndex + frames) % 12;
    const color = Math.max(1, 16 - freshness);
    const radius = 4.2 + Math.max(0, 5 - freshness) * 0.35;
    drawCircle(pixels, x, y, radius, color);
  }

  return pixels;
}

function lzwEncode(indices, minCodeSize) {
  const clearCode = 1 << minCodeSize;
  const endCode = clearCode + 1;
  let nextCode = endCode + 1;
  let codeSize = minCodeSize + 1;

  const dict = new Map();
  const resetDict = () => {
    dict.clear();
    for (let i = 0; i < clearCode; i += 1) dict.set(String(i), i);
    nextCode = endCode + 1;
    codeSize = minCodeSize + 1;
  };

  const bytes = [];
  let bitBuffer = 0;
  let bitCount = 0;

  const writeCode = (code) => {
    bitBuffer |= code << bitCount;
    bitCount += codeSize;
    while (bitCount >= 8) {
      bytes.push(bitBuffer & 0xff);
      bitBuffer >>= 8;
      bitCount -= 8;
    }
  };

  resetDict();
  writeCode(clearCode);

  let prefix = String(indices[0]);
  for (let i = 1; i < indices.length; i += 1) {
    const current = indices[i];
    const key = `${prefix},${current}`;

    if (dict.has(key)) {
      prefix = key;
    } else {
      writeCode(dict.get(prefix));
      if (nextCode < 4096) {
        dict.set(key, nextCode);
        nextCode += 1;
        if (nextCode === (1 << codeSize) && codeSize < 12) codeSize += 1;
      } else {
        writeCode(clearCode);
        resetDict();
      }
      prefix = String(current);
    }
  }

  writeCode(dict.get(prefix));
  writeCode(endCode);

  if (bitCount > 0) bytes.push(bitBuffer & 0xff);
  return Buffer.from(bytes);
}

function subBlocks(data) {
  const blocks = [];
  for (let i = 0; i < data.length; i += 255) {
    const chunk = data.subarray(i, i + 255);
    blocks.push(byte(chunk.length), chunk);
  }
  blocks.push(byte(0));
  return Buffer.concat(blocks);
}

function frameBlock(pixels) {
  const compressed = lzwEncode(pixels, 8);
  return Buffer.concat([
    Buffer.from([0x21, 0xf9, 0x04, 0x09]),
    word(delayCs),
    byte(transparentIndex),
    byte(0),
    byte(0x2c),
    word(0),
    word(0),
    word(width),
    word(height),
    byte(0),
    byte(8),
    subBlocks(compressed),
  ]);
}

function buildGif() {
  const header = Buffer.concat([
    Buffer.from("GIF89a", "ascii"),
    word(width),
    word(height),
    byte(0xf7),
    byte(transparentIndex),
    byte(0),
    colorTable(),
    Buffer.from([0x21, 0xff, 0x0b]),
    Buffer.from("NETSCAPE2.0", "ascii"),
    Buffer.from([0x03, 0x01]),
    word(0),
    byte(0),
  ]);

  const gifFrames = [];
  for (let i = 0; i < frames; i += 1) gifFrames.push(frameBlock(makeFrame(i)));

  return Buffer.concat([header, ...gifFrames, byte(0x3b)]);
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, buildGif());
console.log(outPath);
