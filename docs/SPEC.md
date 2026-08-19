# Accountability Radar — SPEC v0.1

Implementationsneutral. Normativ för beteende, inte för stack.

**Status:** draft · **Gäller:** `opensverige/barometer-bs`  
**Produkt:** Accountability Radar (*ord mot handling*)  
**Relaterat:** [PRD](./PRD.md) · OpenSverige [manifesto](https://github.com/opensverige/.github/blob/main/manifesto.md)

Ändringar i den här filen följer §14. Breaking change i hierarki, score eller invariants = **major**.

---

## 1. Syfte

System som mäter avståndet mellan vad politiska aktörer **säger** och vad de **gör**, enbart via spårbara primärkällor.

### Är

- claim-graf + källor + konflikter över tid
- issue-agnostisk motor (första referenstopic: `ai`)
- öppen, reproducerbar pipeline som tredje part kan köra om

### Är inte

- opinionsmätning / poll-of-polls
- ranking “vem är mest X-positiv”
- röst- eller partirekommendation
- black-box “AI tycker”
- valkompass, matchquiz eller bullshit-test

One-liner: *L1-protokoll är gravitationen. Produkten är avståndet mellan words och actions — aldrig en röstmaskin.*

---

## 2. Sanningshierarki

| Lager | Typ | Exempel | Vid konflikt |
|-------|-----|---------|--------------|
| **L1** | parlamentariskt protokoll | motion, anförande, votering, betänkande/beslut | **vinner** |
| **L2** | exekutiv primärkälla | proposition, regeringsstrategi, myndighetsuppdrag | stark, under L1 vid krock |
| **L3** | aktörskommunikation | partiweb, pressmeddelande, utspel | alltid under L1/L2 |

**Regler**

1. Ingen L3-claim får publiceras som `claim_role=action` utan L1/L2-stöd.
2. L3 utan stöd = `words` only.
3. Tertiära sajter (pollaggregat, visualiseringar, journalistik) är **inte** källor. De får länkas som vidare läsning, aldrig som evidence.
4. Source utan locator får inte ingå i publicerad conflict.

---

## 3. Scope v0

| Dimension | v0 | Utvidgning (samma modell) |
|-----------|----|---------------------------|
| Aktörer | 8 riksdagspartier | ledamot, minister, utskott |
| Actions | L1 obligatoriskt + L2 | — |
| Words | L3 + anföranden som retorik | — |
| Tid | innevarande + föregående riksmöte | äldre data valfritt |
| Geografi | nationell riksdagsnivå | kommun/region är non-goal v0 |
| Topic | `ai` som referensimplementation | andra topics via taxonomi, inte ny motor |

Partiidentiteter v0 (stabila `actor_id`): `s` · `m` · `sd` · `v` · `mp` · `c` · `kd` · `l`.

Mapping parti ↔ regering är **data** (giltighetsfönster, källa), inte hårdkodad magi i UI.

---

## 4. Kärnbegrepp

### 4.1 Actor

Stabil identitet.

| Fält | Krav |
|------|------|
| `actor_id` | stabil nyckel |
| `type` | `party` \| `person` \| `org` |
| `labels` | visningsnamn, alias |
| `party_id` | valfritt, för person |

### 4.2 Topic

Kontrollerad taxonomi, utbyggbar bakåtkompatibelt via alias.

| Fält | Krav |
|------|------|
| `topic_id` | t.ex. `ai`, `energy.nuclear` |
| `definition` | 1–3 meningar: vad som ingår / utesluts |
| `aliases` | söktermer för ingest (sv + en) |

### 4.3 Source

Pekare till oföränderligt underlag.

| Fält | Krav |
|------|------|
| `source_id` | stabil nyckel |
| `layer` | `L1` \| `L2` \| `L3` |
| `kind` | `motion` \| `anforande` \| `votering` \| `beslut` \| `prop` \| `strategy` \| `party_page` \| `press` \| … |
| `locator` | kanonisk URL och/eller officiellt id (`dok_id`, `votering_id`, …) |
| `retrieved_at` | obligatoriskt |
| `published_at` | om känt |
| `content_hash` | hash av hämtad representation |
| `attribution` | utgivare; riksdagsdata anges som Sveriges riksdag |

**Invariant:** source utan locator får inte ingå i publicerad conflict.

### 4.4 Claim

En atomär, granskbar ståndpunkt.

| Fält | Krav |
|------|------|
| `claim_id` | stabil nyckel |
| `actor_id` | — |
| `topic_id` | — |
| `statement` | kort, neutralt (“stödjer X”, “vill kriminalisera Y”) |
| `stance` | `support` \| `oppose` \| `mixed` \| `conditional` \| `silent` |
| `polarity_notes` | villkor/undantag, kort |
| `claim_role` | `words` \| `action` \| `unclear` |
| `time_start` / `time_end` | giltighetsfönster om känt |
| `derived_from[]` | minst en `source_id` (+ valfri quote/span) |
| `evidence_score` | enbart funktion av källor (§7), inte “godhet” |

**Invariants**

- minst en `derived_from`
- L3-only ⇒ `claim_role=words`
- claim utan source är ogiltig och får inte publiceras

### 4.5 Conflict

Explicit spänning mellan claims (eller claim vs dokumenterad frånvaro).

| Fält | Krav |
|------|------|
| `conflict_id` | — |
| `actor_id` | samma aktör i v0 |
| `topic_id` | — |
| `type` | se nedan |
| `claim_ids[]` | ≥2, eller 1 + documented absence |
| `summary` | neutral, en mening |
| `detected_at` | — |
| `status` | `open` \| `resolved` \| `disputed` |
| `resolution_note` | valfri, med source |

**Typer**

| `type` | Betydelse |
|--------|-----------|
| `say_vs_write` | L3 vs L1-dokument |
| `write_vs_vote` | motion/reservation vs votering |
| `then_vs_now` | tidsdiff samma actor+topic |
| `words_without_action` | words finns, ingen action i fönstret |
| `action_without_words` | action finns, L3 tyst eller annorlunda |

**Invariant:** conflict får inte hävda orsak (“svek”, “hyckleri”). Bara observerbar inkonsistens.

---

## 5. Signaldefinitioner (normativa)

Systemet **måste** kunna uttrycka:

| Signal | Definition |
|--------|------------|
| say ≠ write | L3-stance ≠ L1 dokument-stance, samma topic/fönster |
| write ≠ vote | dokumenterad linje ≠ voteringsutfall (partiaggregat v0) |
| then ≠ now | stance ändras över tid utöver angivet `time_end` |
| absence | dokumenterad tystnad där peer-aktörer har claims — flagga, inte moral |

**Acklamation / saknad votering:** `vote_data: none`. Förbjudet att inferera ja/nej.

Ett betänkande kan ha **flera punkter**. Missad punkt = fel resultat. Voteringskoppling sker per punkt, inte per dokumentnamn.

---

## 6. `claim_role`-regler

| Källa | Default-roll |
|-------|----------------|
| votering, formellt beslut | `action` |
| motion / reservation / kommittémotion | `action` (skriftlig vilja i kammarprocessen) |
| party_page, press | `words` |
| anförande | `words`; får `action` **endast** om länkat till konkret yrkande/beslutspunkt med locator |
| prop / regeringsstrategi | L2 `action` för regeringsbärande aktörer enligt mapping-tabell |

---

## 7. `evidence_score`

Monoton i källstyrka. Implementationsfri form så länge:

1. L1 > L2 > L3
2. fler oberoende L1-locators höjer
3. enbart L3 ⇒ låg score + `words`
4. saknad locator ⇒ claim ogiltig för public score

Formeln publiceras i `docs/SCORING.md` vid första implementation. Byte av formel = **major** version.

Score är inte partiskhet, kvalitet på politik, eller “hur AI-positiv”.

---

## 8. Ingest

Varje adapter implementerar samma kontrakt:

```
fetch(window) → raw
normalize(raw) → Source[]
extract(sources, topic) → ClaimDraft[]
```

### Obligatoriska L1-adapters v0

- dokument (motioner m.m.)
- voteringar
- anföranden (minst metadata; text starkt rekommenderad)

Källa: [Riksdagens öppna data](https://www.riksdagen.se/sv/dokument-och-lagar/riksdagens-oppna-data/). Ingen API-nyckel. Attribution: Sveriges riksdag.

### L3-adapters v0

Kanoniska partisidor per topic. Whitelist-URL:er i config, inte fri crawl.

### Krav

- idempotent upsert på `source_id` / `content_hash`
- full provenance: när hämtat, varifrån, hash
- ingen silent drop: fel → `ingest_error`-log
- L3-sidor hashas så diff över tid syns

---

## 9. Conflict-detection

Körs efter extract, topicvis + actorvis.

- regler är **deklarativa** (testdata + expected conflicts i repo)
- varje conflict listar `claim_ids` + sources
- fria från partiskhetstermer

Golden fixtures för minst en conflict per typ i §4.5 (eller explicit “inga i fönstret” med query-audit) är acceptance, inte optional polish.

---

## 10. Agenter (valfria, kontrakt)

Agenter är produkt om de används — inte demo. Människa eller CI godkänner merge till kanonisk dataset-branch.

| Agent | Får | Får inte |
|-------|-----|----------|
| **Extract** | föreslå `ClaimDraft` från source-text | publicera utan schema-validering |
| **Adversary** | söka motbevis, äldre version, vote-mismatch | radera L1-data |
| **Publisher** | formatera audit view | ändra stance utan ny source |

Varje steg loggas som `run_id` + inputs/outputs.

Agent-review på PR: checklista (saknad `dok_id`, broken URL, stance utan L1). Inte auto-merge.

---

## 11. Logiska resurser

Implementationsneutrala. Transport valfri.

- `GET /actors`
- `GET /topics`
- `GET /claims?actor&topic&from&to&role`
- `GET /conflicts?actor&topic&status`
- `GET /sources/{id}`
- `GET /audit/claim/{id}` — full kedja claim → sources → hashes

**UI-krav (om UI finns)**

- varje visad claim har länk till primärkälla
- ingen “rekommenderad röst”
- conflict-vy är default, inte leaderboard

---

## 12. Data och licens

- kod: OSI-licens (org beslutar; rekommendation Apache-2.0 eller MIT)
- dataset: separat licensfil
- riksdagsdata: Sveriges riksdag som källa, deras villkor
- inga personuppgifter utöver det som redan är offentligt i L1
- inga hemligheter eller API-nycklar i repo

---

## 13. Quality gates

Varje ändring av kanonisk data eller kod ska kunna stoppas av:

1. schema-validering (claims / sources / conflicts)
2. locator-check (L1-id eller HTTP-resolvable där tillämpligt)
3. förbud: claim utan source; conflict utan claim-refs
4. diff-review (maintainer)
5. valfritt: agent-checklista som PR-kommentar, inte enväldig merge

---

## 14. Versionering och ändring

| Yta | Regel |
|-----|--------|
| Spec | semver. Breaking score/hierarki/invariants = major |
| Dataset | `as_of` + `run_id` |
| Topic-taxonomi | bakåtkompatibel via alias |
| Formel | `docs/SCORING.md`; byte = major |

**Så här ändras specen**

1. Issue med typ `spec-change` (add / remove / tighten).
2. PR mot den här filen **först** om beteende ändras — implementation följer, inte tvärtom.
3. Invariants i §4 får inte tystas i kod. Vill vi släppa en invariant = major + explicit motivering.
4. Features som inte tjänar actions-vs-words tas bort via samma väg (issue → spec → kod). Ingen zombie-yta.

---

## 15. Non-goals v0

- kommun / region
- sociala medier som L1
- automatisk “sanning” vid acklamation utan betänkande
- realtids-push-garanti
- multiländers parlamentsstöd
- opinionsdata som evidence
- tertiära budget-/poll-sajter som source of truth

---

## 16. Acceptance (v0 klar när)

1. 8 partier × ≥1 topic med både words- och action-försök
2. ≥ N claims med giltig locator (N sätts i PRD; golv 100)
3. minst en automatiskt detekterad conflict per typ i §4.5, eller explicit “inga i fönstret” med query-audit
4. tredje part klonar repo, kör dokumenterad pipeline, får bit-kompatibel eller semantiskt ekvivalent conflict-mängd på freeze-datum
5. publik audit-kedja claim → source utan manuell efterforskning

---

*SPEC v0.1 · OpenSverige · actions vs words*
