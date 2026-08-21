const FLAG_SV = {
  words_without_action: "Säger på webben. Ingen motion i urvalet.",
  action_without_words: "Skrev i kammaren. Ingen topic-sida i urvalet.",
};
const TIP = {
  sade: "Partisida i urvalet (L3). Streck = ingen AI-sida hittad här.",
  skrev: "Motion med AI i titeln (L1). Streck = ingen sådan motion i frysen.",
  rostade: "Registrerad partiröst. Acklamation räknas inte här.",
  beslutades: "Kammarbeslut, t.ex. acklamation. Partiröst då okänd.",
  konflikt: "Mismatch webb vs kammare i urvalet.",
};

function isAcclamation(x) {
  return x && x.vote_method === "acclamation";
}
function ico(name) {
  return `<svg class="ico" aria-hidden="true"><use href="#i-${name}"/></svg>`;
}
function helpBtn(tip) {
  return `<button type="button" class="ico-btn" data-tip="${tip}" aria-label="Förklaring" onclick="event.stopPropagation()">${ico("help")}</button>`;
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
  if (!items || !items.length) return `<span class="stat gap">${empty}</span>`;
  return items.map((x) => {
    const note = isAcclamation(x) ? " — partiröst okänd" : "";
    const date = x.date ? ` <span class="stat gap">${x.date}</span>` : "";
    return `<a href="${x.url}" rel="noopener">${x.label}</a>${date}${note}`;
  }).join("<br />");
}
function cell(items, tip) {
  if (items && items.length) {
    return `<span class="stat ok" title="${tip}">${ico("check")} ${items.length}</span>`;
  }
  return `<span class="stat gap" title="${tip}">${ico("dash")}</span>`;
}

let DATA = null;

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
  partySel.innerHTML = `<option value="all">Alla</option>` + (DATA.parties || []).map((p) => `<option value="${p.actor_id}">${p.name}</option>`).join("");
  topicSel.onchange = renderAll;
  partySel.onchange = renderAll;
}
function openSheet(p) {
  const dlg = document.getElementById("sheet");
  document.getElementById("sheet-body").innerHTML = `<h2>${p.name}</h2>
    <p class="stat gap">${FLAG_SV[p.flag] || "Ingen konfliktflagga i urvalet."}</p>
    <p><strong>Sade</strong><br>${links(p.words, "ingen partisida i urvalet")}</p>
    <p><strong>Skrev</strong><br>${links(p.actions, "ingen AI-motion i urvalet")}</p>
    <p><strong>Röstade</strong><br>${links(p.votes, "ingen registrerad partiröst")}</p>
    <p><strong>Beslutades</strong><br>${links(p.decisions, "inget kammarbeslut i urvalet")}</p>`;
  if (dlg && dlg.showModal) dlg.showModal();
}
function renderAll() {
  const host = document.getElementById("oversikt") || document.getElementById("grid");
  if (!DATA) {
    host.textContent = "dataset.json saknas";
    return;
  }
  const loc = DATA.kpis && DATA.kpis.locator;
  const frz = DATA.kpis && DATA.kpis.metadata_freeze_match;
  const topicLabel = DATA.topic_label || DATA.topic_id || "topic";
  document.getElementById("meta").innerHTML =
    `Topic: <strong>${topicLabel}</strong> · ${(DATA.windows || []).join(" · ") || "—"} · locator ${loc == null ? "—" : Math.round(loc * 100) + "%"} · freeze ${frz == null ? "—" : Math.round(frz * 100) + "%"}`;
  const tvn = document.getElementById("tvn");
  if (tvn) {
    if (!DATA.then_vs_now || !DATA.then_vs_now.length) { tvn.hidden = true; tvn.innerHTML = ""; }
    else {
      tvn.hidden = false;
      tvn.innerHTML = DATA.then_vs_now.map((x) => `<div>${x.name}: ${x.summary}</div>`).join("");
    }
  }
  const parties = visibleParties();
  host.innerHTML = `<table class="overview">
    <thead><tr>
      <th>Parti</th>
      <th>Sade ${helpBtn(TIP.sade)}</th>
      <th>Skrev ${helpBtn(TIP.skrev)}</th>
      <th>Röstade ${helpBtn(TIP.rostade)}</th>
      <th>Beslutades ${helpBtn(TIP.beslutades)}</th>
      <th>Konflikt ${helpBtn(TIP.konflikt)}</th>
    </tr></thead>
    <tbody>${parties.map((p) => `<tr tabindex="0" data-actor="${p.actor_id}">
      <td><img src="logos/${p.actor_id}.svg" alt="" width="20" height="20" />${p.name}</td>
      <td>${cell(p.words, TIP.sade)}</td>
      <td>${cell(p.actions, TIP.skrev)}</td>
      <td>${cell(p.votes, TIP.rostade)}</td>
      <td>${cell(p.decisions, TIP.beslutades)}</td>
      <td>${p.flag ? `<span class="stat" title="${FLAG_SV[p.flag] || p.flag}">${ico("warn")}</span>` : `<span class="stat gap">${ico("dash")}</span>`}</td>
    </tr>`).join("")}</tbody>
  </table>`;
  host.querySelectorAll("tbody tr").forEach((tr) => {
    const open = () => {
      const p = parties.find((x) => x.actor_id === tr.dataset.actor);
      if (p) openSheet(p);
    };
    tr.addEventListener("click", open);
    tr.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); }
    });
  });
  const audit = document.getElementById("audit");
  if (audit) {
    const first = parties.find((p) => (p.actions && p.actions[0]) || (p.words && p.words[0]));
    const src = first && ((first.actions && first.actions[0]) || (first.words && first.words[0]));
    audit.innerHTML = src
      ? `<h2>Audit ${helpBtn("Kedjan: parti → källa → dok_id → URL.")}</h2>
         <ol><li>${first.name}</li><li>${src.label}</li><li>${src.dok_id || "—"}</li><li><a href="${src.url}" rel="noopener">primärkälla</a></li></ol>`
      : "<h2>Audit</h2><p>underlag saknas</p>";
  }
}
Promise.all([loadJson("quotes.json"), loadJson("dataset.json")]).then(([quotes, data]) => {
  DATA = data;
  startSauron(quotes);
  if (DATA) fillFilters();
  renderAll();
});
