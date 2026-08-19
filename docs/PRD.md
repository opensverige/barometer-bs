# Accountability Radar — PRD v0.1

Produktkrav. Beskriver *varför*, *för vem* och *vad vi släpper*. Beteenderegler står i [SPEC](./SPEC.md).

**Status:** draft · **Gäller:** `opensverige/barometer-bs`  
**Arbetstitel på repo:** barometer-bs  
**Produktnamn:** Accountability Radar (*ord mot handling*)

---

## 1. Problem

Partier säger en sak på webben och i utspel. I motioner, anföranden och voteringar kan det stå något annat — eller ingenting. Det avståndet är svårt att se utan att läsa protokoll.

Befintliga “barometrar” mäter opinion. Det är en annan produkt, redan tagen, och den gör oss till spelare i valet.

Vi bygger inte “vem leder” och inte “hur du ska rösta”. Vi bygger spårbarheten mellan **words** och **actions**.

---

## 2. Mål

1. En medborgare, journalist eller bidragare kan se *vad ett parti sagt* och *vad det gjort* på ett topic, med länk till primärkälla.
2. Konflikter (say≠write, write≠vote, then≠now, tystnad) är förstaklassiga objekt — inte buggar.
3. Samma motor byter topic utan ombyggnad. `ai` är referensimplementation, inte produkten.
4. Tredje part kan klona, köra om och få samma conflict-mängd på ett freeze-datum.

### Anti-mål

- poll-of-polls
- “mest AI-positiv”-ranking
- röst- eller partirekommendation
- valkompass / matchquiz / bullshit-test
- tertiära sajter som source of truth (statsbudget.se, valaggregat, nyhetssajter)

---

## 3. Vem det är till för

| Persona | Jobb | Vad de inte ska få |
|---------|------|---------------------|
| Medborgare | “Stämmer det här utspelet mot protokollet?” | en röstsedel från oss |
| Journalist / researcher | hitta motsägelse + citation på minuter | vår tolkning som facit |
| Bidragare | PR:a en källa, en regel, ett topic | LLM-gatekeeper som envälde |
| Forkare | köra pipelinen själva | hemliga nycklar eller dold score |

---

## 4. Produktprincip

Sanningshierarki är produkt, inte implementationsdetalj.

- **L1** riksdagen vinner
- **L2** regering/myndighet är stark men under L1
- **L3** partiweb/press är words tills L1/L2 backar
- konflikt L3≠L1 **är** ytan vi säljer

Default-vy: conflict, inte leaderboard.

---

## 5. Scope som släpps i lager

Features kommer att läggas till och tas bort. Det här är den avsiktliga ordningen — inte en backlog att bygga i ett svep.

### Nu (v0 — scaffold + första sanning)

Måste finnas innan vi pratar UI-polering:

- schema för Actor, Topic, Source, Claim, Conflict
- L1-adapters: dokument, votering, anförande (riksdagen)
- L3-adapter: whitelistade partisidor för topic `ai`
- conflict-detection enligt SPEC §5 / §9
- audit-kedja claim → source → hash
- quality gates i CI (schema, locator, inga orphan conflicts)
- 8 partier × topic `ai`

N = minst **100** giltiga claims (SPEC §16).

### Härnäst (v0.x — när v0 accepterats)

- fler topics via taxonomi (`energy.nuclear`, migration, nato) utan ny motor
- `docs/SCORING.md` med första formeln
- publik read-only vy (conflict-first)
- ledamot som drill-down på samma modell

### Senare / icebox

- minister/utskott som egna actors
- budget-topic med L1/L2 (prop + beslut) — inte tertiär sajt
- källtest (“stämmer påstående X mot primärkälla?”) utan röstrekommendation
- realtids-notis när en L3-sida divergerar från L1

### Döda om de dyker upp igen

- pollingest
- partiskhetsscore
- “rösta så här”
- social media som L1
- agent-auto-merge

---

## 6. Framgång (levande vs döda metrics)

### Levande

- antal verifierade claims med primärlänk
- antal fångade conflicts, per typ
- tid från källuppdatering → publicerad diff
- externa forks som kör pipelinen
- andel claims med L1-stöd

### Döda (styr inte prioritering)

- pageviews på en snygg graf
- “engagement” på quiz
- hur ofta modellen “har rätt om politiken”

---

## 7. Feature-livscykel

Vi kommer att öka, ta bort och lägga till. Gör det explicit så vi inte slänger två dagars arbete — eller låter zombieytor leva.

```
idé (Discord) → issue (typ nedan) → spec-bump om beteende → PR → CI → maintainer-merge
```

| Issue-typ | När | Vad som måste följa med |
|-----------|-----|-------------------------|
| `feature` | ny yta som tjänar actions-vs-words | acceptance + ev. SPEC-tillägg |
| `spec-change` | hierarki, score, invariants, claim_role | SPEC-PR **före** eller **i samma** PR som kod |
| `remove` | yta som inte tjänar moaten, eller som blivit tertiär SoT | varför, vad som ersätter, dataset-migrering |
| `topic` | nytt topic i taxonomin | definition + aliases + minst en L1-sökväg |

**Regler**

1. Beteende ändras inte i tyst kod. SPEC är först.
2. Implementation följer SPEC, inte tvärtom.
3. En feature utan locator-krav eller audit-kedja släpps inte.
4. Tar vi bort något: issue `remove` + SPEC-rad som stryks + fixtures som uppdateras. Ingen död endpoint “för att vi kanske vill ha tillbaka den”.
5. Major (SPEC §14) krävs för breaking score/hierarki/invariants. Allt annat kan vara minor/patch.
6. Diskussion i Discord är billig. Beslut som ska leva ligger i issue + PR.

---

## 8. Kvalitet och bidrag

- öppen PR-modell under OpenSverige
- CI stoppar ogiltig data (SPEC §13)
- 1–2 maintainers merge (CODEOWNERS när vi är fler än en som faktiskt mergear)
- agent får lämna review-kommentar (saknad `dok_id`, broken URL, stance utan L1)
- agent mergear inte

Licens: OSI, org beslutar (rekommendation Apache-2.0 eller MIT). Dataset separat. Riksdagsdata attribueras Sveriges riksdag.

---

## 9. Risker

| Risk | Motdrag |
|------|---------|
| Vi uppfattas som partiska | aldrig ranking/rekommendation; conflict är observation; L1 vinner |
| Acklamation saknas i voteringsdata | `vote_data: none`, gissa aldrig |
| Ett betänkande = flera punkter | koppla vote per punkt |
| Partiweb släpar / är tom | det är en signal (`action_without_words`), inte ett fel i ingest |
| Agent hallucinerar stance | draft only + schema + adversary + människa |
| Scope-creep till “barometer” | anti-mål i den här filen; `remove`-issue om det slinker in |

---

## 10. Öppna frågor (blockerar inte scaffold)

- exakt OSI-licens
- N utöver golvet 100 — höjer vi efter första freeze?
- första publika ytan: Discord-audit, statisk sajt, eller bara dataset i repo?
- vem som är CODEOWNERS dag 1

---

## 11. Klart att scaffolda när

Den här PR:en är mergad och vi är överens om:

1. SPEC v0.1 är norm
2. PRD v0.1 styr vad som får in / ut
3. nästa PR är schema + repo-skelett (`schema/`, `adapters/`, `data/`, CI-validering) — ingen UI-polish

Scaffold ska kunna överleva att topics och features byts. Hårdkoda inte `ai` i motorn.

---

*PRD v0.1 · OpenSverige · actions vs words*
