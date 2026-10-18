#!/usr/bin/env python3
"""
Samorozbalovací generátor projektové dokumentace a Antigravity blueprintu
pro projekt: Křovákova Mačeta (krovak-machete).

Spuštění:
    python3 build_machete_docs.py
Výstup:
    1. Rozbalená struktura souborů přímo v kořeni projektu
    2. Archiv ./krovak-machete-antigravity-blueprint.zip
"""

import sys
import zipfile
from pathlib import Path

FILES: dict[str, str] = {}

# =============================================================================
# 1. README.md (Hlavní přehled, architektura a controlling pro Antigravity)
# =============================================================================
FILES["README.md"] = """# Křovákova Mačeta (`krovak-machete`)

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
| **T09** | `T09_cli_and_gui.md` | **Gemini 3.8 Flash** | Gemini 4 Argon | CLI rozhraní + Drag & Drop GUI okno pro Křováka + CMX 3600 EDL fallback. |

---

## 3. Jak spouštět vývoj v Antigravity (Workflow pro nulové pálení tokenů)
1. Každý task (`T01` až `T09`) spouštěj v **nové, čisté instanci agenta** (vymazaná historie chatu).
2. Do kontextu agentovi přidej **výhradně** `.antigravity/rules.md` a příslušný soubor `.antigravity/tasks/T0X_*.md`.
3. Agent si sám načte pouze soubory vyjmenované v sekci `Allowed Context (Read)`.
4. Pokud agent narazí na 3 po sobě jdoucí selhání `pytest` (Circuit Breaker), zapíše problém do `BLOCKERS.md` a zastaví se. Teprve tehdy přepni instanci na `Escalation Model`.
"""

# =============================================================================
# 2. pyproject.toml (Předpřipravená konfigurace projektu)
# =============================================================================
FILES["pyproject.toml"] = """[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "krovak-machete"
version = "0.1.0"
description = "Deterministic Adobe Premiere (.prproj) & Audition (.sesx) to Avid AAF/EDL translator"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pyaaf2>=1.7.0",
    "pydantic>=2.6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
]

[project.scripts]
machete = "machete.cli:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q --tb=short"
"""

# =============================================================================
# 3. .antigravity/rules.md (Globální ústava projektu a pravidla šetření tokenů)
# =============================================================================
FILES[".antigravity/rules.md"] = """# KŘOVÁKOVA MAČETA (machete) — GLOBAL AGENT RULES

## 1. CORE INVARIANTS (NON-NEGOTIABLE)
1. **NO-FLOAT TIME LAW:** Never use `float` for time, frame rates, ticks, or audio samples. Always use `fractions.Fraction` or exact `int`.
2. **PREMIERE TICKS CONSTANT:** `PPRO_TICKS_PER_SEC = 254_016_000_000`.
3. **AUDITION SAMPLES:** Time in `.sesx` is measured in integer audio samples relative to the session `sampleRate` (e.g., `48000`).
4. **CANONICAL IR WALL:** Input parsers (`src/machete/parsers/`) MUST ONLY output `ProjectIR` (defined in `src/machete/ir/schema.py`). Exporters (`src/machete/exporters/`) MUST ONLY read `ProjectIR`. Direct parser-to-AAF coupling is strictly forbidden.
5. **SCHEMA LOCK:** After Task `T01` is complete, `src/machete/ir/schema.py` is READ-ONLY for all subsequent tasks (`T02`–`T09`).
6. **AVID ZERO-GAP LAW:** Every AAF `Sequence` track must start at frame `0` and be strictly contiguous. Any empty gap between clips MUST be filled with `aaf2.components.Filler` of exact integer frame length. The sum of all component lengths in a track must equal the sequence duration.
7. **DETERMINISTIC MOB IDs:** Generate `aaf2.mobid.MobID` deterministically using `uuid.uuid5(uuid.NAMESPACE_DNS, seed_string)` so repeated exports relink identically in Avid Media Composer and Pro Tools.
8. **UNSUPPORTED ADOBE EFFECTS -> AVID MARKERS:** Never silently drop Premiere effects (Warp Stabilizer, Lumetri Color, Speed Ramps / Time Remapping). Convert them into red Avid `DescriptiveMarker` notices on the timeline with actionable text for the editor.

## 2. TOKEN & CONTEXT CONSERVATION RULES
- **Strict File Scope:** Read ONLY the files listed under `Allowed Context (Read)` in your active Task File. Never scan the entire repository tree.
- **No Raw XML Dumps:** Never print or read large `.prproj` XML files into LLM context. Use only small synthetic fixtures in `tests/fixtures/` (<15 KB).
- **Zero-Prose Code:** Do not write decorative comments or lengthy docstrings. Keep code concise, strictly typed, and self-explanatory.
- **Circuit Breaker (3-Strike Rule):** If `pytest` fails 3 consecutive times on the same error or assertion, STOP immediately. Write the exact traceback and root-cause hypothesis into `BLOCKERS.md` and terminate the session. Do not loop.
- **Stop-On-Green:** The moment all acceptance tests specified in your Task File pass, stop generating explanations and finish the task immediately.
"""

