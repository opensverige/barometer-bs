const FLAG_SV = {
  words_without_action: "Säger på webben. Ingen motion i urvalet.",
  action_without_words: "Skrev i kammaren. Ingen topic-sida i urvalet.",
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

function flowLine(party) {
  const said = (party.words && party.words[0]) || null;
  const did = (party.actions && party.actions[0]) || (party.votes && party.votes[0]) || (party.decisions && party.decisions[0]) || null;
  const left = said ? `<a href="${said.url}" rel="noopener">primärkälla</a>` : "ingen L3";
  const right = did ? `<a href="${did.url}" rel="noopener">${did.dok_id || "L1"}</a>` : "ingen L1";
  return `<span class="conflict-flow">Säger → ${left} → men i riksdagen → ${right}</span>`;
}

let DATA = null;

function visibleParties() {
  const topic = document.getElementById("filter-topic").value;
  const party = document.getElementById("filter-party").value;
  const topicId = DATA.topic_id || (DATA.topics && DATA.topics[0] && DATA.topics[0].topic_id) || "";
  if (topic && topicId && topic !== topicId && topic !== "all") return [];
  return (DATA.parties || []).filter((p) => party === "all" || p.actor_id === party);
}

function fillFilters() {
  const topicSel = document.getElementById("filter-topic");
  const partySel = document.getElementById("filter-party");
  const topics = DATA.topics && DATA.topics.length
    ? DATA.topics
    : [{ topic_id: DATA.topic_id || "unknown", label: DATA.topic_label || DATA.topic_id || "topic" }];
  topicSel.innerHTML = topics.map((t) => `<option value="${t.topic_id || t}">${t.label || t.topic_label || t.topic_id || t}</option>`).join("");
  partySel.innerHTML = `<option value="all">Alla</option>` +
    (DATA.parties || []).map((p) => `<option value="${p.actor_id}">${p.name}</option>`).join("");
  topicSel.onchange = renderAll;
  partySel.onchange = renderAll;
}

function renderAll() {
  if (!DATA) {
    document.getElementById("grid").textContent = "dataset.json saknas";
    return;
  }
  const loc = DATA.kpis && DATA.kpis.locator;
  const frz = DATA.kpis && DATA.kpis.metadata_freeze_match;
  const cov = (DATA.coverage && DATA.coverage.motions_title_gated_by_rm) || {};
  const topicLabel = DATA.topic_label || DATA.topic_id || "topic";
  document.getElementById("meta").innerHTML =
    `Topic: <strong>${topicLabel}</strong> · rm ${(DATA.windows || []).join(" · ") || "—"} · locator ${loc == null ? "—" : Math.round(loc * 100) + "%"} · freeze ${frz == null ? "—" : Math.round(frz * 100) + "%"} · 23/24:${cov["2023/24"] ?? "—"}`;

  const tvn = document.getElementById("tvn");
  if (!DATA.then_vs_now || !DATA.then_vs_now.length) {
    tvn.hidden = true;
    tvn.innerHTML = "";
  } else {
    tvn.hidden = false;
    tvn.innerHTML = DATA.then_vs_now
      .map((x) => `<div class="tvn-card"><strong>${x.name}</strong> — then_vs_now: ${x.status}<br />${x.summary}<br /><a href="${x.t1.url}" rel="noopener">t1</a> · <a href="${x.t2.url}" rel="noopener">t2</a></div>`)
      .join("");
  }

  const parties = visibleParties();
  const hits = parties.filter((p) => p.flag);
  document.getElementById("flags").innerHTML = hits
    .map((p) => {
      const src = [...(p.words || []), ...(p.actions || [])][0];
      return `<div class="flag">${flowLine(p)}<strong>${p.name}</strong> — ${FLAG_SV[p.flag] || p.flag} · ${p.flag} · ${DATA.topic_id || ""} ${src ? `<a href="${src.url}" rel="noopener">källa</a>` : ""}</div>`;
    })
    .join("");

  document.getElementById("grid").innerHTML = parties
    .map((p) => {
      const votes = p.votes || [];
      const decisions = p.decisions || [];
      return `<article class="card" id="actor-${p.actor_id}">
        <h2><span class="dot ${p.actor_id}" aria-hidden="true"></span>${p.name}</h2>
        ${flowLine(p)}
        <p class="row"><span class="k">Sade</span>${links(p.words, "underlag saknas")}</p>
        <p class="row"><span class="k">Skrev</span>${links(p.actions, "underlag saknas")}</p>
        <p class="row"><span class="k">Röstade</span>${links(votes, "underlag saknas")}</p>
        <p class="row"><span class="k">Beslutades</span>${links(decisions, "underlag saknas")}</p>
        ${p.flag ? `<span class="badge">${FLAG_SV[p.flag]}</span>` : ""}
      </article>`;
    })
    .join("");

  const first = parties.find((p) => (p.actions && p.actions[0]) || (p.words && p.words[0]));
  const src = first && ((first.actions && first.actions[0]) || (first.words && first.words[0]));
  document.getElementById("audit").innerHTML = src
    ? `<strong>Audit trail</strong><ol>
        <li>Claim / post: ${first.name}</li>
        <li>Source: ${src.label}</li>
        <li>Dokument: ${src.kind || "—"}</li>
        <li>official ID: ${src.dok_id || "—"}${src.punkt ? " · punkt " + src.punkt : ""}</li>
        <li>Primärkälla: <a href="${src.url}" rel="noopener">${src.url}</a></li>
        <li>Hash: ${DATA.kpis && DATA.kpis.metadata_freeze_match != null ? "metadata_freeze_match " + DATA.kpis.metadata_freeze_match : "oseglad"}</li>
      </ol>`
    : "<strong>Audit trail</strong><p>underlag saknas</p>";
}

Promise.all([loadJson("quotes.json"), loadJson("dataset.json")]).then(([quotes, data]) => {
  DATA = data;
  startSauron(quotes);
  if (DATA) fillFilters();
  renderAll();
});
