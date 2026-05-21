const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const sourcePath = "C:/Users/jaspa/Downloads/cavesglobe.png";
const outPath = path.join(__dirname, "..", "static", "img", "caves-loading.gif");

const outputSize = 300;
const frames = 24;
const delayCs = 4;
const transparentIndex = 0;

function byte(n) {
  return Buffer.from([n & 0xff]);
}

function word(n) {
  return Buffer.from([n & 0xff, (n >> 8) & 0xff]);
}

function readPng(filePath) {
  const png = fs.readFileSync(filePath);
  if (png.slice(0, 8).toString("hex") !== "89504e470d0a1a0a") {
    throw new Error("Source is not a PNG file.");
  }

  let offset = 8;
  let width = 0;
  let height = 0;
  let colorType = 0;
  const idat = [];

  while (offset < png.length) {
    const length = png.readUInt32BE(offset);
    const type = png.slice(offset + 4, offset + 8).toString("ascii");
    const data = png.slice(offset + 8, offset + 8 + length);
    offset += 12 + length;

    if (type === "IHDR") {
      width = data.readUInt32BE(0);
      height = data.readUInt32BE(4);
      const bitDepth = data[8];
      colorType = data[9];
      if (bitDepth !== 8 || colorType !== 6) {
        throw new Error(`Unsupported PNG format: bitDepth=${bitDepth}, colorType=${colorType}`);
      }
    } else if (type === "IDAT") {
      idat.push(data);
    } else if (type === "IEND") {
      break;
    }
  }

  const inflated = zlib.inflateSync(Buffer.concat(idat));
  const stride = width * 4;
  const rgba = Buffer.alloc(width * height * 4);
  const previous = Buffer.alloc(stride);
  const current = Buffer.alloc(stride);
  let input = 0;

  for (let y = 0; y < height; y += 1) {
    const filter = inflated[input];
    input += 1;
    inflated.copy(current, 0, input, input + stride);
    input += stride;

    for (let x = 0; x < stride; x += 1) {
      const left = x >= 4 ? current[x - 4] : 0;
      const up = previous[x];
      const upLeft = x >= 4 ? previous[x - 4] : 0;

      if (filter === 1) current[x] = (current[x] + left) & 0xff;
      else if (filter === 2) current[x] = (current[x] + up) & 0xff;
      else if (filter === 3) current[x] = (current[x] + Math.floor((left + up) / 2)) & 0xff;
      else if (filter === 4) {
        const p = left + up - upLeft;
        const pa = Math.abs(p - left);
        const pb = Math.abs(p - up);
        const pc = Math.abs(p - upLeft);
        current[x] = (current[x] + (pa <= pb && pa <= pc ? left : pb <= pc ? up : upLeft)) & 0xff;
      } else if (filter !== 0) {
        throw new Error(`Unsupported PNG filter: ${filter}`);
      }
    }

    current.copy(rgba, y * stride);
    current.copy(previous);
  }

  return { width, height, rgba, colorType };
}

function getBounds(img) {
  let minX = img.width;
  let minY = img.height;
  let maxX = 0;
  let maxY = 0;

  for (let y = 0; y < img.height; y += 1) {
    for (let x = 0; x < img.width; x += 1) {
      const i = (y * img.width + x) * 4;
      const r = img.rgba[i];
      const g = img.rgba[i + 1];
      const b = img.rgba[i + 2];
      const a = img.rgba[i + 3];
      const visible = a > 20 && !(r > 246 && g > 246 && b > 246);
      if (!visible) continue;
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    }
  }

  return { minX, minY, maxX, maxY };
}

function sampleLayer(img, sx, sy, layer) {
  const x = Math.round(sx);
  const y = Math.round(sy);
  if (x < 0 || y < 0 || x >= img.width || y >= img.height) return null;

  const i = (y * img.width + x) * 4;
  const r = img.rgba[i];
  const g = img.rgba[i + 1];
  const b = img.rgba[i + 2];
  const a = img.rgba[i + 3];
  if (a < 20 || (r > 246 && g > 246 && b > 246)) return null;

  const brightness = (r + g + b) / 3;
  const isBlack = brightness < 70;
  const isGlobe = !isBlack && b > 50;

  if (layer === "plane" && !isBlack) return null;
  if (layer === "globe" && !isGlobe) return null;

  return [r, g, b, a];
}

function blend(dst, index, rgba) {
  const a = rgba[3] / 255;
  const inv = 1 - a;
  dst[index] = Math.round(rgba[0] * a + dst[index] * inv);
  dst[index + 1] = Math.round(rgba[1] * a + dst[index + 1] * inv);
  dst[index + 2] = Math.round(rgba[2] * a + dst[index + 2] * inv);
  dst[index + 3] = Math.min(255, Math.round(255 * a + dst[index + 3] * inv));
}