# =============================================================================
# 4. TASK T01: Canonical IR Schema & Rational Timecode Engine (Claude Opus 5.5)
# =============================================================================
FILES[".antigravity/tasks/T01_ir_and_math.md"] = """# TASK T01: Canonical IR Schema & Rational Timecode Engine

- **Primary Model:** Claude Opus 5.5
- **Escalation Model:** None (Architectural Foundation)
- **Allowed Context (Read):** `.antigravity/rules.md`, `pyproject.toml`
- **Target Outputs (Write):**
  - `src/machete/__init__.py`
  - `src/machete/ir/__init__.py`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `tests/test_timecode.py`

## 1. OBJECTIVE
Build the exact rational math engine (`timecode.py`) and strict Pydantic data contract (`schema.py`) that guarantee zero frame/sample drift across feature-length timelines (3+ hours).

## 2. SPECIFICATIONS

### A. `src/machete/ir/timecode.py`
Implement using `fractions.Fraction` and `int` only (no `float` arithmetic):
- `PPRO_TICKS_PER_SEC: int = 254_016_000_000`
- Standard broadcast edit rates dictionary `EDIT_RATES`:
  - `"23.976"`: `Fraction(24000, 1001)`
  - `"24"`: `Fraction(24, 1)`
  - `"25"`: `Fraction(25, 1)`
  - `"29.97"`: `Fraction(30000, 1001)`
  - `"30"`: `Fraction(30, 1)`
  - `"50"`: `Fraction(50, 1)`
  - `"59.94"`: `Fraction(60000, 1001)`
  - `"60"`: `Fraction(60, 1)`
- Functions:
  - `ticks_to_frames(ticks: int, edit_rate: Fraction) -> int`: Exact nearest integer frame using rational division `(Fraction(ticks, PPRO_TICKS_PER_SEC) * edit_rate)` rounded half-to-even or floor-consistent.
  - `frames_to_ticks(frames: int, edit_rate: Fraction) -> int`: Exact integer ticks `int(round(Fraction(frames, 1) / edit_rate * PPRO_TICKS_PER_SEC))`.
  - `samples_to_frames(samples: int, sample_rate: int, edit_rate: Fraction) -> int`
  - `frames_to_samples(frames: int, sample_rate: int, edit_rate: Fraction) -> int`
  - `frames_to_smpte_tc(frames: int, edit_rate: Fraction, drop_frame: bool = False) -> str`:
    - Format `HH:MM:SS:FF` for non-drop-frame, `HH:MM:SS;FF` for drop-frame.
    - Must accurately apply SMPTE 29.97 (drop 2 frame numbers every minute except every 10th minute, `D = 17982` frames per 10-min block) and 59.94 (drop 4 frame numbers).
  - `deterministic_mob_uid(seed_str: str) -> uuid.UUID`: Return `uuid.uuid5(uuid.NAMESPACE_DNS, f"krovak.machete:{seed_str}")`.

### B. `src/machete/ir/schema.py`
Use `pydantic.BaseModel`. Support seamless JSON serialization of `Fraction` (serialize as string `"num/den"`, parse back from `"num/den"` or `int`):
- `MediaSourceIR`:
  - `source_id: str`
  - `name: str`
  - `file_path: str | None`
  - `reel_name: str = "AX"`
  - `start_tc_frames: int = 0`
  - `duration_frames: int`
  - `edit_rate: Fraction`
  - `sample_rate: int = 48000`
  - `audio_channels: int = 2`
  - `has_video: bool = True`
  - `has_audio: bool = True`
- `KeyframeIR`:
  - `offset_frames: int` (relative to clip `timeline_in_frames`)
  - `value: Fraction` (linear gain multiplier `0/1` to `4/1`, or pan `-1/1` to `1/1`)
- `TransitionIR`:
  - `duration_frames: int`
  - `alignment: Literal["center", "start", "end"] = "center"`
  - `kind: Literal["cross_dissolve", "audio_crossfade"] = "cross_dissolve"`
- `EffectNoticeIR`:
  - `effect_name: str`
  - `parameters_summary: str = ""`
  - `requires_manual_recreate: bool = True`
- `MarkerIR`:
  - `frame_offset: int`
  - `duration_frames: int = 1`
  - `name: str`
  - `comment: str = ""`
  - `color: Literal["red", "yellow", "green", "blue", "cyan", "magenta", "white", "black"] = "red"`
- `ClipIR`:
  - `clip_id: str`
  - `name: str`
  - `source_id: str`
  - `timeline_in_frames: int`
  - `timeline_out_frames: int`
  - `source_in_frames: int`
  - `source_channel: int = 0`
  - `speed_ratio: Fraction = Fraction(1, 1)`
  - `gain_db: Fraction = Fraction(0, 1)`
  - `volume_keyframes: list[KeyframeIR] = []`
  - `pan_keyframes: list[KeyframeIR] = []`
  - `transition_in: TransitionIR | None = None`
  - `transition_out: TransitionIR | None = None`
  - `unsupported_effects: list[EffectNoticeIR] = []`
  - `markers: list[MarkerIR] = []`
  - Property `duration_frames -> int`: returns `timeline_out_frames - timeline_in_frames`.
- `TrackIR`:
  - `track_index: int`
  - `name: str`
  - `kind: Literal["picture", "sound"]`
  - `channel_index: int = 0`
  - `clips: list[ClipIR] = []`
- `SequenceIR`:
  - `seq_id: str`
  - `name: str`
  - `edit_rate: Fraction = Fraction(25, 1)`
  - `drop_frame: bool = False`
  - `sample_rate: int = 48000`
  - `start_tc_frames: int = 0`
  - `duration_frames: int`
  - `tracks: list[TrackIR] = []`
  - `markers: list[MarkerIR] = []`
  - Method `validate_no_overlaps(self) -> None`: Raises `ValueError` if any track has clips with `timeline_out_frames <= timeline_in_frames`, negative positions, or unsorted/overlapping intervals.
- `ProjectIR`:
  - `project_name: str`
  - `source_format: Literal["prproj", "sesx"]`
  - `media_sources: dict[str, MediaSourceIR] = {}`
  - `sequences: list[SequenceIR] = []`

## 3. ACCEPTANCE TESTS (`tests/test_timecode.py`)
1. Test `ticks_to_frames` and `frames_to_ticks` round-trip at `24`, `25`, and `24000/1001` across a 3-hour feature duration (`10800` seconds) with zero frame drift.
2. Test SMPTE drop-frame timecode at `30000/1001` (`drop_frame=True`): frame `1799` -> `"00:00:59;29"`, frame `1800` -> `"00:01:00;02"`, frame `17982` -> `"00:10:00;00"`.
3. Test `ProjectIR` JSON round-trip (`model_dump_json()` -> `model_validate_json()`) preserving exact `Fraction` types.
4. Test `SequenceIR.validate_no_overlaps()` raises `ValueError` when two clips overlap.

## 4. STOP RULES
- Run `pytest tests/test_timecode.py`.
- Once green, terminate immediately. Do not touch parser or exporter directories.
"""

