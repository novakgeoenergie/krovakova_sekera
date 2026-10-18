# TASK T10: Standalone Packaging, macOS App Bundle (.dmg) & Windows Executable

- **Primary Model:** Gemini 3.8 Flash
- **Escalation Model:** Gemini 4 Argon
- **Allowed Context (Read):**
  - `.antigravity/rules.md`
  - `pyproject.toml`
  - `src/machete/cli.py`
  - `src/machete/gui.py`
  - `src/machete/assets/dwarf_seal.icns`
  - `src/machete/assets/dwarf_seal.png`
  - `src/machete/assets/dwarf_scene.png`
- **Target Outputs (Write):**
  - `src/machete/assets/resolver.py`
  - `packaging/machete.spec`
  - `scripts/build_dist.py`
  - `.github/workflows/release.yml`
  - `tests/test_packaging.py`
  - Update `pyproject.toml` (packaging dependencies)
  - Update `README.md` (Token economy & distribution guide)

## 1. OBJECTIVE
Enable zero-dependency, zero-Python distribution for end-user video editors (Křovák). The end user MUST NOT be required to install Python, pip, or any system libraries.
Deliver a turnkey standalone packaging pipeline:
1. Native macOS Application Bundle (`Křovákova Sekera.app`) packaged into a drag-and-drop `.dmg` installer with the `dwarf_seal.icns` application icon.
2. Standalone Windows executable (`KrovakovaSekera.exe`) via cross-compatible PyInstaller specification.
3. Automated multi-platform GitHub Actions release workflow that automatically builds and attaches macOS `.dmg` and Windows `.exe` to GitHub releases.

## 2. SPECIFICATIONS

### A. Asset Resolver (`src/machete/assets/resolver.py`)
Implement a deterministic asset locator `get_asset_path(filename: str) -> Path`:
- When running in frozen mode (PyInstaller `getattr(sys, "frozen", False)`):
  - Resolve from `Path(sys._MEIPASS) / "machete" / "assets" / filename` (or `sys._MEIPASS / filename` fallback).
- When running from source in development:
  - Resolve from `Path(__file__).resolve().parent / filename`.
- Raise `FileNotFoundError` with clear explanation if asset is missing.
- Ensure `src/machete/gui.py` and `src/machete/cli.py` use this resolver.

### B. PyInstaller Specification (`packaging/machete.spec`)
Configure PyInstaller spec to bundle the entire Python runtime, C-extensions, and assets:
- **Binaries & Data:**
  - Embed `src/machete/assets/` into `machete/assets`.
- **Hidden Imports:**
  - Ensure `pyaaf2`, `pydantic`, `pydantic_core`, `tkinter`, `fractions`, `uuid`, `xml.etree.ElementTree`, `gzip` are explicitly collected.
- **macOS Bundle Configuration:**
  - App Name: `Křovákova Sekera`
  - Bundle Identifier: `cz.krovak.machete`
  - Version: `0.1.0`
  - Icon: `src/machete/assets/dwarf_seal.icns`
  - High-DPI support (`NSHighResolutionCapable = True`).
- **CLI Binary:**
  - Also produce standalone console binary `machete` for power users/pipeline automation.

### C. Distribution Builder (`scripts/build_dist.py`)
Create a CLI build helper executable via `python scripts/build_dist.py [--dmg] [--clean]`:
- Run `pyinstaller packaging/machete.spec --clean --noconfirm`.
- On macOS:
  - If `--dmg` requested, construct a clean disk image `Krovakova-Sekera-macOS.dmg` using macOS native `hdiutil create` with an `/Applications` symlink for instant drag-and-drop installation.
- Verify built bundle integrity: check that the executable starts and outputs `--version` or passes headless dry-run.

### D. Multi-Platform GitHub Actions Workflow (`.github/workflows/release.yml`)
Configure GitHub Actions matrix build triggered on tag push (`v*`):
- Jobs:
  - `build-macos`: runs on `macos-latest`, sets up Python 3.11, builds `.app` + `.dmg`, uploads `Krovakova-Sekera-macOS-Universal.dmg`.
  - `build-windows`: runs on `windows-latest`, sets up Python 3.11, builds standalone `KrovakovaSekera-Windows.exe`.
  - `create-release`: attaches both artifacts to the GitHub Release with automated changelog.

### E. Configuration Updates
- In `pyproject.toml`, add optional dependency group:
  ```toml
  [project.optional-dependencies]
  packaging = [
      "pyinstaller>=6.5.0",
  ]
  ```

## 3. ACCEPTANCE TESTS (`tests/test_packaging.py`)
1. Test `get_asset_path`:
   - Returns existing file paths for `dwarf_scene.png`, `dwarf_seal.png`, `dwarf_seal.icns` in standard live mode.
   - Correctly resolves mocked `sys._MEIPASS` path when `sys.frozen = True`.
2. Test `packaging/machete.spec`:
   - Parse and execute `machete.spec` in a synthetic environment or validate syntax, data tuples, and bundle options without fatal errors.
3. Test `build_dist.py`:
   - CLI flags `--help`, `--clean` parse correctly.

## 4. STOP RULES
- Run `pytest tests/test_packaging.py` and verify all tests pass.
- Stop immediately once all tests are green.
