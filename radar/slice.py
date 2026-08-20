from __future__ import annotations

import json
from pathlib import Path

from radar.kpis import locator_kpi, metadata_freeze_match_ratio, snapshot_blob, snapshot_hash
from radar.store import upsert_sources
from radar.title_gate import title_is_on_topic
from radar.models import Locator, Source

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
COMPARABLE_STANCES = {"support", "oppose"}


def _ensure_snapshot(rec: dict) -> str:
    if rec.get("snapshot"):
        return rec["snapshot"]
    ident = rec.get("dok_id") or rec.get("url") or ""
    return snapshot_blob(ident, rec.get("title") or "", rec.get("rm") or "", rec.get("published_at") or "")


def attach_current_hash(rec: dict) -> dict:
    rec = dict(rec)
    rec["snapshot"] = _ensure_snapshot(rec)
    rec["content_hash"] = snapshot_hash(rec["snapshot"])
    return rec


def _source(rec: dict, retrieved: str) -> Source | None:
    kind = rec["kind"]
    if kind == "motion" and not title_is_on_topic(rec.get("title") or ""):
        return None
    dok = rec.get("dok_id")
    if dok in BANNED:
        return None
    if kind == "party_page":
        dok = None
    rec = attach_current_hash(rec)
    layer = "L3" if kind == "party_page" else "L1"
    id_part = dok or rec.get("url") or kind
    return Source(
        source_id=f"{layer.lower()}:{kind}:{id_part}" + (f":{rec['punkt']}" if rec.get("punkt") else ""),
        layer=layer,  # type: ignore[arg-type]
        kind=kind,  # type: ignore[arg-type]
        locator=Locator(
            url=rec["url"],
            official_id=dok,
            official_id_kind="dok_id" if dok and layer == "L1" else None,
        ),
        retrieved_at=retrieved,
        published_at=rec.get("published_at"),
        content_hash=rec["content_hash"],
        attribution="Sveriges riksdag" if layer == "L1" else rec.get("actor_id") or "",
        vote_data="none" if rec.get("vote_method") == "acclamation" else rec.get("vote_data"),
        punkt=rec.get("punkt"),
    )


