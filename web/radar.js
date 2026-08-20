const FLAG_SV = {
  words_without_action: "Säger AI på webben. Ingen motion i urvalet.",
  action_without_words: "Skrev i kammaren. Tyst på AI-sidan.",
};

async function loadDataset() {
  const tries = ["dataset.json", "/dataset.json", "/web/dataset.json"];
  for (const url of tries) {
    try {
      const res = await fetch(url);
      if (res.ok) return res.json();
    } catch (_err) {
      /* next */
    }
  }
  throw new Error("dataset.json saknas");
}

function linkList(items, empty) {
  if (!items.length) return `<span class="empty">${empty}</span>`;
  return items
    .map((x) => `<a href="${x.url}" rel="noopener">${x.label}</a>`)
    .join("<br />");
}

function render(data) {
  const flags = document.getElementById("flags");
  const grid = document.getElementById("grid");
  const hits = data.parties.filter((p) => p.flag);
  flags.innerHTML = hits.length
    ? hits
        .map((p) => {
          const src = [...p.words, ...p.actions][0];
          const href = src ? src.url : "#";
          return `<div class="flag"><strong>${p.name}</strong> — ${FLAG_SV[p.flag]} ${src ? `<a href="${href}" rel="noopener">källa</a>` : ""}</div>`;
        })
        .join("")
    : `<div class="flag">Inga frånvarokonflikter i urvalet.</div>`;

  grid.innerHTML = data.parties
    .map(
      (p) => `<article class="card">
        <h2>${p.name}</h2>
        <p class="row"><span class="k">Sade</span>${linkList(p.words, "tyst i urvalet")}</p>
        <p class="row"><span class="k">Skrev</span>${linkList(p.actions, "ingen motion i urvalet")}</p>
        <p class="row"><span class="k">Röstade</span>${linkList(p.votes, "ingen votering i urvalet")}</p>
        ${p.flag ? `<span class="badge">${FLAG_SV[p.flag]}</span>` : ""}
      </article>`
    )
    .join("");
}

loadDataset().then(render).catch((err) => {
  document.getElementById("grid").textContent = err.message;
});