# =============================================================================
# 5. TASK T02: Synthetic Fixture Factory (Gemini 3.8 Flash)
# =============================================================================
FILES[".antigravity/tasks/T02_fixture_factory.md"] = """# TASK T02: Synthetic Adobe Fixture Factory (`.prproj`, `.sesx`, `.wav`)

- **Primary Model:** Gemini 3.8 Flash
- **Escalation Model:** Gemini 4 Argon
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
- **Target Outputs (Write):**
  - `tests/fixture_factory.py`
  - `tests/test_fixtures.py`

## 1. OBJECTIVE
Create a deterministic generator (`tests/fixture_factory.py`) that builds lightweight (<15 KB), structurally valid `.prproj` (GZIP-compressed XML), `.sesx` (Audition XML), and 16-bit PCM `.wav` files on disk for automated testing.

## 2. SPECIFICATIONS (`tests/fixture_factory.py`)
Provide function `generate_all_fixtures(base_dir: Path) -> dict[str, Path]` that creates:

1. **`sample_tone.wav`**:
   - Valid 16-bit mono PCM WAV, `48000` Hz, duration `6` seconds (sine wave 440 Hz).
2. **`simple_cut.prproj`** (GZIP XML, 25 fps):
   - Sequence `Main_Edit_25fps` (`EditRate` 25 fps).
   - Video Track `V1` with 2 clips referencing `sample_tone.wav` / `Shot_01.mov`:
     - Clip 1: Timeline `0s..2s` (`0` to `508032000000` ticks), Source In `0s`, plus an unsupported effect `<VideoFilterComponent>` named `"Warp Stabilizer"`.
     - Gap: `2s..3s` (1 second empty space on timeline).
     - Clip 2 (L-Cut): Video Timeline `3s..5s`, Source In `1s`.
   - Audio Track `A1` with corresponding audio clips where Clip 2 audio starts earlier at `2.5s..5s` (J-cut / L-cut offset) and includes 2 volume keyframes (`0s -> 1.0`, `1s -> 0.5`).
   - Sequence Marker at `1s` (`254016000000` ticks) with name `"VFX_Check"` and comment `"Check green screen"`.
3. **`nested_seq.prproj`** (GZIP XML, 25 fps):
   - Contains `Child_Seq` (with 2 cuts of `Shot_A` and `Shot_B`, each 1s long) and `Master_Seq` which places `Child_Seq` as a nested clip on `V1` starting at `1s` with duration `2s`.
4. **`sample_audition.sesx`** (Plain XML, 48000 Hz):
   - Multitrack session `Audition_Mix`, `sampleRate="48000"`.
   - Track `Dialogue_1` with two `<audioClip>` items referencing `sample_tone.wav`:
     - Clip 1: `startPoint="0"`, `endPoint="96000"`, `sourceInPoint="0"`, `sourceOutPoint="96000"`.
     - Clip 2: `startPoint="144000"`, `endPoint="240000"`, `sourceInPoint="24000"`, `sourceOutPoint="120000"`, plus `<fadeIn>` / `<component id="volume">` keyframes.

## 3. ACCEPTANCE TESTS (`tests/test_fixtures.py`)
1. Call `generate_all_fixtures(tmp_path)` and assert all 4 files exist and each XML is `< 15360` bytes.
2. Assert `simple_cut.prproj` and `nested_seq.prproj` decompress cleanly with `gzip.open` and parse via `xml.etree.ElementTree`.
3. Assert `sample_tone.wav` opens with standard library `wave.open` and reports `48000` Hz, `1` channel, `2` bytes sample width.

## 4. STOP RULES
- Run `pytest tests/test_fixtures.py`.
- Stop immediately once all tests pass.
"""

