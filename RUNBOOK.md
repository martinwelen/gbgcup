# gbgcup — RUNBOOK

Klubb-specifik "följa-turneringen"-app för **Alingsås HK** i **Göteborg Cup** (inomhus, Göteborg).
Byggd 2026-09-04 som en klon av `ahk-beach`-motorn (Åhus Beach-appen), anpassad för inomhuscup.
Live under cupen: helg 1 (4–6 sep) + helg 2 (11–13 sep) 2026.

**Live:** https://martinwelen.github.io/gbgcup/

---

## 1. Vad appen är
EN installerbar PWA som visar alla Alingsås HK:s lag i Göteborg Cup — schema, live-resultat,
tabeller, slutspelsträd, hallar. Alla 12 lag i EN app med **klass- + lagfilter** (inte en app
per ålder som Åhus). Data hämtas från CupManagers `results_api`, byggs till statiska filer och
serveras på GitHub Pages. Auto-uppdateras under cupen.

**Alingsås 12 lag / 7 klasser:**
- Helg 1 (U12–U16): P15, P16 (1 & 2), F13 (Vit & Blå), F16 (1 & 2)
- Helg 2 (junior + U10–U11): HJ (1 & 2), DJ, F11 (Vit & Blå)

---

## 2. Datakälla (CupManager) — verifierade fakta
- **api_host:** `goteborgcup.cupmanager.net` (samma `results_api` som Åhus)
- **tournamentId:** `72459189` (EN turnering, 16 klasser, ~1189 matcher, 30 arenor)
- **clubId (Alingsås HK):** `76496464`
- OBS: `10967287` i `goteborgcup.com`-URL:en är webbplatsens vanity-ID, INTE turnerings-ID:t.
- **Klass** kommer från `division.category → Category.shortName` (P16/F13/HJ/DJ), INTE Åhus
  "(f. 2011)"-format. Lag-slug = `t-<team_id>` (unikt, aldrig kollision Vit/Blå/1/2).
- **Regler** (goteborgcup.com/sv/tavlingsregler): 2×15 min alla UTOM HJ 2×20. Mini-klasser
  P10/F10/P11/F11 = inga resultat/tabeller/slutspel (→ F11 visar bara schema).

---

## 3. Arkitektur / filer
Kloned från `ahk-beach`; `config.py`-konstanter driver allt.

| Fil | Ansvar |
|---|---|
| `config.py` | IDs, host, Pages-path, färger, `VENUE_ABBR` (spelplats-förkortningar) |
| `api.py` | cupmanager-klient (MatchWindow-paging, store) |
| `derive.py` | slug, `parse_category` (klass-token P16/F13/HJ/DJ), färgregel |
| `rules.py` | regelprofil per klass (Mini vs Classic, duration 40/50 min) |
| `fetch_data.py` | klubbdriven matchdata → `data.json`; hallnamn+koordinater, per-klass-duration |
| `fetch_standings.py` | tabeller + slutspel → `standings.json`; bracket `matchNr`+tid+ref |
| `build_apps.py` | bygger EN samlad app (`club_group` + `merge_standings`) → repo-roten |
| `template.py` | hela HTML/CSS/JS-mallen (en fil) |
| `build_all.py` | kör hela kedjan: fetch_data → fetch_standings → build_apps |
| `.github/workflows/update.yml` | schemalagd data-refresh + bygg + commit (backup för CF-worker) |
| `ops/gh-dispatch-worker/` | CF Worker som triggar update.yml (primär trigger) |
| `dashboard/` | privat CF Web Analytics-dashboard (Worker) |

**Byggmål:** appen byggs till **repo-roten** (`index.html`, `manifest.json`, `sw.js`,
`sched.json` + assets). Pages serverar roten. `data.json`/`standings.json` committas.

---

