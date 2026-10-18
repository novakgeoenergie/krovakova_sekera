# Manuální Testovací Protokol — Křovákova Sekera (`machete`)

Tento balíček obsahuje kompletní sadu reálných multimediálních souborů (video s vypáleným časovým kódem, 48kHz WAV audio) a připravené testovací projekty pro manuální ověření před balíčkováním (Task T10).

---

## 📁 Přehled testovacích složek

Každá složka je zcela samostatná a obsahuje jak zdrojový projekt Adobe, tak skutečná média i předexportovaný soubor AAF:

### 1. `test_01_simple_cut/` (Základní střih + efekty + audio automatizace)
- **`simple_cut.prproj`**: Premiere Pro projekt na 25 fps.
- **`Shot_01.mov`**: 25fps video s vypáleným TC `01:00:00:00`–`01:00:05:24` a vizuálním čítačem snímků.
- **`sample_tone.wav`**: 48 kHz mono tón (440 Hz).
- **`simple_cut.aaf`**: Předexportovaný AAF pro Avid.
- **Klíčové vlastnosti k ověření:**
  - V1 obsahuje dva střihy ze stejného zdrojového videa s mezerou mezi nimi (Avid Zero-Gap Law: mezera je vyplněna `Fillerem`).
  - První klip v Premiere obsahuje nepodporovaný efekt **Warp Stabilizer**. V AAF se musí objevit jako **červený marker (DescriptiveMarker)** na timeline s textem pro střihače.
  - A1 obsahuje audio stopu s volume automatizací (fade z 1.0 na 0.5).

### 2. `test_02_nested_seq/` (Vnořené sekvence / Flattening)
- **`nested_seq.prproj`**: Premiere Pro projekt obsahující master sekvenci a v ní vnořenou podsestavu (`Child_Seq`).
- **`Shot_A.mov`** & **`Shot_B.mov`**: 25fps barevně odlišená videa s TC čítači.
- **`nested_seq.aaf`**: Vyexportovaný AAF se zploštělou (flattened) časovou osou.
- **Klíčové vlastnosti k ověření:**
  - Vnořená sekvence je rozložena na jednotlivé střihy `Shot_A` a `Shot_B`.
  - Žádné kolize na časové ose, přesná návaznost na frame.

### 3. `test_03_audition_mix/` (Adobe Audition -> Pro Tools)
- **`sample_audition.sesx`**: Multitrack session ze vzorkovací frekvencí 48 000 Hz.
- **`sample_tone.wav`**: 48 kHz audio esence.
- **`sample_audition_embedded.aaf`**: AAF s **vloženým zvukem přímo uvnitř souboru** (Embedded).
- **`sample_audition_linked.aaf`**: AAF s odkazovaným (Linked) zvukem.
- **Klíčové vlastnosti k ověření:**
  - Pro Tools otevře `sample_audition_embedded.aaf` bez dotazu na umístění médií.
  - Hlasitostní obálka (Volume Automation) odpovídá breakpointům v Audition.

### 4. `test_04_real_premiere_project/` (Reálný 1.1 MB Adobe Premiere projekt z produkce)
- **`sample.prproj`**: Reálný projekt Adobe Premiere Pro (z repozitáře `projectivetech/media-samples`) se sekvencí `FlavourSys xy1` (548 frames, 25 fps).
- **Média pro relinkování na časové ose:**
  - `Comic1.mov` (10s, 25fps)
  - `Pt2 n.mov` (8s, 25fps)
  - `PT3 n.mov` (6s, 25fps)
  - `Pt1 n.mov` (6s, 25fps)
- **`sample.aaf`**: Předexportovaný AAF soubor přímo pro Avid Media Composer.
- **Klíčové vlastnosti k ověření:**
  - Otevři `sample.prproj` v Adobe Premiere Pro — projekt se otevře a média se ihned najdou bez chyby.
  - V Avid Media Composeru importuj `sample.aaf` a zkontroluj návaznost 4 střihů a čítačů na V1.

---

## 🛠️ Postup manuálního testování

### Krok A: Kontrola v Adobe Premiere Pro / Audition
1. Otevři `test_01_simple_cut/simple_cut.prproj` v Adobe Premiere Pro.
2. Zkontroluj, že video `Shot_01.mov` a zvuk `sample_tone.wav` hrají bez hlášení "Media Offline".
3. Poznamenej si časový kód střihů a pozici markeru/efektu.
4. Otevři `test_03_audition_mix/sample_audition.sesx` v Adobe Audition a prohlédni si volume křivku.

### Krok B: Import do Avid Media Composer
1. V Media Composeru vytvoř projekt s formátem **1080p 25fps**.
2. Vytvoř nový Bin (např. `Machete_Test`).
3. Zvol **File -> Import Media...** (nebo přetáhni `simple_cut.aaf` do Binu).
4. Otevři sekvenci na časové ose:
   - [ ] **Zero-Gap Law:** Zkontroluj, že mezi klipy není žádná černá díra bez filleru (časová osa je spojitá od TC 0).
   - [ ] **Frame Accuracy:** Zkontroluj, že čítač vypálený v obraze (`TC: 01:00:...`) přesně sedí na střihové body.
   - [ ] **Červený marker:** Na prvním klipu musí být červený marker upozorňující na *Warp Stabilizer*.
5. Zopakuj pro `nested_seq.aaf` a zkontroluj rozpad vnořené sekvence na jednotlivé záběry A a B.

### Krok C: Import do Avid Pro Tools
1. V Pro Tools zvol **File -> Open Session...** nebo **Import -> Session Data...**.
2. Vyber `test_03_audition_mix/sample_audition_embedded.aaf`.
3. V dialogu importu zvol:
   - Sample Rate: 48 kHz
   - Bit Depth: 16 bit
   - Track Offset: 0
4. Zkontroluj:
   - [ ] Audio stopy se ihned vykreslí s vlnovkami (Waveforms) bez nutnosti relinkovat externí WAV.
   - [ ] Přepni zobrazení stopy na **Volume Automation** — ověř přítomnost zlomových bodů (breakpoints) a průběh křivky.

---

## 🔄 Jak přegenerovat soubory nebo provést nový převod

Pokud provedeš změnu v kódu převodníku, můžeš celou sadu přegenerovat jedním příkazem z kořene repozitáře:

```bash
python scripts/generate_manual_test_suite.py
```