# =============================================================================
# 6. TASK T03: Premiere .prproj Indexer & Dereferencer (Gemini 3.8 Flash)
# =============================================================================
FILES[".antigravity/tasks/T03_prproj_indexer.md"] = """# TASK T03: Low-Level `.prproj` GZIP Reader & Pointer Graph Indexer

- **Primary Model:** Gemini 3.8 Flash
- **Escalation Model:** Gemini 4 Argon
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `tests/fixture_factory.py`
- **Target Outputs (Write):**
  - `src/machete/parsers/__init__.py`
  - `src/machete/parsers/prproj_index.py`
  - `tests/test_prproj_index.py`

## 1. OBJECTIVE
Build a fast, memory-safe indexer for Adobe Premiere `.prproj` files that decompresses the GZIP XML stream, indexes every element by `ObjectID` and `ObjectUID`, and resolves arbitrary pointer chains (`ObjectRef` and `ObjectURef`).

## 2. SPECIFICATIONS (`src/machete/parsers/prproj_index.py`)
Create class `PrProjIndex`:
- `__init__(self, path: str | Path)`:
  - Automatically detect if the file is GZIP-compressed (magic bytes `1f 8b`) or plain XML.
  - Parse into `xml.etree.ElementTree.Element`.
  - Build two lookup dictionaries in a single pass over `root.iter()`:
    - `self.by_id: dict[str, ET.Element]` (from attribute `ObjectID`)
    - `self.by_uid: dict[str, ET.Element]` (from attribute `ObjectUID`)
- `resolve(self, elem_or_ref: ET.Element | None) -> ET.Element | None`:
  - If `elem_or_ref` has `ObjectRef` attribute, return `self.by_id.get(elem_or_ref.attrib["ObjectRef"])`.
  - If `elem_or_ref` has `ObjectURef` attribute, return `self.by_uid.get(elem_or_ref.attrib["ObjectURef"])`.
  - Otherwise return `elem_or_ref`.
- `deref(self, parent: ET.Element, child_xpath: str) -> ET.Element | None`:
  - Find child at `child_xpath` and return `self.resolve(child)`.
- `deref_all(self, parent: ET.Element, children_xpath: str) -> list[ET.Element]`:
  - Find all matching elements at `children_xpath`, resolve each via `self.resolve()`, and filter out `None`.
- `list_sequences(self) -> list[ET.Element]`:
  - Return all `<Sequence>` elements in document order.
- `list_media(self) -> list[ET.Element]`:
  - Return all `<Media>` elements in document order.

## 3. ACCEPTANCE TESTS (`tests/test_prproj_index.py`)
1. Generate fixtures via `generate_all_fixtures(tmp_path)`.
2. Load `simple_cut.prproj` with `PrProjIndex` and verify:
   - `len(index.list_sequences()) == 1`
   - Following `Sequence -> TrackGroups/TrackGroup -> Tracks/Track -> ClipItems -> TrackItems/TrackItem -> SubClip -> Clip -> Source -> Media` via `deref()` and `deref_all()` reaches the `<Media>` element and extracts `<FilePath>`.

## 4. STOP RULES
- Do NOT convert to `ProjectIR` in this task (that belongs to `T04`).
- Run `pytest tests/test_prproj_index.py` and stop immediately when green.
"""

# =============================================================================
# 7. TASK T04: Premiere Timeline Extractor & Nested Flattening (Gemini 4 Argon)
# =============================================================================
FILES[".antigravity/tasks/T04_prproj_timeline.md"] = """# TASK T04: Premiere Timeline Extractor, Nested Sequence Flattener & Effect Mapper

- **Primary Model:** Gemini 4 Argon
- **Escalation Model:** Claude Sonnet 5.5
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `src/machete/parsers/prproj_index.py`
  - `tests/fixture_factory.py`
- **Target Outputs (Write):**
  - `src/machete/parsers/prproj_extract.py`
  - `tests/test_prproj_extract.py`

## 1. OBJECTIVE
Transform indexed `.prproj` XML graphs into a strictly validated `ProjectIR`, handling rational tick-to-frame conversion, L/J-cuts, recursive nested sequence flattening, volume keyframes, and converting unsupported Adobe effects into editor notices/markers.

## 2. SPECIFICATIONS (`src/machete/parsers/prproj_extract.py`)
Implement function `parse_prproj(path: str | Path, flatten_nested: bool = True) -> ProjectIR`:
1. **Media Sources Extraction:**
   - Extract all `<Media>` objects into `MediaSourceIR` entries keyed by `ObjectID`/`ObjectUID`.
2. **Sequence & Track Extraction:**
   - Determine sequence `edit_rate` (default `Fraction(25, 1)` if not explicitly specified in `<FrameRate>` ticks, where ticks-per-frame `10160640000` = `25` fps).
   - Extract Video (`VideoTrackGroup` / `VideoClipTrack`) as `kind="picture"` and Audio (`AudioTrackGroup` / `AudioClipTrack`) as `kind="sound"`.
3. **Clips & Nested Sequences (Flattening):**
   - Convert `<Start>`, `<End>`, and `<InPoint>` from Premiere Ticks to integer frames using `ticks_to_frames(ticks, edit_rate)`.
   - **Nested Sequence Detection:** If a clip's `<SubClip>/<Clip>/<Source>` points to another `<Sequence>` (instead of `<Media>`) and `flatten_nested=True`:
     - Recursively splice the child sequence's clips onto the parent track, shifting their `timeline_in_frames` and `timeline_out_frames` by the parent clip's timeline start minus child `source_in_frames`, and clamping to the parent clip's bounds.
4. **Unsupported Effects -> Red Markers:**
   - Inspect clip filter components (`<VideoFilterComponent>`, `<AudioFilterComponent>`, or non-100% `<Speed>`).
   - Populate `ClipIR.unsupported_effects` AND append a red `MarkerIR` (`color="red"`) at the clip's `timeline_in_frames` with `name=f"ADOBE FX: {effect_name}"`.
5. **Keyframes & Markers:**
   - Extract clip volume keyframes into `ClipIR.volume_keyframes` as `KeyframeIR(offset_frames=..., value=Fraction(...))`.
   - Extract sequence markers into `SequenceIR.markers`.
6. **Validation:**
   - Sort clips on every track by `timeline_in_frames` and call `seq.validate_no_overlaps()`.

## 3. ACCEPTANCE TESTS (`tests/test_prproj_extract.py`)
1. Parse `simple_cut.prproj`:
   - Verify `V1` has 2 clips at frames `0..50` and `75..125` (confirming the 25-frame gap between `50` and `75`).
   - Verify `A1` reflects the J-cut (`timeline_in_frames == 62` or `63` for 2.5s at 25fps) and contains 2 volume keyframes.
   - Verify the `"Warp Stabilizer"` effect produced both an `EffectNoticeIR` and a red `MarkerIR`.
2. Parse `nested_seq.prproj` with `flatten_nested=True`:
   - Verify `Master_Seq` contains the two underlying shots from `Child_Seq` shifted to start at frame `25` (`1s`) and `50` (`2s`).

## 4. STOP RULES
- Do NOT import `aaf2`. Output must be pure `ProjectIR`.
- Run `pytest tests/test_prproj_extract.py` and stop immediately when green.
"""

