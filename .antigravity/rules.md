# KŘOVÁKOVA SEKERA (machete) — GLOBAL AGENT RULES

## 1. CORE INVARIANTS (NON-NEGOTIABLE)
1. **NO-FLOAT TIME LAW:** Never use `float` for time, frame rates, ticks, or audio samples. Always use `fractions.Fraction` or exact `int`.
2. **PREMIERE TICKS CONSTANT:** `PPRO_TICKS_PER_SEC = 254_016_000_000`.
3. **AUDITION SAMPLES:** Time in `.sesx` is measured in integer audio samples relative to the session `sampleRate` (e.g., `48000`).
4. **CANONICAL IR WALL:** Input parsers (`src/machete/parsers/`) MUST ONLY output `ProjectIR` (defined in `src/machete/ir/schema.py`). Exporters (`src/machete/exporters/`) MUST ONLY read `ProjectIR`. Direct parser-to-AAF coupling is strictly forbidden.
5. **SCHEMA LOCK:** After Task `T01` is complete, `src/machete/ir/schema.py` is READ-ONLY for all subsequent tasks (`T02`–`T10`).
6. **AVID ZERO-GAP LAW:** Every AAF `Sequence` track must start at frame `0` and be strictly contiguous. Any empty gap between clips MUST be filled with `aaf2.components.Filler` of exact integer frame length. The sum of all component lengths in a track must equal the sequence duration.
7. **DETERMINISTIC MOB IDs:** Generate `aaf2.mobid.MobID` deterministically using `uuid.uuid5(uuid.NAMESPACE_DNS, seed_string)` so repeated exports relink identically in Avid Media Composer and Pro Tools.
8. **UNSUPPORTED ADOBE EFFECTS -> AVID MARKERS:** Never silently drop Premiere effects (Warp Stabilizer, Lumetri Color, Speed Ramps / Time Remapping). Convert them into red Avid `DescriptiveMarker` notices on the timeline with actionable text for the editor.

## 2. TOKEN & CONTEXT CONSERVATION RULES
- **Strict File Scope:** Read ONLY the files listed under `Allowed Context (Read)` in your active Task File. Never scan the entire repository tree.
- **No Raw XML Dumps:** Never print or read large `.prproj` XML files into LLM context. Use only small synthetic fixtures in `tests/fixtures/` (<15 KB).
- **Zero-Prose Code:** Do not write decorative comments or lengthy docstrings. Keep code concise, strictly typed, and self-explanatory.
- **Circuit Breaker (3-Strike Rule):** If `pytest` fails 3 consecutive times on the same error or assertion, STOP immediately. Write the exact traceback and root-cause hypothesis into `BLOCKERS.md` and terminate the session. Do not loop.
- **Stop-On-Green:** The moment all acceptance tests specified in your Task File pass, stop generating explanations and finish the task immediately.