## 4. Funktioner (allt live)
- **Samlad app** — alla 12 lag, filter på klass + lag (chip-rad). Klass = Category.shortName.
- **Schema** — hero ("Härnäst"/"Pågår nu"), matchkort med hall + **Google Maps-länk (exakt
  koordinat)** + ev. video. **Avslutade dagar fälls ihop** till en filter-medveten
  sammanfattningsrad ("X spelade · W vinster"), tryck för att fälla ut.
- **Live-resultat** — pollar `MatchResult` var 10:e s i tidsfönster. Ställningen **hänger kvar**
  genom paus/matchslut: `LIVE h–a` (pulsar) / `Paus h–a` / `Slut h–a`. Vitt på hero (läsbart
  på orange). `POLL_GRACE_MS` 40 min + `sched.json` `no-store` (mot försvinnande resultat).
- **Tabeller** — grupptabeller per klass, Alingsås highlightad, A/B-slutspels-tier-avdelare.
- **Slutspel** — riktigt **tidy-tree** med kopplingslinjer. Feeders löses via `Vinn. <matchNr>`
  ELLER **vinnande lag** (så trädet håller ihop när matcher spelats). Rondordning efter namn
  (1/16→…→final). Varje kort: starttid + `#matchnr` + båda lagnamn + **spelplats (förkortad)**;
  refererade platser = "Vinnare #matchnr". Alingsås-väg i orange. Scroll i båda led.
  Filter "Alla" → "Välj en klass"; Mini-klass utan slutspel → "Inget slutspel".
- **Hallar** — Leaflet/OSM-karta (lazy) med pins per anläggning + lista (adress, matchantal,
  maps-länk). Alltid alla hallar (inget filter-beroende).
- **Exakta hall-koordinater** — via `Arena → Location → MapLocation` (lat/lng + gatuadress),
  alla 30 hallar. `VENUE_ABBR` i config = godkända kortnamn för slutspelsträdet.
- **PWA** — installerbar, offline-cache (SW `gbgcup-v1`, tom LEGACY-lista — delad origin med
  ahk-beach). localStorage-nyckel `gbgcup-filter`.

---

## 5. Drift / auto-uppdatering
**Primär trigger:** CF Worker `gbgcup-dispatch-worker` (cron var 10:e min, fönster
`ACTIVE_FROM/UNTIL` 2026-09-04..09-13) → `workflow_dispatch update.yml`.
- URL: `https://gbgcup-dispatch-worker.martin-220.workers.dev`
- `/` = hälsa/konfig, `/trigger` = tvinga dispatch nu.
- Konfig i `ops/gh-dispatch-worker/wrangler.toml`. Secret: `GITHUB_TOKEN` (fine-grained PAT,
  Actions:RW på gbgcup — satt av Martin, expiry efter cupen).
- Deploy: `cd ops/gh-dispatch-worker && npx wrangler deploy` (CF-auth krävs).

**Backup:** `update.yml` egen cron (`*/30 * * * *` + `*/10 7-22 4-6,11-13 9 *`). GitHubs cron
är opålitlig i tid → därför CF-workern som primär.

**Manuell trigger:** `gh workflow run update.yml -f force=true` (force = bygg om även om datan
är oförändrad, för kod-ändringar).

**Pages:** publikt repo, Pages från `main`/root. Deploy sker på push till main.

**Deploy-flöde (kod-ändring):** editera → `python3 build_apps.py` → `pytest` → commit → push →
Pages bygger på merge. `git pull --rebase --autostash` före push (CI auto-committar data var
~10 min → rebasa alltid). Se [[tournament-ci-race-workflow]].

---

## 6. Statistik (två cookieless lösningar)
Besökslasten syns INTE i GitHub (se §8) — utan i dessa:

**Cloudflare Web Analytics + privat dashboard:**
- Beacon i appen, token `57fb7084887545a1873459ca4f21ce95`.
- GraphQL `site_tag` `04e357fd3199431fa8f1e8fa8e4deffb` (≠ beacon-token — gotcha, hittad via
  `/diag`). Se [[cf-analytics-dashboard]].