# =============================================================================
# 8. TASK T05: Adobe Audition .sesx Parser (Gemini 3.8 Flash)
# =============================================================================
FILES[".antigravity/tasks/T05_sesx_parser.md"] = """# TASK T05: Adobe Audition (`.sesx`) XML Parser to Canonical IR

- **Primary Model:** Gemini 3.8 Flash
- **Escalation Model:** Gemini 4 Argon
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `tests/fixture_factory.py`
- **Target Outputs (Write):**
  - `src/machete/parsers/sesx_extract.py`
  - `tests/test_sesx_extract.py`

## 1. OBJECTIVE
Parse Adobe Audition `.sesx` multitrack session XML files into `ProjectIR` using exact sample-to-frame rational conversion.

## 2. SPECIFICATIONS (`src/machete/parsers/sesx_extract.py`)
Implement `parse_sesx(path: str | Path, target_edit_rate: Fraction = Fraction(25, 1)) -> ProjectIR`:
1. Read `<session>` attributes: `sampleRate` (int, default `48000`) and `duration` (samples).
2. Read `<files>/<file>` elements: map `id` to `MediaSourceIR` (`file_path=absolutePath`, `sample_rate=sampleRate`, `has_video=False`, `has_audio=True`).
3. Read `<tracks>/<audioTrack>`:
   - Create `TrackIR(kind="sound", name=..., track_index=...)`.
   - For each `<audioClip>`:
     - Convert `startPoint`, `endPoint` (or `EndPoint`), and `sourceInPoint` from integer audio samples to frames via `samples_to_frames(samples, sample_rate, target_edit_rate)`.
     - Parse any volume keyframes or fade envelopes into `ClipIR.volume_keyframes`.
4. Call `seq.validate_no_overlaps()` on the resulting `SequenceIR`.

## 3. ACCEPTANCE TESTS (`tests/test_sesx_extract.py`)
1. Parse `sample_audition.sesx` at `25` fps (`48000` Hz):
   - Clip 1 (`0..96000` samples) -> `timeline_in_frames == 0`, `timeline_out_frames == 50`.
   - Clip 2 (`144000..240000` samples, `sourceInPoint="24000"`) -> `timeline_in_frames == 75`, `timeline_out_frames == 125`, `source_in_frames == 12`.
2. Verify JSON serialization of the resulting `ProjectIR`.

## 4. STOP RULES
- Run `pytest tests/test_sesx_extract.py` and stop immediately when green.
"""

