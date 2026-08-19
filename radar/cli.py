from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from radar.conflicts import detect
from radar.models import Dataset
from radar.validate import load_dataset, validate_payload


def cmd_validate(path: Path) -> int:
    _, errors = load_dataset(path)
    if errors:
        print("INVALID")
        for err in errors:
            print(f"- {err}")
        return 1
    print(f"OK {path}")
    return 0


def cmd_detect(path: Path, write: bool) -> int:
    payload, errors = load_dataset(path)
    if errors:
        print("INVALID dataset, abort detect")
        for err in errors:
            print(f"- {err}")
        return 1
    ds = Dataset.from_dict(payload)
    found = detect(ds.claims, ds.source_index(), detected_at=f"{ds.as_of}T00:00:00Z")
    payload["conflicts"] = [c.to_dict() for c in found]
    types = sorted({c.type for c in found})
    print(json.dumps({"count": len(found), "types": types, "conflicts": payload["conflicts"]}, ensure_ascii=False, indent=2))
    if write:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


def cmd_ingest(source: str, rms: list[str], topic: str, out: Path) -> int:
    if source == "riksdagen":
        from radar.adapters.riksdagen import RiksdagenAdapter

        aliases = ["AI", "artificiell intelligens"]
        topics = json.loads(Path("config/topics.json").read_text(encoding="utf-8"))
        for t in topics:
            if t["topic_id"] == topic:
                aliases = t["aliases"]
                break
        adapter = RiksdagenAdapter(aliases=aliases)
        raw = adapter.fetch(rms)
        sources = adapter.normalize(raw)
        claims = adapter.extract(sources, topic, raw=raw)
        payload = {
            "as_of": rms[-1] if rms else "",
            "run_id": f"ingest-riksdagen-{topic}",
            "spec_version": "0.1.0",
            "actors": json.loads(Path("config/actors.json").read_text(encoding="utf-8")),
            "topics": json.loads(Path("config/topics.json").read_text(encoding="utf-8")),
            "sources": [_source_dict(s) for s in sources],
            "claims": [_claim_dict(c) for c in claims],
            "conflicts": [],
            "ingest_errors": adapter.errors,
        }
    elif source == "partyweb":
        from radar.adapters.partyweb import PartywebAdapter

        pages = json.loads(Path("config/party_pages.json").read_text(encoding="utf-8"))["pages"]
        pages = [p for p in pages if p["topic_id"] == topic]
        adapter = PartywebAdapter(pages)
        raw = adapter.fetch(rms)
        sources = adapter.normalize(raw)
        payload = {
            "as_of": "partyweb",
            "run_id": f"ingest-partyweb-{topic}",
            "spec_version": "0.1.0",
            "actors": json.loads(Path("config/actors.json").read_text(encoding="utf-8")),
            "topics": json.loads(Path("config/topics.json").read_text(encoding="utf-8")),
            "sources": [_source_dict(s) for s in sources],
            "claims": [],
            "conflicts": [],
            "ingest_errors": adapter.errors,
        }
    else:
        print(f"unknown source {source}")
        return 2

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} sources={len(payload['sources'])} claims={len(payload['claims'])} errors={len(payload['ingest_errors'])}")
    post = validate_payload(payload)
    if post:
        print("WARN dataset has validation issues:")
        for err in post:
            print(f"- {err}")
        return 0
    return 0


def _source_dict(s) -> dict:
    loc = {"url": s.locator.url, "official_id": s.locator.official_id, "official_id_kind": s.locator.official_id_kind}
    loc = {k: v for k, v in loc.items() if v}
    d = {
        "source_id": s.source_id,
        "layer": s.layer,
        "kind": s.kind,
        "locator": loc,
        "retrieved_at": s.retrieved_at,
        "content_hash": s.content_hash,
        "attribution": s.attribution,
    }
    if s.published_at:
        d["published_at"] = s.published_at
    if s.vote_data:
        d["vote_data"] = s.vote_data
    if s.punkt:
        d["punkt"] = s.punkt
    return d


def _claim_dict(c) -> dict:
    d = {
        "claim_id": c.claim_id,
        "actor_id": c.actor_id,
        "topic_id": c.topic_id,
        "statement": c.statement,
        "stance": c.stance,
        "claim_role": c.claim_role,
        "derived_from": [{"source_id": x.source_id, **({"quote": x.quote} if x.quote else {})} for x in c.derived_from],
        "evidence_score": c.evidence_score,
    }
    if c.polarity_notes:
        d["polarity_notes"] = c.polarity_notes
    if c.time_start:
        d["time_start"] = c.time_start
    if c.time_end:
        d["time_end"] = c.time_end
    return d


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="radar")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate")
    p_val.add_argument("path", type=Path)

    p_det = sub.add_parser("detect")
    p_det.add_argument("path", type=Path)
    p_det.add_argument("--write", action="store_true")

    p_ing = sub.add_parser("ingest")
    p_ing.add_argument("source", choices=["riksdagen", "partyweb"])
    p_ing.add_argument("--rm", action="append", dest="rms", default=[])
    p_ing.add_argument("--topic", default="ai")
    p_ing.add_argument("--out", type=Path, default=Path("data/raw/ingest.json"))

    args = parser.parse_args(argv)
    if args.cmd == "validate":
        return cmd_validate(args.path)
    if args.cmd == "detect":
        return cmd_detect(args.path, args.write)
    if args.cmd == "ingest":
        rms = args.rms or ["2024/25", "2025/26"]
        return cmd_ingest(args.source, rms, args.topic, args.out)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
