// Build the Sieve architecture diagram through the Excalidraw MCP server.
//
// The server keeps the scene in memory, so this script creates every element,
// reads the scene back, and writes docs/architecture.excalidraw.
//
//   node tools/excalidraw_arch.mjs
//
// To use an installed copy instead of npx: set EXCALIDRAW_MCP_ENTRY to the
// package's src/cli.js.
import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = resolve(ROOT, "docs/architecture.excalidraw");

const BLUE = "#a5d8ff";
const PURPLE = "#d0bfff";
const YELLOW = "#ffec99";
const GREEN = "#b2f2bb";
const GREY = "#e9ecef";
const INK = "#1e1e1e";

const boxes = [
  // Consumers
  { x: 60, y: 60, w: 240, h: 56, color: BLUE, text: "OpenCode agent" },
  { x: 330, y: 60, w: 210, h: 56, color: BLUE, text: "/sieve commands" },
  { x: 570, y: 60, w: 210, h: 56, color: BLUE, text: "Scripts, dashboards" },
  { x: 810, y: 60, w: 270, h: 56, color: BLUE, text: "Terminal (sieve ...)" },
  // Transport
  {
    x: 60, y: 176, w: 1020, h: 96, color: PURPLE,
    text: "Transport\nMCP server over stdio: index · query · read · compress · original · symbol · stats · memory · summarize\nFastAPI service (sieve-serve) · CLI (sieve ...)",
  },
  // Engine pipeline
  { x: 60, y: 330, w: 170, h: 70, color: YELLOW, text: "discover.py" },
  { x: 280, y: 330, w: 170, h: 70, color: YELLOW, text: "index.py\nparse/" },
  { x: 500, y: 330, w: 170, h: 70, color: YELLOW, text: "retrieval/\nBM25 + boosts" },
  { x: 720, y: 330, w: 170, h: 70, color: YELLOW, text: "allocator.py\nbudget split" },
  { x: 940, y: 330, w: 170, h: 70, color: YELLOW, text: "composer.py\nhard ceiling" },
  // Engine detail
  {
    x: 60, y: 450, w: 390, h: 96, color: GREY,
    text: "Python ast · tree-sitter (TS, JS, C, C++, Go, Java, Rust) · regex fallback\nchunks per file and per function",
  },
  {
    x: 500, y: 450, w: 390, h: 96, color: GREY,
    text: "BM25 + symbol / import / call-graph boosts\noptional local vectors (fastembed, opt-in)",
  },
  {
    x: 940, y: 450, w: 170, h: 96, color: GREY,
    text: "per-task split + token ceiling\nmemory layer (recent turns)",
  },
  // State on disk
  {
    x: 60, y: 600, w: 330, h: 70, color: GREEN,
    text: "~/.sieve/originals\nevery original saved by ref",
  },
  {
    x: 420, y: 600, w: 300, h: 70, color: GREEN,
    text: "~/.sieve/memory\nnotes + recent turns",
  },
  {
    x: 750, y: 600, w: 330, h: 70, color: GREEN,
    text: "~/.sieve/events\ntoken savings log (stats)",
  },
  // Quality gates
  {
    x: 250, y: 720, w: 700, h: 56, color: GREY,
    text: "Bench & eval — 12-task recall eval · six-task real benchmark · 45 tests",
  },
];

// Straight connectors as [x1, y1, x2, y2].
const arrows = [
  [180, 116, 180, 176],
  [435, 116, 435, 176],
  [675, 116, 675, 176],
  [945, 116, 945, 176],
  [560, 272, 560, 330], // call into the engine
  [630, 330, 630, 272], // budgeted context back to the transport
  [230, 365, 280, 365],
  [450, 365, 500, 365],
  [670, 365, 720, 365],
  [890, 365, 940, 365],
  [145, 400, 145, 450],
  [585, 400, 585, 450],
  [1025, 400, 1025, 450],
  [200, 546, 200, 600],
  [570, 546, 570, 600],
  [1025, 546, 1025, 600],
];

const entry = process.env.EXCALIDRAW_MCP_ENTRY;
const proc = entry
  ? spawn(process.execPath, [entry], { stdio: ["pipe", "pipe", "pipe"] })
  : spawn("npx", ["-y", "excalidraw-mcp"], { shell: true });

let buf = "";
let nextId = 1;
const pending = new Map();

proc.stdout.on("data", (chunk) => {
  buf += chunk.toString();
  let index;
  while ((index = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, index).trim();
    buf = buf.slice(index + 1);
    if (!line) continue;
    let msg;
    try { msg = JSON.parse(line); } catch { continue; }
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  }
});
proc.stderr.on("data", (d) => process.stderr.write("[excalidraw] " + d));
proc.on("exit", (code) => {
  if (code) console.error(`server exited with ${code}`);
});