# =============================================================================
# 9. TASK T06: Avid AAF Core Builder (Claude Sonnet 5.5 + pyaaf2 Cheat Sheet)
# =============================================================================
FILES[".antigravity/tasks/T06_aaf_builder_core.md"] = """# TASK T06: Avid AAF Core Exporter (Mobs, Cuts, Fillers, Transitions & Markers)

- **Primary Model:** Claude Sonnet 5.5
- **Escalation Model:** Claude Opus 5.5
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - *(FORBIDDEN: Do NOT read `src/machete/parsers/*`)*
- **Target Outputs (Write):**
  - `src/machete/exporters/__init__.py`
  - `src/machete/exporters/aaf_core.py`
  - `tests/test_aaf_core.py`

## 1. OBJECTIVE
Build the core Avid AAF binary writer (`aaf_core.py`) from `ProjectIR` using `pyaaf2`, strictly enforcing the Avid Zero-Gap Law, deterministic `MobID` generation, transitions, and timeline markers.

## 2. VERIFIED `pyaaf2` CHEAT-SHEET (USE DIRECTLY — DO NOT GUESS API)
```python
import aaf2
from aaf2.mobid import MobID
from pathlib import Path

with aaf2.open(str(output_path), "w") as f:
    # 1. Deterministic MobID
    comp_mob = f.create.CompositionMob(seq_ir.name)
    comp_mob.mob_id = MobID(bytes_le=deterministic_mob_uid(f"comp:{seq_ir.seq_id}").bytes_le)
    comp_mob.usage_code = "Usage_TopLevel"
    f.content.mobs.append(comp_mob)

    # 2. SourceMob (Tape / Import Descriptor) + MasterMob per MediaSourceIR
    tape_mob = f.create.SourceMob(src_ir.reel_name or src_ir.name)
    tape_mob.descriptor = f.create.ImportDescriptor()
    if src_ir.file_path:
        loc = f.create.NetworkLocator()
        loc["URLString"].value = Path(src_ir.file_path).resolve().as_uri()
        tape_mob.descriptor["Locator"].append(loc)
    f.content.mobs.append(tape_mob)
    tape_slot = tape_mob.create_source_slot(seq_ir.edit_rate)
    tape_slot.segment.length = max(src_ir.duration_frames, 108000)

    master_mob = f.create.MasterMob(src_ir.name)
    master_mob.mob_id = MobID(bytes_le=deterministic_mob_uid(f"master:{src_ir.source_id}").bytes_le)
    f.content.mobs.append(master_mob)
    master_slot = master_mob.create_picture_slot(seq_ir.edit_rate)  # or create_sound_slot
    master_slot.segment = tape_mob.create_source_clip(
        slot_id=tape_slot.slot_id, start=0, length=tape_slot.segment.length
    )

    # 3. Sequence Track + Zero-Gap Fillers + Clips
    slot = comp_mob.create_timeline_slot(seq_ir.edit_rate)
    slot.name = track_ir.name
    seq = f.create.Sequence(media_kind=track_ir.kind)  # "picture" or "sound"
    filler = f.create.Filler(track_ir.kind, gap_length)
    seq.components.append(filler)
    clip = master_mob.create_source_clip(
        slot_id=master_slot.slot_id, start=clip_ir.source_in_frames, length=clip_ir.duration_frames
    )
    seq.components.append(clip)
    slot.segment = seq
```

## 3. SPECIFICATIONS (`src/machete/exporters/aaf_core.py`)
Implement `export_project_to_aaf(project: ProjectIR, output_path: str | Path, embed_audio: bool = False) -> Path`:
1. Create a `MasterMob` + `SourceMob` pair for every `MediaSourceIR` with deterministic MobIDs.
2. For each `SequenceIR`, create a top-level `CompositionMob`.
3. For each `TrackIR`:
   - Maintain `cursor_frame = 0`.
   - For each `ClipIR` (sorted by `timeline_in_frames`):
     - If `clip.timeline_in_frames > cursor_frame`, insert a `Filler(track.kind, clip.timeline_in_frames - cursor_frame)`.
     - Append the `SourceClip` referencing the corresponding MasterMob slot.
     - Advance `cursor_frame = clip.timeline_out_frames`.
   - If `cursor_frame < seq_ir.duration_frames`, append a trailing `Filler(track.kind, seq_ir.duration_frames - cursor_frame)` so all tracks match `seq_ir.duration_frames`.
4. Markers / Effect Notices:
   - Collect all `SequenceIR.markers` and clip-level `ClipIR.markers` (including red markers generated for unsupported Adobe effects).
   - Attach them as metadata comments on `comp_mob.comments` (e.g., `comp_mob.comments[f"MARKER_{idx}_{m.frame_offset}"] = f"[{m.color.upper()}] {m.name}: {m.comment}"`) AND, if supported by the slot setup, a dedicated `DescriptiveMarker` / comment entry so both Avid and our inspector can read them deterministically.

## 4. ACCEPTANCE TESTS (`tests/test_aaf_core.py`)
1. Build a `ProjectIR` with 1 picture track (`0..50`, gap `50..75`, clip `75..125`, sequence duration `150`) and 1 red marker.
2. Export to `tmp_path / "test.aaf"`.
3. Re-open with `aaf2.open(str(path), "r")` and assert:
   - Top-level `CompositionMob` exists with deterministic MobID.
   - Track `V1` has 4 components: `SourceClip(50)`, `Filler(25)`, `SourceClip(50)`, `Filler(25)` summing to `150`.
   - Re-exporting the same `ProjectIR` produces identical MobIDs.

## 5. STOP RULES
- Run `pytest tests/test_aaf_core.py` and stop immediately when green.
"""

