const NAMES = {
  s: "Socialdemokraterna",
  m: "Moderaterna",
  sd: "Sverigedemokraterna",
  v: "Vänsterpartiet",
  mp: "Miljöpartiet",
  c: "Centerpartiet",
  kd: "Kristdemokraterna",
  l: "Liberalerna",
};

const quoteEl = document.getElementById("quote");
const whoEl = document.getElementById("who");
const srcEl = document.getElementById("src");
const grid = document.getElementById("deltas");

let quotes = [];
let last = -1;

function wordCount(text) {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function pick() {
  if (!quotes.length) return;
  let i = Math.floor(Math.random() * quotes.length);
  if (quotes.length > 1 && i === last) i = (i + 1) % quotes.length;
  last = i;
  const q = quotes[i];
  quoteEl.textContent = q.text;
  whoEl.textContent = NAMES[q.actor_id] || q.actor_id;
  srcEl.href = q.source;
}

function card(d) {
  const empty = "—";
  const el = document.createElement("article");
  el.innerHTML = `
    <h2>${NAMES[d.actor_id] || d.actor_id}</h2>
    <p><strong>Sa 2022</strong> ${(d.said_then && d.said_then[0]) || empty}</p>
    <p><strong>Gjorde</strong> ${(d.did && d.did[0]) || empty}</p>
    <p><strong>Säger nu</strong> ${(d.says_now && d.says_now[0]) || empty}</p>
    <p class="flag">${(d.conflict_types || []).join(" · ") || "ingen conflict i fönstret"}</p>`;
  return el;
}

async function boot() {
  const [qRes, dRes] = await Promise.all([
    fetch("./quotes.json"),
    fetch("./delta.json").catch(() => null),
  ]);
  const pack = await qRes.json();
  quotes = (pack.quotes || []).filter((q) => wordCount(q.text) <= (pack.max_words || 10));
  pick();
  setInterval(pick, 6000);
  document.querySelector(".bubble").addEventListener("click", pick);

  if (dRes && dRes.ok) {
    const delta = await dRes.json();
    (delta.deltas || []).forEach((d) => grid.appendChild(card(d)));
  }
}

boot();