- Dashboard-worker `gbgcup-stats.martin-220.workers.dev`, gate via hemlig path:
  `https://gbgcup-stats.martin-220.workers.dev/gbg-aa3970d7fb306978`
- Secrets på workern: `CF_API_TOKEN` (Account Analytics:Read, Martins), `DASH_SECRET`.
  Vars: `CF_ACCOUNT_ID`, `CF_SITE_TAG`. Källa: `dashboard/stats-worker.js`.

**Umami (self-hostad, delad infra):**
- `stats.whatabout.cloud`, website-id `24b3a459-a6d0-459d-8f4e-137170b7e1ee`.
- Admin-token via inloggning; admin-lösen i Azure Key Vault `kv-homelab-9397df` secret
  `umami-admin-password` (kräver `az login`). Website skapad via `POST /api/websites`.
- Tracker i appen: `stats.whatabout.cloud/script.js`.

---

## 7. Test
`python3 -m pytest` → **85 tester** (motor + template-substring-regressioner). CI kör INTE
pytest (bara fetch/build), så tester blockerar inte deploy — kör lokalt före push.
Fixturer: enhetstester mot konstruerade stores (ingen nätverk).

---

## 8. GitHub-hosting-belastning
- **Pages har ingen bandbredds-dashboard.** Mjuk gräns ~100 GB/mån, ~100k req/tim; GitHub
  mejlar vid överskridande. Publikt repo → generös gratisnivå.
- **Sidvikt:** ~400 KB/färsk laddning (`index.html` 164 KB + `sched.json` 101 KB + assets).
  Största löpande posten: `sched.json` (101 KB) hämtas var 60:e s per öppen flik.
  Uppskattning: full matchdag = enstaka GB/mån, långt under gränsen. Ingen risk.
- **Repo-trafik-API** (`gh api repos/martinwelen/gbgcup/traffic/...`): visar github.com-vyer +
  git-clones — clones domineras av egen CI (varje körning klonar), inte besökare.
- **Actions:** publikt repo → Actions-minuter gratis/obegränsade på standard-runners.
- **Riktig besökslast:** CF- och Umami-dashboarden (§6).

---

## 9. Nyckel-gotchas / lärdomar
- **Slutspelsträd + spelade matcher:** "Vinn. <matchNr>"-referensen ersätts av vinnarlagets
  namn när matchen spelats → länken bryts. Därför löses feeders ÄVEN via vinnande lag. Utan det
  blir spelade matcher föräldralösa (skev vy). Verifiera alltid slutspel på en klass med
  SPELADE matcher (t.ex. P16), inte bara en oskriven. Se [[verify-hard-case-before-deploy]].
- **Rondordning** efter rondnamn, INTE starttid (otidssatta slutspel kastar om annars).
- **Live-flaggan** (`live`) är false vid paus OCH kan vara true efter finished → behåll senaste
  ställning tills statisk slutscore finns. Se [[livescore-result-disappearing]].
- **SW-cache/localStorage** delar origin med ahk-beach → unika namn (`gbgcup-v1`, `gbgcup-filter`),
  tom LEGACY-lista (radera aldrig syskonappars cache). Se [[u15-shared-pipeline]].
- **CORS:** in-browser `pollOne` mot `goteborgcup.cupmanager.net` — verifierad ACAO för
  `martinwelen.github.io`.
- **Verifiera live/hårda fallet före deploy** och visa Martin — särskilt efter negativ feedback.

---

## 10. Öppna / möjliga finputs (ej gjorda)
- Feeder-lagens namn i "Vinnare #matchnr"-platser (i st f matchnummer).
- "Hoppa till Alingsås match"-knapp i schema/slutspel.
- Per-klass-duration är inne; ICS-export, ritad hall-karta = ej gjorda.
- Design/spec: `ahk-beach/docs/superpowers/specs/2026-09-04-gbgcup-alingsas-foljaapp-design.md`.
