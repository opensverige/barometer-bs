const GLYPH = {
  K: "♔", Q: "♕", R: "♖", B: "♗", N: "♘", P: "♙",
  k: "♚", q: "♛", r: "♜", b: "♝", n: "♞", p: "♟",
};

function startBoard() {
  return [
    ["r", "n", "b", "q", "k", "b", "n", "r"],
    ["p", "p", "p", "p", "p", "p", "p", "p"],
    [".", ".", ".", ".", ".", ".", ".", "."],
    [".", ".", ".", ".", ".", ".", ".", "."],
    [".", ".", ".", ".", ".", ".", ".", "."],
    [".", ".", ".", ".", ".", ".", ".", "."],
    ["P", "P", "P", "P", "P", "P", "P", "P"],
    ["R", "N", "B", "Q", "K", "B", "N", "R"],
  ].map((row) => row.slice());
}

function sqToRc(sq) {
  const file = sq.charCodeAt(0) - 97;
  const rank = Number(sq[1]);
  return [8 - rank, file];
}

function applyMove(board, move) {
  const [r1, c1] = sqToRc(move.from);
  const [r2, c2] = sqToRc(move.to);
  const next = board.map((row) => row.slice());
  next[r2][c2] = next[r1][c1];
  next[r1][c1] = ".";
  return next;
}

function boardAt(moves, ply) {
  let board = startBoard();
  for (let i = 0; i < ply; i++) board = applyMove(board, moves[i]);
  return board;
}

function eventById(match, sourceId) {
  return (match.events || []).find((e) => e.source_id === sourceId) || null;
}

const state = { match: null, ply: 0, timer: null, selected: null };

function warnEl() {
  return document.getElementById("demo-warn");
}

function renderBoard() {
  const board = boardAt(state.match.moves, state.ply);
  const el = document.getElementById("board");
  const move = state.match.moves[state.ply - 1];
  el.innerHTML = "";
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < 8; c++) {
      const sq = document.createElement("button");
      sq.type = "button";
      const file = String.fromCharCode(97 + c);
      const name = file + String(8 - r);
      sq.className = "sq " + ((r + c) % 2 === 0 ? "light" : "dark");
      if (move && (move.from === name || move.to === name)) sq.classList.add("active");
      const piece = board[r][c];
      sq.textContent = piece === "." ? "" : GLYPH[piece] || piece;
      sq.dataset.square = name;
      sq.dataset.piece = piece;
      sq.addEventListener("click", () => onSquare(name, piece, move));
      el.appendChild(sq);
    }
  }
  document.getElementById("timeline").value = String(state.ply);
  watchEye(move);
  if (move) showCard(eventById(state.match, move.source_id), move);
}

function watchEye(move) {
  const eye = document.getElementById("eye");
  const pupil = document.getElementById("pupil");
  if (!move) {
    eye.style.transform = "translateX(0)";
    pupil.setAttribute("transform", "");
    eye.classList.remove("flare");
    return;
  }
  const file = move.to.charCodeAt(0) - 97;
  const dx = (file - 3.5) * 6;
  eye.style.transform = `translateX(${dx}px)`;
  pupil.setAttribute("transform", `translate(${dx * 0.3} 0)`);
  const ev = eventById(state.match, move.source_id);
  eye.classList.toggle("flare", !!(ev && (ev.contradiction || ev.evidence === "strong")));
}

function showCard(ev, move) {
  const card = document.getElementById("card");
  if (!ev) {
    card.hidden = true;
    return;
  }
  card.hidden = false;
  card.innerHTML = `<strong>${ev.label}</strong><br/>typ: ${ev.kind}<br/>datum: ${ev.date}<br/>dok_id: ${ev.dok_id || "—"}<br/>punkt: ${ev.punkt || "—"}<br/>source_id: ${ev.source_id}<br/><a href="${ev.url}" rel="noopener">källa</a>`;
}

function onSquare(name, piece, move) {
  if (move && (move.from === name || move.to === name)) {
    showCard(eventById(state.match, move.source_id), move);
  }
}

function setPly(n) {
  const max = state.match.moves.length;
  state.ply = Math.max(0, Math.min(max, n));
  renderBoard();
}

function play() {
  pause();
  state.timer = setInterval(() => {
    if (state.ply >= state.match.moves.length) {
      pause();
      return;
    }
    setPly(state.ply + 1);
  }, 900);
}

function pause() {
  if (state.timer) clearInterval(state.timer);
  state.timer = null;
}

function fillSelects() {
  const w = document.getElementById("white-sel");
  const b = document.getElementById("black-sel");
  w.innerHTML = "";
  b.innerHTML = "";
  for (const p of state.match.players) {
    const o1 = new Option(p.label, p.id);
    const o2 = new Option(p.label, p.id);
    w.add(o1);
    b.add(o2);
  }
  w.value = state.match.players[0].id;
  b.value = state.match.players[1].id;
}

async function boot() {
  const warn = warnEl();
  if (warn) warn.hidden = false;
  const res = await fetch("match-demo.json");
  state.match = await res.json();
  if (!state.match.demo || state.match.warning !== "VISUAL DEMO — INTE POLITISK DATA") {
    document.body.textContent = "Demo-varning saknas. Avbryter.";
    return;
  }
  document.getElementById("timeline").max = String(state.match.moves.length);
  fillSelects();
  document.getElementById("prev").onclick = () => setPly(state.ply - 1);
  document.getElementById("next").onclick = () => setPly(state.ply + 1);
  document.getElementById("play").onclick = play;
  document.getElementById("pause").onclick = pause;
  document.getElementById("timeline").oninput = (e) => setPly(Number(e.target.value));
  setPly(0);
}

boot();