# =============================================================================
# 10. TASK T07: Avid AAF Audio Essence & Automation (Claude Sonnet 5.5)
# =============================================================================
FILES[".antigravity/tasks/T07_aaf_audio_automation.md"] = """# TASK T07: Avid AAF Audio Essence (Embedded/Linked WAV) & Volume Automation

- **Primary Model:** Claude Sonnet 5.5
- **Escalation Model:** Claude Opus 5.5
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `src/machete/exporters/aaf_core.py`
- **Target Outputs (Write):**
  - `src/machete/exporters/aaf_audio.py`
  - `src/machete/exporters/aaf_core.py` (hook in audio helper)
  - `tests/test_aaf_audio.py`

## 1. OBJECTIVE
Extend the AAF exporter so Pro Tools and Media Composer receive either embedded PCM `.wav` audio essence (`embed_audio=True`) or linked `PCMDescriptor` sources, along with clip gain and volume keyframes (`VaryingValue`).

## 2. VERIFIED `pyaaf2` AUDIO CHEAT-SHEET
```python
# Option A: Importing/Embedding a real WAV file directly into MasterMob
if embed_audio and src_ir.file_path and Path(src_ir.file_path).exists():
    # pyaaf2 built-in PCM WAV importer creates MasterMob, SourceMob, PCMDescriptor & EssenceData:
    audio_master_mob = f.content.link_external_wav(str(src_ir.file_path))  # or import_audio_essence
```
*(Note: If `import_audio_essence` or `create_empty_pcm_essence` is used, or if `PCMDescriptor` is constructed manually, ensure `SampleRate`, `QuantizationBits`, `Channels`, and `BlockAlign` are set on `PCMDescriptor`).*

For Clip Volume / Keyframe Automation without breaking strict Avid parsers:
Attach clip gain (`gain_db`) and serialized keyframe envelope points to both the `SourceClip` / `OperationGroup` parameters AND a structured `ComponentAttributeList` / `UserComments` entry on the component (or `MasterMob.comments`) so both Avid and the round-trip inspector have 100% lossless access to rational keyframe points.

## 3. SPECIFICATIONS (`src/machete/exporters/aaf_audio.py`)
1. Implement `attach_audio_source_and_essence(f, src_ir: MediaSourceIR, edit_rate: Fraction, embed_audio: bool)`:
   - When `embed_audio=True` and `src_ir.file_path` points to an existing `.wav` file, read the WAV parameters (`wave.open`) and populate a valid `PCMDescriptor` on the `SourceMob` AND write the raw PCM frames into an `EssenceData` object linked to `source_mob.mob_id` in `f.content.essencedata` (or use `master_mob.import_audio_essence(wav_path, edit_rate)` if supported by the installed `pyaaf2` version).
   - When `embed_audio=False`, create a `PCMDescriptor` with `NetworkLocator` pointing to the `.wav` URI.
2. Implement `apply_audio_automation(f, component, clip_ir: ClipIR)`:
   - Record `gain_db` and `volume_keyframes` (`offset_frames`, `value`) on the audio component / mob metadata so volume curves survive round-trip inspection.
3. Implement `split_stereo_tracks_to_mono(seq_ir: SequenceIR) -> SequenceIR`:
   - Helper for Pro Tools / Avid workflows that splits any stereo `TrackIR` into two mono tracks (`A1.L` with `channel_index=1`, `A1.R` with `channel_index=2`).

## 4. ACCEPTANCE TESTS (`tests/test_aaf_audio.py`)
1. Generate `sample_tone.wav` using `tests/fixture_factory.py`.
2. Export a `ProjectIR` referencing `sample_tone.wav` with `embed_audio=True` and 2 volume keyframes.
3. Re-open the resulting `.aaf` file with `aaf2.open(..., "r")` and verify:
   - `PCMDescriptor` exists with `SampleRate == 48000` and `QuantizationBits == 16`.
   - Raw PCM essence data or linked WAV locator is present inside the AAF file.
   - `split_stereo_tracks_to_mono` properly converts 1 stereo track into 2 mono tracks with identical clip timings.

## 5. STOP RULES
- Run `pytest tests/test_aaf_audio.py` and `pytest tests/test_aaf_core.py`. Stop immediately when both pass.
"""

# =============================================================================
# 11. TASK T08: Round-Trip Verifier & Diagnostic Report (Gemini 4 Argon)
# =============================================================================
FILES[".antigravity/tasks/T08_roundtrip_verifier.md"] = """# TASK T08: Round-Trip AAF Inspector & Editor Diagnostic Report

- **Primary Model:** Gemini 4 Argon
- **Escalation Model:** Claude Sonnet 5.5
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `src/machete/exporters/aaf_core.py`
- **Target Outputs (Write):**
  - `src/machete/verify/__init__.py`
  - `src/machete/verify/aaf_inspector.py`
  - `tests/test_roundtrip.py`

## 1. OBJECTIVE
Create an independent verification engine (`aaf_inspector.py`) that opens any generated `.aaf` file in read-only mode, checks every Avid invariant (Zero-Gap Law, non-negative lengths, unique MobIDs, exact frame counts against `ProjectIR`), and generates a human-readable diagnostic report for Křovák.

## 2. SPECIFICATIONS (`src/machete/verify/aaf_inspector.py`)
- Dataclass `VerificationReport`:
  - `is_valid: bool`
  - `sequence_name: str`
  - `total_tracks: int`
  - `total_clips: int`
  - `total_fillers: int`
  - `errors: list[str]`
  - `warnings: list[str]` (including all unsupported Adobe effects converted to red markers)
  - Method `to_markdown(self) -> str`: Formats a clear Czech/English summary table for the editor (showing exact SMPTE timecode of every red marker / unsupported Adobe effect).
- Function `verify_aaf_against_ir(aaf_path: str | Path, expected_ir: ProjectIR) -> VerificationReport`:
  - Open `aaf_path` via `aaf2.open(str(aaf_path), "r")`.
  - Verify every `CompositionMob` matches a `SequenceIR` in `expected_ir`.
  - For every timeline slot:
    - Walk `slot.segment.components`.
    - Verify no component has length `<= 0`.
    - Verify sum of all `SourceClip` and `Filler` lengths equals `seq_ir.duration_frames`.
    - Verify every `SourceClip` start frame and length on the timeline matches the corresponding `ClipIR` in `expected_ir` with 0 frames tolerance.

## 3. ACCEPTANCE TESTS (`tests/test_roundtrip.py`)
1. Full End-to-End test 1: `simple_cut.prproj` -> `parse_prproj` -> `export_project_to_aaf` -> `verify_aaf_against_ir`. Assert `report.is_valid` is `True` and `"Warp Stabilizer"` appears in `report.warnings` / `report.to_markdown()`.
2. Full End-to-End test 2: `nested_seq.prproj` -> `parse_prproj(flatten_nested=True)` -> `export_project_to_aaf` -> `verify_aaf_against_ir`. Assert `report.is_valid` is `True`.
3. Full End-to-End test 3: `sample_audition.sesx` -> `parse_sesx` -> `export_project_to_aaf(embed_audio=True)` -> `verify_aaf_against_ir`. Assert `report.is_valid` is `True`.

## 4. STOP RULES
- Run `pytest tests/test_roundtrip.py` and stop immediately when green.
"""

