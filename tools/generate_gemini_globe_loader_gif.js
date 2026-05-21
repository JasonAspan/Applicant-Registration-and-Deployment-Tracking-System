const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const sourcePath = "C:/Users/jaspa/Downloads/Gemini_Generated_Image_hg4yfkhg4yfkhg4y.png";
const outPath = path.join(__dirname, "..", "static", "img", "globe-plane-loading.gif");

const size = 300;
const frames = 30;
const delayCs = 7;
const backgroundIndex = 0;
const purpleIndex = 1;
const blackIndex = 2;
const shadowIndex = 3;

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
    offset += length + 12;

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
    const filter = inflated[input++];
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

function extractPlane(img) {
  const crop = { x: 635, y: 360, w: 385, h: 255 };
  const mask = [];
  for (let y = 0; y < crop.h; y += 1) {
    for (let x = 0; x < crop.w; x += 1) {
      const sx = crop.x + x;
      const sy = crop.y + y;
      const i = (sy * img.width + sx) * 4;
      const r = img.rgba[i];
      const g = img.rgba[i + 1];
      const b = img.rgba[i + 2];
      const a = img.rgba[i + 3];
      const dark = a > 30 && r < 70 && g < 70 && b < 70;
      if (dark) mask.push({ x, y });
    }
  }
  return { ...crop, mask };
}

function setPixel(pixels, x, y, index) {
  if (x < 0 || y < 0 || x >= size || y >= size) return;
  pixels[Math.round(y) * size + Math.round(x)] = index;
}

function drawCircleBrush(pixels, cx, cy, radius, index) {
  const minX = Math.floor(cx - radius);
  const maxX = Math.ceil(cx + radius);
  const minY = Math.floor(cy - radius);
  const maxY = Math.ceil(cy + radius);
  const rr = radius * radius;
  for (let y = minY; y <= maxY; y += 1) {
    for (let x = minX; x <= maxX; x += 1) {
      const dx = x + 0.5 - cx;
      const dy = y + 0.5 - cy;
      if (dx * dx + dy * dy <= rr) setPixel(pixels, x, y, index);
    }
  }
}

function drawLine(pixels, x1, y1, x2, y2, thickness, index) {
  const length = Math.max(Math.abs(x2 - x1), Math.abs(y2 - y1));
  const steps = Math.max(1, Math.ceil(length * 1.5));
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    drawCircleBrush(pixels, x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, thickness / 2, index);
  }
}

function fillPolygon(pixels, points, index) {
  let minY = Infinity;
  let maxY = -Infinity;
  for (const p of points) {
    minY = Math.min(minY, p.y);
    maxY = Math.max(maxY, p.y);
  }

  for (let y = Math.floor(minY); y <= Math.ceil(maxY); y += 1) {
    const nodes = [];
    let j = points.length - 1;
    for (let i = 0; i < points.length; i += 1) {
      const pi = points[i];
      const pj = points[j];
      if ((pi.y < y && pj.y >= y) || (pj.y < y && pi.y >= y)) {
        nodes.push(pi.x + ((y - pi.y) / (pj.y - pi.y)) * (pj.x - pi.x));
      }
      j = i;
    }

    nodes.sort((a, b) => a - b);
    for (let i = 0; i < nodes.length; i += 2) {
      if (nodes[i + 1] === undefined) break;
      for (let x = Math.floor(nodes[i]); x <= Math.ceil(nodes[i + 1]); x += 1) {
        setPixel(pixels, x, y, index);
      }
    }
  }
}

function drawParametric(pixels, fn, start, end, thickness, index, steps = 220) {
  let prev = fn(start);
  for (let i = 1; i <= steps; i += 1) {
    const u = start + ((end - start) * i) / steps;
    const cur = fn(u);
    drawLine(pixels, prev.x, prev.y, cur.x, cur.y, thickness, index);
    prev = cur;
  }
}

function drawGlobe(pixels, phase) {
  const cx = size / 2 - 22;
  const cy = size / 2;
  const r = 94;
  const stroke = 7;

  drawParametric(
    pixels,
    (a) => ({ x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r }),
    0,
    Math.PI * 2,
    stroke,
    purpleIndex,
    360,
  );

  for (const lat of [-0.52, 0, 0.52]) {
    const y = cy + Math.sin(lat) * r;
    const rx = Math.cos(lat) * r;
    const ry = lat === 0 ? 5 : 26;
    drawParametric(
      pixels,
      (a) => ({ x: cx + Math.cos(a) * rx, y: y + Math.sin(a) * ry }),
      0,
      Math.PI * 2,
      stroke * 0.82,
      purpleIndex,
      260,
    );
  }

  for (let i = 0; i < 6; i += 1) {
    const lambda = phase + (i * Math.PI) / 3;
    const rx = Math.abs(Math.cos(lambda)) * r;
    const front = Math.cos(lambda) >= 0;
    drawParametric(
      pixels,
      (a) => ({ x: cx + Math.cos(a) * rx, y: cy + Math.sin(a) * r }),
      -Math.PI / 2,
      Math.PI / 2,
      front ? stroke * 0.9 : stroke * 0.58,
      purpleIndex,
      180,
    );
  }

  drawLine(pixels, cx, cy - r + 2, cx, cy + r - 2, stroke, purpleIndex);
}

