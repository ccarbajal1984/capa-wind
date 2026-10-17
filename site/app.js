const REQUIRED_PARENT = "capa-wind.pages.dev";

const ticks = document.querySelector("#ticks");
for (let i = 0; i < 16; i += 1) {
  const major = i % 4 === 0;
  const angle = (i * 22.5 * Math.PI) / 180;
  const inner = major ? 66 : 70;
  const outer = 78;
  const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
  line.setAttribute("x1", String(100 + Math.sin(angle) * inner));
  line.setAttribute("y1", String(100 - Math.cos(angle) * inner));
  line.setAttribute("x2", String(100 + Math.sin(angle) * outer));
  line.setAttribute("y2", String(100 - Math.cos(angle) * outer));
  line.setAttribute("class", major ? "tick major" : "tick");
  ticks.appendChild(line);
}

function relative(path) {
  return new URL(path, document.baseURI);
}

function formatWhen(value) {
  return new Date(value).toLocaleString("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Madrid",
  });
}

function hourLabel(value) {
  return new Date(value).toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Madrid",
  });
}

function setText(id, value) {
  document.getElementById(id).textContent = value;
}

function renderCurrent(data) {
  const current = data.current;
  setText("direction", current.dir);
  setText("degrees", `${current.dir_deg}°`);
  setText("wind", Number(current.wind_kt).toFixed(1));
  setText("gust", Number(current.gust_kt).toFixed(1));
  setText("temp", Number(current.temp_c).toFixed(1));
  const updated = document.getElementById("updated");
  updated.dateTime = data.updated;
  updated.textContent = formatWhen(data.updated);
  document.getElementById("marker").setAttribute("transform", `rotate(${current.dir_deg} 100 100)`);
}

function svgEl(name, attrs) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
  return node;
}

function emptyPlot(host, message) {
  host.innerHTML = `<p class="empty">${message}</p>`;
}

function drawWind(samples) {
  const host = document.getElementById("wind-chart");
  if (!samples.length) {
    emptyPlot(host, "No wind samples yet.");
    return;
  }
  const width = 640;
  const height = 200;
  const pad = { l: 36, r: 12, t: 12, b: 28 };
  const max = Math.max(1, ...samples.map((item) => Math.max(item.wind_kt, item.gust_kt)));
  const yMax = Math.ceil(max / 2) * 2;
  const xAt = (index) => pad.l + (index * (width - pad.l - pad.r)) / Math.max(samples.length - 1, 1);
  const yAt = (value) => pad.t + (1 - value / yMax) * (height - pad.t - pad.b);
  const path = (key) => samples.map((item, index) => `${index === 0 ? "M" : "L"} ${xAt(index).toFixed(1)} ${yAt(item[key]).toFixed(1)}`).join(" ");
  const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": "Wind and gust, last 24 hours" });
  for (let tick = 0; tick <= yMax; tick += Math.max(yMax / 2, 1)) {
    const y = yAt(tick);
    svg.appendChild(svgEl("line", { x1: pad.l, y1: y, x2: width - pad.r, y2: y, class: "grid" }));
    const label = svgEl("text", { x: 0, y: y + 4, class: "axis" });
    label.textContent = String(Math.round(tick));
    svg.appendChild(label);
  }
  svg.appendChild(svgEl("path", { d: path("gust_kt"), class: "line-gust" }));
  svg.appendChild(svgEl("path", { d: path("wind_kt"), class: "line-wind" }));
  [0, Math.floor((samples.length - 1) / 2), samples.length - 1].forEach((index) => {
    const label = svgEl("text", { x: xAt(index), y: height - 6, class: "axis", "text-anchor": "middle" });
    label.textContent = hourLabel(samples[index].t);
    svg.appendChild(label);
  });
  host.replaceChildren(svg);
}

function drawDirection(samples) {
  const host = document.getElementById("dir-chart");
  if (!samples.length) {
    emptyPlot(host, "No direction samples yet.");
    return;
  }
  const width = 640;
  const height = 200;
  const pad = { l: 36, r: 12, t: 12, b: 28 };
  const xAt = (index) => pad.l + (index * (width - pad.l - pad.r)) / Math.max(samples.length - 1, 1);
  const yAt = (deg) => pad.t + (1 - deg / 360) * (height - pad.t - pad.b);
  const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": "Wind direction, last 24 hours" });
  ["N", "E", "S", "W"].forEach((name, index) => {
    const deg = index * 90;
    const y = yAt(deg);
    svg.appendChild(svgEl("line", { x1: pad.l, y1: y, x2: width - pad.r, y2: y, class: "grid" }));
    const label = svgEl("text", { x: 0, y: y + 4, class: "axis" });
    label.textContent = name;
    svg.appendChild(label);
  });
  samples.forEach((item, index) => {
    svg.appendChild(svgEl("circle", { cx: xAt(index).toFixed(1), cy: yAt(item.dir_deg).toFixed(1), r: 2.4, class: "dot" }));
  });
  host.replaceChildren(svg);
}

function parentsFrom(config) {
  const parents = new Set([REQUIRED_PARENT, "localhost", "127.0.0.1"]);
  (config.parents || []).forEach((parent) => {
    if (typeof parent === "string" && parent.length > 0) parents.add(parent);
  });
  return [...parents];
}

function twitchSrc(channel, parents) {
  const params = new URLSearchParams({ channel, muted: "true" });
  const query = params.toString();
  const parentQuery = parents.map((parent) => `parent=${encodeURIComponent(parent)}`).join("&");
  return `https://player.twitch.tv/?${query}&${parentQuery}`;
}

async function loadConfig() {
  try {
    const response = await fetch(relative("config.json"), { cache: "no-store" });
    if (!response.ok) return { twitchChannel: "capa" };
    return await response.json();
  } catch {
    return { twitchChannel: "capa" };
  }
}

async function loadLive() {
  const response = await fetch(relative("data/live.json"), { cache: "no-store" });
  if (!response.ok) throw new Error(`live.json ${response.status}`);
  const data = await response.json();
  renderCurrent(data);
  drawWind(data.history || []);
  drawDirection(data.history || []);
}

async function boot() {
  const config = await loadConfig();
  const channel = config.twitchChannel || "capa";
  setText("channel-name", channel);
  document.getElementById("twitch").src = twitchSrc(channel, parentsFrom(config));
  try {
    await loadLive();
  } catch (error) {
    document.getElementById("updated").textContent = "unavailable";
    emptyPlot(document.getElementById("wind-chart"), "Wind data could not be loaded.");
    emptyPlot(document.getElementById("dir-chart"), "Direction data could not be loaded.");
    console.error(error);
  }
}

boot();
setInterval(() => {
  loadLive().catch((error) => console.error(error));
}, 60000);