def load_freeze(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def records_to_sources(freeze: dict) -> list[Source]:
    out: list[Source] = []
    for rec in freeze["records"]:
        src = _source(rec, freeze["frozen_at"])
        if src:
            out.append(src)
    return upsert_sources([], out)


def source_to_schema(source: Source) -> dict:
    loc: dict = {}
    if source.locator.url:
        loc["url"] = source.locator.url
    if source.locator.official_id:
        loc["official_id"] = source.locator.official_id
    if source.locator.official_id_kind:
        loc["official_id_kind"] = source.locator.official_id_kind
    payload = {
        "source_id": source.source_id,
        "layer": source.layer,
        "kind": source.kind,
        "locator": loc,
        "retrieved_at": source.retrieved_at,
        "content_hash": source.content_hash,
        "attribution": source.attribution,
    }
    if source.published_at:
        payload["published_at"] = source.published_at
    if source.vote_data:
        payload["vote_data"] = source.vote_data
    if source.punkt:
        payload["punkt"] = source.punkt
    return payload


def _is_acclamation_record(rec: dict) -> bool:
    return rec.get("vote_method") == "acclamation"


def _item(rec: dict, role: str) -> dict:
    item = {
        "label": rec["title"],
        "url": rec["url"],
        "date": rec["published_at"],
        "rm": rec["rm"],
        "role": role,
        "kind": rec["kind"],
    }
    if rec.get("actor_id"):
        item["actor_id"] = rec["actor_id"]
    if rec.get("dok_id") and rec["kind"] != "party_page":
        item["dok_id"] = rec["dok_id"]
    if rec.get("punkt"):
        item["punkt"] = rec["punkt"]
    if rec.get("party_vote") in COMPARABLE_STANCES and not _is_acclamation_record(rec):
        item["party_vote"] = rec["party_vote"]
        item["vote_method"] = rec.get("vote_method") or "recorded"
    if _is_acclamation_record(rec):
        item["decision_result"] = rec.get("decision_result") or "known"
        item["vote_method"] = "acclamation"
        item["party_vote"] = "unknown"
        item["role"] = "beslutades"
    return item


def _comparable_positions(party: dict) -> list[dict]:
    return [
        item
        for item in party["votes"]
        if item.get("party_vote") in COMPARABLE_STANCES and item.get("vote_method") != "acclamation"
    ]


def _dedupe(items: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    uniq: list[dict] = []
    for item in items:
        key = (item.get("dok_id"), item.get("punkt"), item.get("url"), item.get("role"))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)
    return uniq


def build_ui(freeze: dict) -> dict:
    hashed_records = [attach_current_hash(rec) for rec in freeze["records"]]
    freeze = {**freeze, "records": hashed_records}
    by_actor: dict[str, dict] = {
        aid: {
            "actor_id": aid,
            "name": name,
            "words": [],
            "actions": [],
            "votes": [],
            "decisions": [],
            "timeline": [],
            "flag": None,
        }
        for aid, name in ACTORS
    }
    related_to_actor: dict[str, str] = {}
    for rec in freeze["records"]:
        if rec["kind"] == "motion" and rec.get("actor_id") and rec.get("dok_id"):
            related_to_actor[rec["dok_id"]] = rec["actor_id"]

    for rec in freeze["records"]:
        if rec["kind"] == "motion" and not title_is_on_topic(rec.get("title") or ""):
            continue
        actor = rec.get("actor_id")
        if rec["kind"] == "party_page" and actor in by_actor:
            item = _item(rec, "sade")
            by_actor[actor]["words"].append(item)
            by_actor[actor]["timeline"].append(item)
            continue
        if rec["kind"] == "motion" and actor in by_actor:
            item = _item(rec, "skrev")
            by_actor[actor]["actions"].append(item)
            by_actor[actor]["timeline"].append(item)
            continue
        if _is_acclamation_record(rec):
            target = actor or related_to_actor.get(rec.get("related_dok_id") or "")
            item = _item(rec, "beslutades")
            if target in by_actor:
                by_actor[target]["decisions"].append(item)
                by_actor[target]["timeline"].append(item)
            continue
        if rec["kind"] == "votering" and actor in by_actor:
            item = _item(rec, "rostade")
            by_actor[actor]["votes"].append(item)
            by_actor[actor]["timeline"].append(item)

    then_vs_now = []
    for party in by_actor.values():
        party["decisions"] = _dedupe(party["decisions"])
        party["votes"] = [v for v in party["votes"] if v.get("vote_method") != "acclamation"]
        has_w = bool(party["words"])
        has_a = bool(party["actions"])
        if has_w and not has_a:
            party["flag"] = "words_without_action"
        elif has_a and not has_w:
            party["flag"] = "action_without_words"
        party["timeline"].sort(key=lambda x: x.get("date") or "")
        pos = _comparable_positions(party)
        if len(pos) >= 2 and pos[0].get("party_vote") != pos[-1].get("party_vote"):
            t1, t2 = pos[0], pos[-1]
            then_vs_now.append({
                "actor_id": party["actor_id"],
                "name": party["name"],
                "t1": t1,
                "t2": t2,
                "status": "open",
                "summary": f"{t1['date']}: {t1.get('party_vote')} → {t2['date']}: {t2.get('party_vote')}",
            })

    by_rm = {w: 0 for w in freeze["windows"]}
    for rec in freeze["records"]:
        if rec["kind"] == "motion" and title_is_on_topic(rec.get("title") or ""):
            by_rm[rec["rm"]] = by_rm.get(rec["rm"], 0) + 1

    return {
        "as_of": freeze["frozen_at"][:10],
        "run_id": "ai-3rm-slice",
        "topic_id": "ai",
        "topic_label": "Artificiell intelligens",
        "attribution": "Sveriges riksdag",
        "windows": freeze["windows"],
        "coverage": {
            "motions_title_gated_by_rm": by_rm,
            "anforanden": 0,
            "recorded_party_votes": sum(
                1
                for r in freeze["records"]
                if r.get("kind") == "votering"
                and r.get("party_vote") in COMPARABLE_STANCES
                and r.get("vote_method") != "acclamation"
            ),
        },
        "kpis": {
            "locator": locator_kpi(freeze["records"]),
            "metadata_freeze_match": metadata_freeze_match_ratio(freeze["records"]),
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