function request(method, params = {}) {
  const id = nextId++;
  proc.stdin.write(JSON.stringify({ jsonrpc: "2.0", id, method, params }) + "\n");
  return new Promise((resolve_, reject) => {
    pending.set(id, resolve_);
    setTimeout(() => reject(new Error(`timeout: ${method}`)), 60000);
  });
}

function payload(result) {
  const text = result?.content?.find((part) => part.type === "text")?.text ?? "{}";
  return JSON.parse(text);
}

await request("initialize", {
  protocolVersion: "2024-11-05",
  capabilities: {},
  clientInfo: { name: "sieve-architecture", version: "1.0.0" },
});
proc.stdin.write(JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) + "\n");

for (const box of boxes) {
  await request("tools/call", {
    name: "create_element",
    arguments: {
      type: "rectangle", x: box.x, y: box.y, width: box.w, height: box.h,
      text: box.text, backgroundColor: box.color, strokeColor: INK,
      strokeWidth: 2, roughness: 1, opacity: 100, fontSize: 16,
    },
  });
}

for (const [x1, y1, x2, y2] of arrows) {
  await request("tools/call", {
    name: "create_element",
    arguments: {
      type: "arrow", x: x1, y: y1,
      points: [{ x: 0, y: 0 }, { x: x2 - x1, y: y2 - y1 }],
      strokeColor: INK, strokeWidth: 2, roughness: 1, opacity: 100,
    },
  });
}

const scene = payload((await request("tools/call", {
  name: "get_resource", arguments: { resource: "elements" },
})).result);

// Expand to a spec-compliant Excalidraw scene so excalidraw.com can open it.
const roundness = (type) => (type === "rectangle" ? { type: 3 } : null);
const elements = [];

scene.elements.forEach((item, index) => {
  const seed = 1000 + index;
  if (item.type === "arrow") {
    elements.push({
      id: item.id, type: "arrow", x: item.x, y: item.y,
      width: item.points.at(-1).x, height: item.points.at(-1).y, angle: 0,
      strokeColor: INK, backgroundColor: "transparent", fillStyle: "solid",
      strokeWidth: 2, strokeStyle: "solid", roughness: 1, opacity: 100,
      groupIds: [], frameId: null, roundness: { type: 2 }, seed, version: 1,
      versionNonce: seed, isDeleted: false, boundElements: null, updated: 1,
      link: null, locked: false,
      points: item.points.map((point) => [point.x, point.y]),
      lastCommittedPoint: null, startBinding: null, endBinding: null,
      startArrowhead: null, endArrowhead: "arrow", elbowed: false,
    });
    return;
  }
  const textId = `${item.id}-label`;
  elements.push({
    id: item.id, type: "rectangle", x: item.x, y: item.y,
    width: item.width, height: item.height, angle: 0,
    strokeColor: INK, backgroundColor: item.backgroundColor ?? "transparent",
    fillStyle: "solid", strokeWidth: 2, strokeStyle: "solid", roughness: 1,
    opacity: 100, groupIds: [], frameId: null, roundness: roundness(item.type),
    seed, version: 1, versionNonce: seed, isDeleted: false,
    boundElements: item.text ? [{ type: "text", id: textId }] : null,
    updated: 1, link: null, locked: false,
  });
  if (!item.text) return;
  const labels = item.text.split("\n");
  const longest = Math.max(...labels.map((line) => line.length));
  const fontSize = item.fontSize ?? 16;
  const width = Math.min(item.width - 20, Math.ceil(longest * fontSize * 0.55));
  const height = Math.ceil(labels.length * fontSize * 1.25);
  elements.push({
    id: textId, type: "text",
    x: item.x + (item.width - width) / 2, y: item.y + (item.height - height) / 2,
    width, height, angle: 0, strokeColor: INK, backgroundColor: "transparent",
    fillStyle: "solid", strokeWidth: 2, strokeStyle: "solid", roughness: 1,
    opacity: 100, groupIds: [], frameId: null, roundness: null, seed: seed + 1,
    version: 1, versionNonce: seed + 1, isDeleted: false, boundElements: null,
    updated: 1, link: null, locked: false,
    text: item.text, originalText: item.text, fontSize, fontFamily: 2,
    textAlign: "center", verticalAlign: "middle", containerId: item.id,
    lineHeight: 1.25, customData: null,
  });
});

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify({
  type: "excalidraw", version: 2, source: "https://excalidraw.com",
  elements, appState: { gridSize: null, viewBackgroundColor: "#ffffff" },
  files: {},
}, null, 1) + "\n");

console.log(`wrote ${OUT}: ${boxes.length} boxes, ${arrows.length} arrows, ${elements.length} elements`);
proc.kill();
process.exit(0);
