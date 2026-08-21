const FLAG_SV = {
  words_without_action: "Säger på webben. Ingen motion i urvalet.",
  action_without_words: "Skrev i kammaren. Ingen topic-sida i urvalet.",
};
const TIP = {
  sade: "L3: partisida i urvalet. Tom = ingen AI-sida hittad, inte att de är tysta i verkligheten.",
  skrev: "L1: motion med AI i titeln. Tom = ingen sådan motion i frysen.",
  rostade: "Registrerad partiröst (Ja/Nej/Avstår). Acklamation räknas inte här.",
  beslutades: "Kammarbeslut, t.ex. acklamation. Partiröst då okänd.",
  konflikt: "Mismatch mellan webb och kammaren i urvalet.",
};

function isAcclamation(x) {
  return x && x.vote_method === "acclamation";
}

async function loadJson(name) {
  for (const url of [name, "/" + name, "/web/" + name]) {
    try {
      const res = await fetch(url);
      if (res.ok) return res.json();
    } catch (_e) {}
  }
  return null;
}

function shuffle(list) {
  const a = list.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function startSauron(pack) {
  const el = document.getElementById("bubble");
  if (!el) return;
  const quotes = (pack && pack.quotes) || [{ actor: "RADARN", text: "Protokoll före valtal." }];
  let order = shuffle(quotes);
  let i = 0;
  function show() {
    const q = order[i % order.length];
    el.innerHTML = `${q.text}<small>${q.actor || ""}</small>`;
    i += 1;
    if (i % order.length === 0) order = shuffle(quotes);
  }
  show();
  el.addEventListener("click", show);
  setInterval(show, 6000);
}

function links(items, empty) {
  if (!items || !items.length) return `<span class="empty">${empty}</span>`;
  return items
    .map((x) => {
      const note = isAcclamation(x) ? " — partiröst okänd" : "";
      const date = x.date ? ` <span class="empty">${x.date}</span>` : "";
      return `<a href="${x.url}" rel="noopener">${x.label}</a>${date}${note}`;
    })
    .join("<br />");
}

function cell(items, tip) {
  if (items && items.length) return `<span class="yes" title="${tip}">${items.length}</span>`;
  return `<span class="no" title="${tip}">—</span>`;
}

function th(label, key) {
  return `<th>${label} <button type="button" class="help" data-tip="${TIP[key]}">help</button></th>`;
}

let DATA = null;
let OPEN = null;

function visibleParties() {
  const topicSel = document.getElementById("filter-topic");
  const partySel = document.getElementById("filter-party");
  if (!topicSel || !partySel) return DATA.parties || [];
  const topic = topicSel.value;
  const party = partySel.value;
  const topicId = DATA.topic_id || "";
  if (topic && topicId && topic !== topicId && topic !== "all") return [];
  return (DATA.parties || []).filter((p) => party === "all" || p.actor_id === party);
}

function fillFilters() {
  const topicSel = document.getElementById("filter-topic");
  const partySel = document.getElementById("filter-party");
  if (!topicSel || !partySel) return;
  const topics = DATA.topics && DATA.topics.length
    ? DATA.topics
    : [{ topic_id: DATA.topic_id || "unknown", label: DATA.topic_label || DATA.topic_id || "topic" }];
  topicSel.innerHTML = topics.map((t) => `<option value="${t.topic_id || t}">${t.label || t.topic_label || t.topic_id || t}</option>`).join("");
  partySel.innerHTML = `<option value="all">Alla</option>` +
    (DATA.parties || []).map((p) => `<option value="${p.actor_id}">${p.name}</option>`).join("");
  topicSel.onchange = renderAll;
  partySel.onchange = renderAll;
}

function openSheet(p) {
  OPEN = p.actor_id;
  const sheet = document.getElementById("sheet");
  const body = document.getElementById("sheet-body");
  sheet.hidden = false;
  body.innerHTML = `<h2>${p.name}</h2>
    <p class="empty">${FLAG_SV[p.flag] || "Ingen konfliktflagga i urvalet."}</p>
    <p><span class="k">Sade</span><br>${links(p.words, "ingen partisida i urvalet")}</p>
    <p><span class="k">Skrev</span><br>${links(p.actions, "ingen AI-motion i urvalet")}</p>
    <p><span class="k">Röstade</span><br>${links(p.votes, "ingen registrerad partiröst")}</p>
    <p><span class="k">Beslutades</span><br>${links(p.decisions, "inget kammarbeslut i urvalet")}</p>`;
}

function renderAll() {
  if (!DATA) {
    document.getElementById("grid").textContent = "dataset.json saknas";
    return;
  }
  const loc = DATA.kpis && DATA.kpis.locator;
  const frz = DATA.kpis && DATA.kpis.metadata_freeze_match;
  const topicLabel = DATA.topic_label || DATA.topic_id || "topic";
  document.getElementById("meta").innerHTML =
    `Topic: <strong>${topicLabel}</strong> · rm ${(DATA.windows || []).join(" · ") || "—"} · locator ${loc == null ? "—" : Math.round(loc * 100) + "%"} · freeze ${frz == null ? "—" : Math.round(frz * 100) + "%"}`;

  const tvn = document.getElementById("tvn");
  if (tvn) {
    if (!DATA.then_vs_now || !DATA.then_vs_now.length) {
      tvn.hidden = true;
      tvn.innerHTML = "";
    } else {
      tvn.hidden = false;
      tvn.innerHTML = DATA.then_vs_now.map((x) => `<div>${x.name}: ${x.summary}</div>`).join("");
    }
  }

  const parties = visibleParties();
  const flags = document.getElementById("flags");
  if (flags) flags.innerHTML = "";

  document.getElementById("grid").innerHTML = `<table class="overview">
    <thead><tr>
      <th>Parti</th>${th("Sade", "sade")}${th("Skrev", "skrev")}${th("Röstade", "rostade")}${th("Beslutades", "beslutades")}${th("Konflikt", "konflikt")}
    </tr></thead>
    <tbody>
      ${parties.map((p) => `<tr tabindex="0" data-actor="${p.actor_id}">
        <td><img src="logos/${p.actor_id}.svg" alt="" width="20" height="20" />${p.name}</td>
        <td>${cell(p.words, TIP.sade)}</td>
        <td>${cell(p.actions, TIP.skrev)}</td>
        <td>${cell(p.votes, TIP.rostade)}</td>
        <td>${cell(p.decisions, TIP.beslutades)}</td>
        <td>${p.flag ? "ja" : "—"}</td>
      </tr>`).join("")}
    </tbody>
  </table>`;

  document.querySelectorAll("table.overview tbody tr").forEach((tr) => {
    const open = () => {
      const p = parties.find((x) => x.actor_id === tr.dataset.actor);
      if (p) openSheet(p);
    };
    tr.addEventListener("click", open);
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        open();
      }
    });
  });

  const audit = document.getElementById("audit");
  if (audit) {
    const first = parties.find((p) => (p.actions && p.actions[0]) || (p.words && p.words[0]));
    const src = first && ((first.actions && first.actions[0]) || (first.words && first.words[0]));
    audit.innerHTML = src
      ? `<strong>Audit trail</strong> <button type="button" class="help" data-tip="Kedjan bakom en post: parti → källa → dok_id → URL.">help</button>
         <ol><li>${first.name}</li><li>${src.label}</li><li>${src.dok_id || "—"}</li><li><a href="${src.url}" rel="noopener">primärkälla</a></li></ol>`
      : "<strong>Audit trail</strong><p>underlag saknas</p>";
  }
}

Promise.all([loadJson("quotes.json"), loadJson("dataset.json")]).then(([quotes, data]) => {
  DATA = data;
  startSauron(quotes);
  if (DATA) fillFilters();
  renderAll();
  const close = document.getElementById("sheet-close");
  if (close) close.onclick = () => {
    document.getElementById("sheet").hidden = true;
  };
});
