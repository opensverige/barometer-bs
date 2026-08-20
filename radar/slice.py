from __future__ import annotations

import json
from pathlib import Path

from radar.kpis import freeze_match_ratio, locator_kpi, snapshot_blob, snapshot_hash
from radar.models import Claim, DerivedFrom, Locator, Source
from radar.store import upsert_sources
from radar.title_gate import title_is_on_topic

ACTORS = [
    ("s", "Socialdemokraterna"),
    ("m", "Moderaterna"),
    ("sd", "Sverigedemokraterna"),
    ("v", "Vänsterpartiet"),
    ("mp", "Miljöpartiet"),
    ("c", "Centerpartiet"),
    ("kd", "Kristdemokraterna"),
    ("l", "Liberalerna"),
]
BANNED = {"HD024115", "HD024156"}


def _source(rec: dict, retrieved: str) -> Source | None:
    dok = rec["dok_id"]
    if dok in BANNED:
        return None
    if rec["kind"] == "motion" and not title_is_on_topic(rec["title"]):
        return None
    blob = snapshot_blob(dok, rec["title"], rec["rm"], rec["published_at"])
    kind = {"motion": "motion", "beslut": "beslut", "party_page": "party_page", "anforande": "anforande", "votering": "votering"}.get(
        rec["kind"], rec["kind"]
    )
    layer = "L3" if rec["kind"] == "party_page" else "L1"
    return Source(
        source_id=f"{layer.lower()}:{kind}:{dok}" + (f":{rec['punkt']}" if rec.get("punkt") else ""),
        layer=layer,  # type: ignore[arg-type]
        kind=kind,  # type: ignore[arg-type]
        locator=Locator(url=rec["url"], official_id=dok, official_id_kind="dok_id" if layer == "L1" else None),
        retrieved_at=retrieved,
        published_at=rec.get("published_at"),
        content_hash=snapshot_hash(blob),
        attribution="Sveriges riksdag" if layer == "L1" else rec.get("actor_id") or "",
        vote_data=rec.get("vote_data"),
        punkt=rec.get("punkt"),
    )


def load_freeze(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def records_to_sources(freeze: dict) -> list[Source]:
    retrieved = freeze["frozen_at"]
    out: list[Source] = []
    for rec in freeze["records"]:
        src = _source(rec, retrieved)
        if src:
            out.append(src)
    return upsert_sources([], out)


def _item(rec: dict, role: str) -> dict:
    item = {"label": rec["title"], "url": rec["url"], "date": rec["published_at"], "rm": rec["rm"], "role": role}
    if rec.get("dok_id"):
        item["dok_id"] = rec["dok_id"]
    if rec.get("punkt"):
        item["punkt"] = rec["punkt"]
    if rec.get("vote_data") == "none":
        item["vote_data"] = "none"
        item["label"] = rec["title"] + " — partiröst okänd (acklamation)"
    return item


def build_ui(freeze: dict) -> dict:
    sources = records_to_sources(freeze)
    by_actor: dict[str, dict] = {
        aid: {"actor_id": aid, "name": name, "words": [], "actions": [], "votes": [], "timeline": [], "flag": None}
        for aid, name in ACTORS
    }
    related_to_actor: dict[str, str] = {}
    for rec in freeze["records"]:
        if rec["kind"] == "motion" and rec.get("actor_id"):
            related_to_actor[rec["dok_id"]] = rec["actor_id"]

    for rec in freeze["records"]:
        if rec["kind"] == "motion" and not title_is_on_topic(rec["title"]):
            continue
        aid = rec.get("actor_id")
        if rec["kind"] == "party_page" and aid in by_actor:
            item = _item(rec, "sade")
            by_actor[aid]["words"].append(item)
            by_actor[aid]["timeline"].append(item)
        elif rec["kind"] == "motion" and aid in by_actor:
            item = _item(rec, "skrev")
            by_actor[aid]["actions"].append(item)
            by_actor[aid]["timeline"].append(item)
        elif rec["kind"] in {"votering", "beslut"}:
            target = aid or related_to_actor.get(rec.get("related_dok_id") or "")
            item = _item(rec, "rostade")
            if rec.get("vote_data") == "none":
                item["abstain"] = True
            if target in by_actor:
                by_actor[target]["votes"].append(item)
                by_actor[target]["timeline"].append(item)

    for party in by_actor.values():
        has_w = bool(party["words"])
        has_a = bool(party["actions"])
        if has_w and not has_a:
            party["flag"] = "words_without_action"
        elif has_a and not has_w:
            party["flag"] = "action_without_words"
        party["timeline"].sort(key=lambda x: x.get("date") or "")

    then_vs_now = []
    for party in by_actor.values():
        tl = party["timeline"]
        if len(tl) >= 2:
            t1, t2 = tl[0], tl[-1]
            voted = [x for x in party["votes"] if not x.get("abstain")]
            then_vs_now.append({
                "actor_id": party["actor_id"],
                "name": party["name"],
                "t1": t1,
                "t2": t2,
                "status": "open" if voted else "underlag_saknas",
                "summary": (
                    f"{t1['date']}: {t1['role']} → {t2['date']}: {t2['role']}. "
                    + ("Registrerad vändning saknas — acklamation ger ingen partiröst." if not voted else "Två tidpunkter med källor.")
                ),
            })

    claims: list[Claim] = []
    src_index = {s.source_id: s for s in sources}
    for src in sources:
        if src.kind == "motion" and src.locator.official_id:
            claims.append(
                Claim(
                    claim_id=f"cl:src:{src.source_id}",
                    actor_id="sd",
                    topic_id="ai",
                    statement=src.locator.official_id,
                    stance="silent",
                    claim_role="action",
                    derived_from=(DerivedFrom(src.source_id),),
                    evidence_score=0.7,
                )
            )
    # locator KPI must not invent stance; silent + derived_from is enough for coverage
    loc = locator_kpi(
        [
            Claim(
                claim_id=f"cl:{s.source_id}",
                actor_id="s",
                topic_id="ai",
                statement=s.locator.official_id or s.source_id,
                stance="silent",
                claim_role="words" if s.layer == "L3" else "action",
                derived_from=(DerivedFrom(s.source_id),),
                evidence_score=0.4 if s.layer == "L3" else 0.7,
            )
            for s in sources
        ],
        src_index,
    )
    freeze_rows = []
    for rec in freeze["records"]:
        blob = snapshot_blob(rec["dok_id"], rec["title"], rec["rm"], rec["published_at"])
        freeze_rows.append({"snapshot": blob, "content_hash": snapshot_hash(blob)})

    by_rm = {w: 0 for w in freeze["windows"]}
    for rec in freeze["records"]:
        if rec["kind"] == "motion" and title_is_on_topic(rec["title"]):
            by_rm[rec["rm"]] = by_rm.get(rec["rm"], 0) + 1

    return {
        "as_of": freeze["frozen_at"][:10],
        "run_id": "ai-3rm-slice",
        "topic_id": "ai",
        "topic_label": "Artificiell intelligens",
        "attribution": "Sveriges riksdag",
        "windows": freeze["windows"],
        "coverage": {"motions_title_gated_by_rm": by_rm, "anforanden": 0, "recorded_party_votes": 0},
        "kpis": {
            "locator": loc,
            "freeze_match": freeze_match_ratio(freeze_rows),
        },
        "note": freeze.get("note"),
        "then_vs_now": then_vs_now,
        "parties": list(by_actor.values()),
    }


def write_web_dataset(freeze_path: Path, out: Path) -> dict:
    ui = build_ui(load_freeze(freeze_path))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ui, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ui
