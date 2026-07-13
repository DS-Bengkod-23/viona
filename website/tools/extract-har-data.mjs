import fs from "node:fs";
import path from "node:path";

const input = process.argv[2];
const output = process.argv[3];
const assetOutput = process.argv[4] ?? "public/lms-assets";

if (!input || !output) {
  console.error("Usage: node tools/extract-har-data.mjs <input.har> <output.json> [asset-output-dir]");
  process.exit(1);
}

const har = JSON.parse(fs.readFileSync(input, "utf8"));
const byKey = new Map();
const assetMap = {};

function responseText(entry) {
  const content = entry.response?.content;
  if (!content?.text) {
    return "";
  }

  if (content.encoding === "base64") {
    return Buffer.from(content.text, "base64").toString("utf8");
  }

  return content.text;
}

function fileNameFromUrl(url, fallbackExt) {
  const parsed = new URL(url);
  const base = path.basename(parsed.pathname) || `asset-${Object.keys(assetMap).length + 1}${fallbackExt}`;
  return base.includes(".") ? base : `${base}${fallbackExt}`;
}

for (const entry of har.log.entries) {
  const url = entry.request?.url ?? "";
  const match = url.match(/api\/v3\/courses\/5\/(sub-section|sub-sub-section)\/(\d+)/);
  const text = responseText(entry);

  if (!match || entry.response?.status !== 200 || !text) {
    continue;
  }

  const key = `${match[1]}:${match[2]}`;
  if (byKey.has(key)) {
    continue;
  }

  byKey.set(key, JSON.parse(text));
}

for (const entry of har.log.entries) {
  const url = entry.request?.url ?? "";
  const content = entry.response?.content;
  const mime = content?.mimeType ?? "";

  if (entry.response?.status !== 200 || !content?.text || !mime.startsWith("image/")) {
    continue;
  }

  if (!url.includes("api-lms.jong.my.id/storage/image_assets")) {
    continue;
  }

  const ext = mime === "image/png" ? ".png" : ".jpg";
  const fileName = fileNameFromUrl(url, ext);
  const diskPath = path.join(assetOutput, fileName);
  fs.mkdirSync(path.dirname(diskPath), { recursive: true });

  const buffer = content.encoding === "base64"
    ? Buffer.from(content.text, "base64")
    : Buffer.from(content.text, "binary");

  fs.writeFileSync(diskPath, buffer);
  assetMap[url] = `/lms-assets/${fileName}`;
}

const items = Object.fromEntries(
  [...byKey.values()]
    .sort((a, b) => a.id - b.id)
    .map((item) => [String(item.id), item]),
);

const capturedLinkKeys = new Set();
const capturedLinks = [];

for (const entry of har.log.entries) {
  const url = entry.request?.url ?? "";
  const match = url.match(/lms\.jong\.my\.id\/kursus\/5\/(sub-section|sub-sub-section)\/(\d+)/);
  if (!match) {
    continue;
  }

  const key = `${match[1]}:${match[2]}`;
  if (!capturedLinkKeys.has(key)) {
    capturedLinkKeys.add(key);
    capturedLinks.push({ type: match[1], id: Number(match[2]) });
  }
}

const sections = [
  {
    id: "welcome",
    title: "Welcome!",
    items: [
      { id: 57 },
      { id: 65 },
      { id: 67, children: [49] },
      { id: 69 },
      { id: 70 },
    ],
  },
  {
    id: "what-is-eda",
    title: "Apa itu EDA?",
    items: [
      { id: 202 },
      { id: 203, children: [100, 102] },
      { id: 204 },
      { id: 205 },
      { id: 206, children: [104, 105] },
      { id: 207 },
      { id: 209 },
    ],
  },
  {
    id: "univariate",
    title: "Analisa Univariate",
    items: [
      { id: 183 },
      { id: 184, children: [75, 76, 77] },
      { id: 185, children: [78, 79] },
      { id: 186, children: [80, 81, 82] },
      { id: 187, children: [83, 84, 85] },
      { id: 188 },
      { id: 189 },
    ],
  },
  {
    id: "bivariate",
    title: "Analisa Bivariat",
    items: [
      { id: 190 },
      { id: 191, children: [86, 87, 88] },
      { id: 193, children: [89, 90, 91] },
      { id: 194, children: [92, 93, 94] },
      { id: 195, children: [95, 96, 97, 98] },
      { id: 196 },
    ],
  },
  {
    id: "data-quality",
    title: "Deteksi Masalah Data",
    items: [
      { id: 210 },
      { id: 211, children: [106, 107] },
      { id: 212, children: [108, 109] },
      { id: 213, children: [110, 111] },
      { id: 214, children: [112, 113] },
      { id: 215 },
      { id: 216, title: "Kuis", item_type: "QUIZ", unavailable: true },
    ],
  },
];

const data = {
  capturedAt: har.log.entries?.[0]?.startedDateTime ?? null,
  source: "C:/Users/GF63/Downloads/LMSV3.har",
  course: {
    id: 5,
    title: "Exploratory Data Analysis (EDA)",
    platform: "Bengkel Koding",
  },
  sections,
  items,
  capturedLinks,
  assetMap,
};

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, JSON.stringify(data, null, 2));