function drawPlane(pixels, _plane, progress) {
  const scale = 1.08;
  const startX = -28;
  const endX = 300;
  const x = startX + (endX - startX) * progress;
  const y = 152 + Math.sin(progress * Math.PI) * 26;
  const tilt = -0.14 + Math.sin(progress * Math.PI * 2) * 0.05;
  const cos = Math.cos(tilt);
  const sin = Math.sin(tilt);

  const transform = (points) => points.map((p) => ({
    x: x + p.x * scale * cos - p.y * scale * sin,
    y: y + p.x * scale * sin + p.y * scale * cos,
  }));

  const body = [
    { x: 72, y: 0 },
    { x: 34, y: -9 },
    { x: -48, y: -11 },
    { x: -68, y: -5 },
    { x: -48, y: 11 },
    { x: 34, y: 9 },
  ];
  const wingTop = [
    { x: 0, y: -6 },
    { x: -26, y: -44 },
    { x: -43, y: -40 },
    { x: -20, y: -4 },
  ];
  const wingBottom = [
    { x: 0, y: 6 },
    { x: -24, y: 42 },
    { x: -40, y: 38 },
    { x: -20, y: 4 },
  ];
  const tailTop = [
    { x: -46, y: -8 },
    { x: -64, y: -31 },
    { x: -75, y: -27 },
    { x: -59, y: -5 },
  ];
  const tailBottom = [
    { x: -46, y: 8 },
    { x: -64, y: 31 },
    { x: -75, y: 27 },
    { x: -59, y: 5 },
  ];

  for (const poly of [wingTop, wingBottom, tailTop, tailBottom, body]) {
    fillPolygon(pixels, transform(poly), blackIndex);
  }
}

function drawTrail(pixels, progress) {
  const cx = size / 2 - 22;
  const cy = size / 2 + 20;
  const rx = 126;
  const ry = 35;
  const head = Math.PI * 0.05 + progress * Math.PI * 1.12;
  const tail = head - Math.PI * 0.92;

  drawParametric(
    pixels,
    (a) => ({ x: cx + Math.cos(a) * rx, y: cy + Math.sin(a) * ry }),
    tail,
    head,
    6,
    shadowIndex,
    180,
  );
}

function makeFrame(plane, i) {
  const pixels = Buffer.alloc(size * size, backgroundIndex);
  const t = i / frames;
  const globePhase = t * Math.PI * 1.2;
  const planeProgress = t;

  drawGlobe(pixels, globePhase);
  drawTrail(pixels, planeProgress);
  drawPlane(pixels, plane, planeProgress);

  return pixels;
}

function colorTable() {
  const colors = [
    [255, 255, 255],
    [43, 31, 105],
    [0, 0, 0],
    [0, 0, 0],
  ];
  while (colors.length < 256) colors.push([0, 0, 0]);
  return Buffer.from(colors.flat());
}

function lzwEncode(indices, minCodeSize) {
  const clearCode = 1 << minCodeSize;
  const endCode = clearCode + 1;
  const codeSize = minCodeSize + 1;
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

  for (let i = 0; i < indices.length; i += 254) {
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
  return Buffer.concat([
    Buffer.from([0x21, 0xf9, 0x04, 0x09]),
    word(delayCs),
    byte(0),
    byte(0),
    byte(0x2c),
    word(0),
    word(0),
    word(size),
    word(size),
    byte(0),
    byte(8),
    subBlocks(lzwEncode(indices, 8)),
  ]);
}

function buildGif() {
  const img = readPng(sourcePath);
  const plane = extractPlane(img);
  const header = Buffer.concat([
    Buffer.from("GIF89a", "ascii"),
    word(size),
    word(size),
    byte(0xf7),
    byte(backgroundIndex),
    byte(0),
    colorTable(),
    Buffer.from([0x21, 0xff, 0x0b]),
    Buffer.from("NETSCAPE2.0", "ascii"),
    Buffer.from([0x03, 0x01]),
    word(0),
    byte(0),
  ]);

  const blocks = [];
  for (let i = 0; i < frames; i += 1) blocks.push(frameBlock(makeFrame(plane, i)));
  return Buffer.concat([header, ...blocks, byte(0x3b)]);
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, buildGif());
console.log(outPath);
