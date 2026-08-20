const FLAG_SV = {
  words_without_action: "Säger AI på webben. Ingen motion i urvalet.",
  action_without_words: "Skrev i kammaren. Ingen AI-sida i urvalet.",
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

function render(data) {
  if (!data) {
    document.getElementById("grid").textContent = "dataset.json saknas";
    return;
  }
  const loc = data.kpis && (data.kpis.locator ?? data.kpis.metadata_freeze_match);
  const frz = data.kpis && data.kpis.metadata_freeze_match;
  const cov = (data.coverage && data.coverage.motions_title_gated_by_rm) || {};
  document.getElementById("meta").innerHTML =
    `Topic: <strong>AI</strong> · rm ${ (data.windows || []).join(" · ") || "—" } · locator ${data.kpis && data.kpis.locator == null ? "—" : Math.round((data.kpis.locator || 0) * 100) + "%"} · freeze ${frz == null ? "—" : Math.round(frz * 100) + "%"} · titel-gate 23/24:${cov["2023/24"] ?? "—"}`;

  const tvn = document.getElementById("tvn");
  if (!data.then_vs_now || !data.then_vs_now.length) {
    tvn.hidden = true;
    tvn.innerHTML = "";
  } else {
    tvn.hidden = false;
    tvn.innerHTML = data.then_vs_now
      .map((x) => `<div class="tvn-card"><strong>${x.name}</strong> — then_vs_now: ${x.status}<br />${x.summary}<br /><a href="${x.t1.url}" rel="noopener">t1</a> · <a href="${x.t2.url}" rel="noopener">t2</a></div>`)
      .join("");
  }

  const hits = (data.parties || []).filter((p) => p.flag);
  document.getElementById("flags").innerHTML = hits
    .map((p) => {
      const src = [...(p.words || []), ...(p.actions || [])][0];
      return `<div class="flag"><strong>${p.name}</strong> — ${FLAG_SV[p.flag] || p.flag} ${src ? `<a href="${src.url}" rel="noopener">källa</a>` : ""}</div>`;
    })
    .join("");

  document.getElementById("grid").innerHTML = (data.parties || [])
    .map((p) => {
      const votes = p.votes || [];
      const decisions = p.decisions || [];
      return `<article class="card">
        <h2>${p.name}</h2>
        <p class="row"><span class="k">Sade</span>${links(p.words, "underlag saknas")}</p>
        <p class="row"><span class="k">Skrev</span>${links(p.actions, "underlag saknas")}</p>
        <p class="row"><span class="k">Röstade</span>${links(votes, "underlag saknas")}</p>
        <p class="row"><span class="k">Beslutades</span>${links(decisions, "underlag saknas")}</p>
        ${p.flag ? `<span class="badge">${FLAG_SV[p.flag]}</span>` : ""}
      </article>`;
    })
    .join("");
}

Promise.all([loadJson("quotes.json"), loadJson("dataset.json")]).then(([quotes, data]) => {
  startSauron(quotes);
  render(data);
});
