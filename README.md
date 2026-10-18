# Křovákova Sekera (`krovak-machete`)

> **Deterministický překladač filmových projektů Adobe Premiere Pro (`.prproj`) a Adobe Audition (`.sesx`) do nativního formátu Avid AAF (`.aaf` Edit Protocol) a CMX 3600 EDL pro Avid Media Composer a Avid Pro Tools.**

---

## 1. O projektu
Křovákova Sekera je specializovaný nástroj pro filmovou a televizní postprodukci zajišťující 100% snímkově a vzorkově přesný (**Frame & Sample Accurate**) převod časových os celovečerních filmových projektů bez nutnosti instalovat Adobe Creative Cloud aplikace.

### Klíčové vlastnosti
* **100% Frame & Sample Accuracy:** Přesná racionální matematika (`Fraction` & `int`) bez snímkového driftu i na celovečerních 3+ hodinových stopážích.
* **Avid Zero-Gap Law:** Striktní dodržení spojitosti stop kompozice – mezery i konce stop jsou vyplněny přesnými objekty `Filler`.
* **Deterministická Mob ID:** Stabilní UUIDv5 pro spolehlivý conform a relinkování v Media Composeru i Pro Tools.
* **Červené markery pro Adobe efekty:** Žádný filtr nezmizí beze stopy – nepodporované efekty (*Warp Stabilizer*, *Lumetri* apod.) jsou převedeny na červené značky na časové ose s popisem pro editora.
* **Pro Tools Audio Essence:** Podpora embedded 16-bit PCM WAV zvuku a stereo-to-mono splitu pro zvuková studia.
* **Dvě uživatelská rozhraní:** Výkonné CLI pro dávkové zpracování a přehledné desktopové GUI okno s pergameno-dřevěným designem a animovaným kamenickým monitorem.

---

## 2. Rychlý start

### Spuštění grafického rozhraní (GUI)
```bash
./machete gui
```

### Převod přes příkazovou řádku (CLI)
```bash
# Základní převod Premiere projektu do AAF včetně kontrolního reportu a EDL
./machete convert projekt.prproj -o projekt.aaf --also-edl --report report.md

# Převod Audition relace s vloženým zvukem pro Pro Tools a rozdělením sterea na mono
./machete convert session.sesx -o mix.aaf --embed-audio --split-mono
```

---

## 3. Distribuce a Standalone balíčky

Křovákova Sekera je distribuována jako samostatná aplikace bez nutnosti instalace Pythonu:
* **macOS:** Nativní aplikační balíček `Křovákova Sekera.app` a diskový obraz `.dmg` s instalací přetažením do `/Applications`.
* **Windows:** Samostatný spustitelný soubor `KrovakovaSekera.exe`.

### Lokální sestavení balíčků
```bash
# Instalace balíčkovacích závislostí
pip install -e ".[packaging]"

# Lokální sestavení DMG na macOS
python scripts/build_dist.py --clean --dmg
```

### Automatizované CI/CD
Při vytvoření a odeslání tagu verze (`v*`) do repozitáře spustí GitHub Actions workflow `.github/workflows/release.yml`, které automaticky sestaví nativní binárky na macOS i Windows a publikuje je do GitHub Releases.

---

## 4. Vývoj a testování
Podrobnou specifikaci architektury a formátů naleznete v [`docs/PROJEKTOVA_DOKUMENTACE.md`](docs/PROJEKTOVA_DOKUMENTACE.md).

```bash
# Spuštění kompletní testovací sady
pytest
```
