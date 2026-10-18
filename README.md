# Křovákova Sekera (`krovak-machete`)

Deterministický překladač filmových projektů **Adobe Premiere Pro (`.prproj`)** a **Adobe Audition (`.sesx`)** do nativního formátu **Avid AAF (`.aaf` Edit Protocol)** a **CMX 3600 EDL** pro Avid Media Composer a Avid Pro Tools.

---

> [!TIP]
> **Kompletní a podrobná projektová dokumentace:**  
> Viz [`docs/PROJEKTOVA_DOKUMENTACE.md`](docs/PROJEKTOVA_DOKUMENTACE.md) pro kompletní specifikaci časové matematiky, diagramy architektury, reverzní inženýrství Adobe formátů, Avid AAF standardy, verifikační engine a uživatelská rozhraní.

---

## 1. Záměr projektu
Zajistit 100% snímkově a vzorkově přesný (Frame & Sample Accurate) převod celovečerních filmových projektů bez nutnosti mít nainstalované aplikace Adobe. Architektura je navržena specificky pro autonomní agentní vývoj v **Antigravity IDE** s přísnou izolací kontextu a minimalizací spotřeby tokenů drahých modelů.

---

## 2. Alokace modelů v Antigravity (Token Economy)

| Task | Soubor úkolu | Primární model | Záložní model (Escalation) | Účel a zdůvodnění |
| :--- | :--- | :--- | :--- | :--- |
| **T01** | `T01_ir_and_math.md` | **Claude Opus 5.5** | — | **Kritický základ (1 běh):** Definice `schema.py` a racionální timecode matematiky (`Fraction`). |
| **T02** | `T02_fixture_factory.md` | **Gemini 3.8 Flash** | Gemini 4 Argon | Generátor syntetických `.prproj`, `.sesx` a `.wav` souborů pro testování. |
| **T03** | `T03_prproj_indexer.md` | **Gemini 3.8 Flash** | Gemini 4 Argon | GZIP čteč, indexace `ObjectID`/`ObjectUID` a dereference pointerů v `.prproj`. |
| **T04** | `T04_prproj_timeline.md` | **Gemini 4 Argon** | Claude Sonnet 5.5 | Průchod grafem Premiere sekvencí, rekurzivní flattening vnořených sekvencí, L/J-cuty, markery. |
| **T05** | `T05_sesx_parser.md` | **Gemini 3.8 Flash** | Gemini 4 Argon | Parsování XML z Adobe Audition (`.sesx`) do kanonického `ProjectIR`. |
| **T06** | `T06_aaf_builder_core.md` | **Claude Sonnet 5.5** | Claude Opus 5.5 | Stavba binárního AAF stromu (`CompositionMob`, `MasterMob`, `SourceMob`, `Filler`, `Transition`). |
| **T07** | `T07_aaf_audio_automation.md` | **Claude Sonnet 5.5** | Claude Opus 5.5 | Zápis PCM WAV esence (Embedded/Linked), stereo-to-mono split, `VaryingValue` keyframes. |
| **T08** | `T08_roundtrip_verifier.md` | **Gemini 4 Argon** | Claude Sonnet 5.5 | Kruhový inspektor: zpětné čtení AAF a porovnání s `ProjectIR` + generátor diagnostického reportu. |
| **T09** | `T09_cli_and_gui.md` | **Gemini 3.8 Flash** | Gemini 4 Argon | CLI rozhraní + GUI „Křovákova Sekera“ s animovaným trpasličím progress monitorem + CMX 3600 EDL fallback. |
| **T10** | `T10_packaging_and_installer.md` | **Gemini 3.8 Flash** | Gemini 4 Argon | Standalone balíček bez nutnosti instalace Pythonu: macOS DMG (.app) + Windows EXE + GitHub Actions CI/CD. |

---

## 3. Jak spouštět vývoj v Antigravity (Workflow pro nulové pálení tokenů)
1. Každý task (`T01` až `T10`) spouštěj v **nové, čisté instanci agenta** (vymazaná historie chatu).
2. Do kontextu agentovi přidej **výhradně** `.antigravity/rules.md` a příslušný soubor `.antigravity/tasks/T0X_*.md`.
3. Agent si sám načte pouze soubory vyjmenované v sekci `Allowed Context (Read)`.
4. Pokud agent narazí na 3 po sobě jdoucí selhání `pytest` (Circuit Breaker), zapíše problém do `BLOCKERS.md` a zastaví se. Teprve tehdy přepni instanci na `Escalation Model`.


## Distribuce a Standalone Balíčky (T10)

Křovákova Sekera je plně podporována jako samostatná nativní aplikace bez závislosti na instalaci Pythonu:

### Podporované platformy
- **macOS:** Standalone aplikační balíček `Křovákova Sekera.app` a diskový obraz `KrovakovaSekera.dmg` obsahující zástupce složky `/Applications`.
- **Windows:** Samostatný spustitelný soubor `KrovakovaSekera.exe`.

### Sestavení balíčků
```bash
# Instalace balíčkovacích závislostí
pip install -e ".[packaging]"

# Lokální sestavení (s vyčištěním a vytvořením DMG na macOS)
python scripts/build_dist.py --clean --dmg

# Vyzkoušení sestavení na nečisto (dry-run)
python scripts/build_dist.py --dry-run
```

### Automatizované CI/CD
Při vytvoření a odeslání tagu verze (`v*`) do repozitáře spustí GitHub Actions workflow `.github/workflows/release.yml`, které automaticky sestaví nativní binárky na macOS i Windows a publikuje je do GitHub Release.