# =============================================================================
# 12. TASK T09: CLI, CMX 3600 EDL Fallback & Křovák's GUI (Gemini 3.8 Flash)
# =============================================================================
FILES[".antigravity/tasks/T09_cli_and_gui.md"] = """# TASK T09: CLI, CMX 3600 EDL Generator & Křovák's One-Click GUI

- **Primary Model:** Gemini 3.8 Flash
- **Escalation Model:** Gemini 4 Argon
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `src/machete/ir/timecode.py`
  - `src/machete/ir/schema.py`
  - `src/machete/parsers/prproj_extract.py`
  - `src/machete/parsers/sesx_extract.py`
  - `src/machete/exporters/aaf_core.py`
  - `src/machete/verify/aaf_inspector.py`
- **Target Outputs (Write):**
  - `src/machete/exporters/edl_cmx3600.py`
  - `src/machete/cli.py`
  - `src/machete/gui.py`
  - `tests/test_cli_and_edl.py`

## 1. OBJECTIVE
Deliver the final user-facing tools: a backup CMX 3600 EDL exporter (`edl_cmx3600.py`), a full-featured CLI (`cli.py`), and a zero-dependency tkinter GUI (`gui.py`) tailored for Křovák.

## 2. SPECIFICATIONS

### A. `src/machete/exporters/edl_cmx3600.py`
Implement `export_sequence_to_edl(seq: SequenceIR, media_sources: dict[str, MediaSourceIR], output_path: str | Path) -> Path`:
- Write standard CMX 3600 header: `TITLE: {seq.name}` and `FCM: DROP FRAME` or `NON-DROP FRAME`.
- For each clip on the primary video track (or audio track if audio-only), format standard event lines:
  `001  {REEL:<8} V     C        {SRC_IN} {SRC_OUT} {REC_IN} {REC_OUT}`
  `* FROM CLIP NAME: {clip.name}`
- Include markers/unsupported effects as `* LOC: {TC} RED     {marker.name}` lines.

### B. `src/machete/cli.py`
Use `argparse` to provide command `machete`:
- Usage: `machete convert <input_file> -o <output.aaf> [--embed-audio] [--split-mono] [--no-flatten] [--also-edl] [--report <report.md>]`
- Automatically detect `.prproj` vs `.sesx` by file extension.
- Run `verify_aaf_against_ir` automatically after every export; exit with code 0 if valid, 1 if verification fails.
- Usage: `machete gui` launches the desktop window.

### C. `src/machete/gui.py`
Build a clean `tkinter` window titled `"Křovákova Mačeta — Adobe -> Avid Překladač"`:
- File picker for input (`.prproj` / `.sesx`) and output (`.aaf`).
- Checkboxes:
  - `[x] Zploštit vnořené sekvence (Flatten Nested Sequences)`
  - `[x] Vložit WAV zvuk přímo do AAF (Embedded Audio pro Pro Tools)`
  - `[x] Rozdělit stereo stopy na mono (A1.L / A2.R)`
  - `[x] Vygenerovat záložní CMX 3600 EDL a kontrolní report`
- Big button `"PROSEKAT DO AVIDU"` that runs the conversion, verifies the output, and displays the diagnostic report directly in a text panel.

## 3. ACCEPTANCE TESTS (`tests/test_cli_and_edl.py`)
1. Test `main(["convert", str(prproj_path), "-o", str(aaf_path), "--also-edl", "--report", str(report_path)])` returns exit code 0.
2. Assert `.aaf`, `.edl`, and `.md` report files are created on disk and non-empty.
3. Assert `.edl` contains `TITLE: Main_Edit_25fps` and `001` event line with valid SMPTE timecodes.

## 4. STOP RULES
- Run full test suite `pytest` across all test files.
- Once 100% of tests pass, stop immediately. Project is complete.
"""


def main() -> None:
    # Cílový kořen projektu (výchozí: aktuální adresář)
    target_arg = sys.argv[1] if len(sys.argv) > 1 else "."
    project_root = Path(target_arg).resolve()
    zip_path = project_root / "krovak-machete-antigravity-blueprint.zip"

    print(f"-> Inicializuji Křovákovu Mačetu v: {project_root}")

    # Vytvoření prázdných balíčkových složek pro zdrojový kód a testy
    empty_dirs = [
        "src/machete/ir",
        "src/machete/parsers",
        "src/machete/exporters",
        "src/machete/verify",
        "tests/fixtures",
        "docs",
        ".antigravity/tasks",
    ]
    for d in empty_dirs:
        (project_root / d).mkdir(parents=True, exist_ok=True)

    # Zápis všech souborů na disk a současně do ZIP archivu
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel_path, content in FILES.items():
            full_path = project_root / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            zf.writestr(f"krovak-machete/{rel_path}", content)
            print(f"  + Zapsán: {rel_path}")

    print(f"\n[OK] Složka projektu připravena v: {project_root}")
    print(f"[OK] ZIP balíček vytvořen v:        {zip_path}")
    print(f"[OK] Celkem zapsáno souborů:        {len(FILES)}")


if __name__ == "__main__":
    main()
