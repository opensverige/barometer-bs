/* MOCK — not riksdagen data */
const MOCK = {
  tabs: [
    { id: "events", label: "Händelser", value: "128", delta: "+12%", up: true },
    { id: "motions", label: "Motioner", value: "42", delta: "+8%", up: true },
    { id: "gaps", label: "Luckor", value: "6", delta: "−1", up: true },
  ],
  series: {
    events: [18, 22, 19, 14, 16, 24, 26, 21],
    motions: [4, 6, 5, 3, 4, 7, 8, 5],
    gaps: [8, 8, 7, 7, 6, 6, 5, 6],
  },
  labels: ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8"],
  kinds: [
    { name: "Motion", n: 42, pct: 48 },
    { name: "Partisida", n: 22, pct: 25 },
    { name: "Beslut", n: 14, pct: 16 },
    { name: "Votering", n: 9, pct: 11 },
  ],
  windows: [
    { name: "2025/26", n: 71, pct: 55 },
    { name: "2024/25", n: 34, pct: 27 },
    { name: "2023/24", n: 23, pct: 18 },
  ],
};

function pathFrom(values) {
  const w = 640;
  const h = 200;
  const max = Math.max(...values, 1);
  const step = w / (values.length - 1);
  const pts = values.map((v, i) => {
    const x = i * step;
    const y = h - (v / max) * (h - 16) - 8;
    return [x, y];
  });
  const line = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
  const area = line + ` L${w},${h} L0,${h} Z`;
  return { line, area, pts };
}

function bars(rows) {
  return rows
    .map((r) => `<div class="va-bar">
      <div class="va-bar-track"><i style="width:${r.pct}%"></i><span>${r.name}</span></div>
      <b>${r.n}</b>
    </div>`)
    .join("");
}

function draw(tab) {
  const { line, area } = pathFrom(MOCK.series[tab]);
  const svg = document.getElementById("va-svg");
  if (!svg) return;
  svg.innerHTML = `
    <defs>
      <linearGradient id="vaFill" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#0070f3" stop-opacity="0.22"/>
        <stop offset="100%" stop-color="#0070f3" stop-opacity="0.02"/>
      </linearGradient>
    </defs>
    <line x1="0" y1="20" x2="640" y2="20" stroke="#ebebeb"/>
    <line x1="0" y1="110" x2="640" y2="110" stroke="#ebebeb"/>
    <path d="${area}" fill="url(#vaFill)"/>
    <path d="${line}" fill="none" stroke="#0070f3" stroke-width="2"/>
  `;
  document.querySelectorAll(".va-metric").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === tab);
  });
}

function mountCharts() {
  const host = document.getElementById("grafer");
  if (!host) return;
  if (!document.querySelector('link[href="charts.css"]')) {
    const l = document.createElement("link");
    l.rel = "stylesheet";
    l.href = "charts.css";
    document.head.appendChild(l);
  }
  host.innerHTML = `
    <div class="va-head">
      <h2>Grafer</h2>
      <span class="pill mock">MOCK · DEMO</span>
    </div>
    <p class="va-note">Påhittad tidsserie för att visa komponenten. Inte riksdagsdata. Inte ranking.</p>
    <div class="va-card">
      <div class="va-metrics">
        ${MOCK.tabs.map((t, i) => `<button type="button" class="va-metric${i === 0 ? " active" : ""}" data-tab="${t.id}">
          <span>${t.label}</span><br/>
          <strong>${t.value}</strong><span class="va-delta ${t.up ? "up" : "down"}">${t.delta}</span>
        </button>`).join("")}
      </div>
      <div class="va-chart">
        <svg id="va-svg" viewBox="0 0 640 200" preserveAspectRatio="none" aria-hidden="true"></svg>
      </div>
    </div>
    <div class="va-panels">
      <div class="va-panel">
        <h3>Källtyp · mock</h3>
        ${bars(MOCK.kinds)}
      </div>
      <div class="va-panel">
        <h3>Riksmöte · mock</h3>
        ${bars(MOCK.windows)}
      </div>
    </div>`;
  host.querySelectorAll(".va-metric").forEach((b) => {
    b.addEventListener("click", () => draw(b.dataset.tab));
  });
  draw("events");
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mountCharts);
else mountCharts();
