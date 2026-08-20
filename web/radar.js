const FLAG_SV = {
  words_without_action: "Säger AI på webben. Ingen motion i urvalet.",
  action_without_words: "Skrev i kammaren. Ingen AI-sida i urvalet.",
};

async function loadDataset() {
  for (const url of ["dataset.json", "/dataset.json", "/web/dataset.json"]) {
    try {
      const res = await fetch(url);
      if (res.ok) return res.json();
    } catch (_e) {}
  }
  throw new Error("dataset.json saknas");
}

function isAcclamation(x) {
  return x.vote_method === "acclamation";
}

function links(items, empty) {
  if (!items.length) return `<span class="empty">${empty}</span>`;
  return items
    .map((x) => {
      const note = isAcclamation(x) ? " — partiröst okänd" : "";
      const date = x.date ? ` <span class="empty">${x.date}</span>` : "";
      return `<a href="${x.url}" rel="noopener">${x.label}</a>${date}${note}`;
    })
    .join("<br />");
}

function render(data) {
  const loc = data.kpis && data.kpis.locator;
  const frz = data.kpis && data.kpis.metadata_freeze_match;
  const cov = (data.coverage && data.coverage.motions_title_gated_by_rm) || {};
  document.getElementById("meta").innerHTML =
    `Topic: <strong>AI</strong> · rm ${ (data.windows || []).join(" · ") } · locator ${loc == null ? "—" : Math.round(loc * 100) + "%"} · metadata_freeze_match ${frz == null ? "—" : Math.round(frz * 100) + "%"} · titel-gate 23/24:${cov["2023/24"] ?? 0} 24/25:${cov["2024/25"] ?? 0} 25/26:${cov["2025/26"] ?? 0}`;

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

  const hits = data.parties.filter((p) => p.flag);
  document.getElementById("flags").innerHTML = hits
    .map((p) => {
      const src = [...p.words, ...p.actions][0];
      return `<div class="flag"><strong>${p.name}</strong> — ${FLAG_SV[p.flag] || p.flag} ${src ? `<a href="${src.url}" rel="noopener">källa</a>` : ""}</div>`;
    })
    .join("");

  document.getElementById("grid").innerHTML = data.parties
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

loadDataset().then(render).catch((err) => {
  document.getElementById("grid").textContent = err.message;
});