function drawLayer(dest, img, bounds, scale, angle, layer, opacity = 1) {
  const cx = (bounds.minX + bounds.maxX) / 2;
  const cy = (bounds.minY + bounds.maxY) / 2;
  const outCenter = outputSize / 2;
  const cos = Math.cos(-angle);
  const sin = Math.sin(-angle);

  for (let y = 0; y < outputSize; y += 1) {
    for (let x = 0; x < outputSize; x += 1) {
      const dx = (x + 0.5 - outCenter) / scale;
      const dy = (y + 0.5 - outCenter) / scale;
      const sx = cx + dx * cos - dy * sin;
      const sy = cy + dx * sin + dy * cos;
      const rgba = sampleLayer(img, sx, sy, layer);
      if (!rgba) continue;
      rgba[3] = Math.round(rgba[3] * opacity);
      blend(dest, (y * outputSize + x) * 4, rgba);
    }
  }
}

function makeFrame(img, bounds, frameIndex) {
  const rgba = Buffer.alloc(outputSize * outputSize * 4);
  const contentW = bounds.maxX - bounds.minX + 1;
  const contentH = bounds.maxY - bounds.minY + 1;
  const baseScale = (outputSize * 0.78) / Math.max(contentW, contentH);
  const t = frameIndex / frames;
  const globeAngle = t * Math.PI * 2;
  const planeAngle = -t * Math.PI * 2;

  drawLayer(rgba, img, bounds, baseScale * 0.98, globeAngle, "globe", 1);
  drawLayer(rgba, img, bounds, baseScale * 1.02, planeAngle, "plane", 1);

  return rgba;
}

function palette() {
  const colors = [[0, 0, 0]];
  for (let r = 0; r < 8; r += 1) {
    for (let g = 0; g < 8; g += 1) {
      for (let b = 0; b < 4; b += 1) {
        if (colors.length >= 256) break;
        colors.push([
          Math.round((r / 7) * 255),
          Math.round((g / 7) * 255),
          Math.round((b / 3) * 255),
        ]);
      }
    }
  }
  while (colors.length < 256) colors.push([0, 0, 0]);
  return Buffer.from(colors.flat());
}

function quantize(rgba) {
  const indices = Buffer.alloc(outputSize * outputSize);
  for (let i = 0, p = 0; i < rgba.length; i += 4, p += 1) {
    const a = rgba[i + 3];
    if (a < 24) {
      indices[p] = transparentIndex;
      continue;
    }

    const r = Math.min(7, Math.round((rgba[i] / 255) * 7));
    const g = Math.min(7, Math.round((rgba[i + 1] / 255) * 7));
    const b = Math.min(3, Math.round((rgba[i + 2] / 255) * 3));
    const mapped = 1 + (r * 32 + g * 4 + b);
    indices[p] = mapped > 255 ? 255 : mapped;
  }
  return indices;
}

function lzwEncode(indices, minCodeSize) {
  const clearCode = 1 << minCodeSize;
  const endCode = clearCode + 1;
  let codeSize = minCodeSize + 1;
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

  // Conservative GIF LZW stream: emit raw pixel codes and clear before the
  // decoder needs to increase beyond 9-bit codes. It is larger, but robust.
  for (let i = 0; i < indices.length; i += 254) {
    codeSize = minCodeSize + 1;
    writeCode(clearCode);
    const end = Math.min(indices.length, i + 254);
    for (let p = i; p < end; p += 1) writeCode(indices[p]);
  }

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

function frameBlock(indices) {
  const compressed = lzwEncode(indices, 8);
  return Buffer.concat([
    Buffer.from([0x21, 0xf9, 0x04, 0x09]),
    word(delayCs),
    byte(transparentIndex),
    byte(0),
    byte(0x2c),
    word(0),
    word(0),
    word(outputSize),
    word(outputSize),
    byte(0),
    byte(8),
    subBlocks(compressed),
  ]);
}

function buildGif() {
  const img = readPng(sourcePath);
  const bounds = getBounds(img);
  const header = Buffer.concat([
    Buffer.from("GIF89a", "ascii"),
    word(outputSize),
    word(outputSize),
    byte(0xf7),
    byte(transparentIndex),
    byte(0),
    palette(),
    Buffer.from([0x21, 0xff, 0x0b]),
    Buffer.from("NETSCAPE2.0", "ascii"),
    Buffer.from([0x03, 0x01]),
    word(0),
    byte(0),
  ]);

  const gifFrames = [];
  for (let i = 0; i < frames; i += 1) {
    gifFrames.push(frameBlock(quantize(makeFrame(img, bounds, i))));
  }

  return Buffer.concat([header, ...gifFrames, byte(0x3b)]);
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, buildGif());
console.log(outPath);
