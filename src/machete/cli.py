from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
import sys

from machete.exporters.aaf_audio import split_stereo_tracks_to_mono
from machete.exporters.aaf_core import export_project_to_aaf
from machete.exporters.edl_cmx3600 import export_sequence_to_edl
from machete.parsers.prproj_extract import parse_prproj
from machete.parsers.sesx_extract import parse_sesx
from machete.verify.aaf_inspector import VerificationReport, verify_aaf_against_ir

# Alias for backwards compatibility / specifications referencing VerificationResult
VerificationResult = VerificationReport


def run_conversion_pipeline(
    input_path: str | Path,
    output_path: str | Path | None = None,
    embed_audio: bool = False,
    split_mono: bool = False,
    flatten_nested: bool = True,
    also_edl: bool = False,
    report_path: str | Path | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
) -> VerificationReport:
    """Execute the 5-stage deterministic conversion and verification pipeline.

    1. Průzkum slojí a indexace Adobe XML... (15%)
    2. Osekávání vnořených sekvencí na čisté kvádry... (40%)
    3. Kladení základů Avid AAF stromu... (70%)
    4. Třídění a zalévání audio esencí (PCM WAV)... (85%)
    5. Kamenická inspekce integrity zdiva (Roundtrip Verifier)... (100%)
    """
    in_file = Path(input_path).resolve()
    if not in_file.exists():
        raise FileNotFoundError(f"Vstupní soubor nebyl nalezen: {in_file}")

    if output_path is not None:
        out_file = Path(output_path).resolve()
    else:
        out_file = in_file.with_suffix(".aaf")

    # Stage 1: Průzkum slojí a indexace
    if progress_callback:
        progress_callback(15, "Průzkum slojí a indexace Adobe XML...")

    ext = in_file.suffix.lower()

    # Stage 2: Osekávání a parsing sekvencí
    if progress_callback:
        progress_callback(40, "Osekávání vnořených sekvencí na čisté kvádry...")

    if ext == ".sesx":
        project_ir = parse_sesx(in_file)
    else:
        project_ir = parse_prproj(in_file, flatten_nested=flatten_nested)

    if split_mono:
        project_ir = project_ir.model_copy(
            update={"sequences": [split_stereo_tracks_to_mono(s) for s in project_ir.sequences]}
        )

    # Stage 3: Kladení základů Avid AAF
    if progress_callback:
        progress_callback(70, "Kladení základů Avid AAF stromu...")

    export_project_to_aaf(project_ir, out_file, embed_audio=embed_audio)

    if also_edl and project_ir.sequences:
        edl_path = out_file.with_suffix(".edl")
        export_sequence_to_edl(project_ir.sequences[0], project_ir.media_sources, edl_path)

    # Stage 4: Třídění a zalévání audio esencí
    if progress_callback:
        progress_callback(85, "Třídění a zalévání audio esencí (PCM WAV)...")

    # Stage 5: Kamenická inspekce integrity zdiva
    if progress_callback:
        progress_callback(100, "Kamenická inspekce integrity zdiva (Roundtrip Verifier)...")

    report = verify_aaf_against_ir(out_file, project_ir)

    if report_path is not None:
        r_path = Path(report_path).resolve()
        r_path.parent.mkdir(parents=True, exist_ok=True)
        r_path.write_text(report.to_markdown(), encoding="utf-8")

    return report


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for machete."""
    if argv is None:
        argv = sys.argv[1:]

    # Filter out macOS Process Serial Number argument when launched from Finder
    argv = [arg for arg in argv if not arg.startswith("-psn")]

    parser = argparse.ArgumentParser(
        prog="machete",
        description="Křovákova Mačeta / Sekera — Adobe (.prproj / .sesx) -> Avid AAF/EDL překladač",
    )
    parser.add_argument("--gui", action="store_true", help="Spustit grafické rozhraní (Křovákova Sekera)")

    subparsers = parser.add_subparsers(dest="command", help="Příkaz k provedení")

    convert_parser = subparsers.add_parser("convert", help="Převést projekt Adobe na Avid AAF")
    convert_parser.add_argument("input_file", type=str, help="Cesta k souboru .prproj nebo .sesx")
    convert_parser.add_argument("-o", "--output", type=str, default=None, help="Cesta k výstupnímu souboru .aaf")
    convert_parser.add_argument("--embed-audio", action="store_true", help="Vložit WAV audio data přímo do AAF")
    convert_parser.add_argument("--split-mono", action="store_true", help="Rozdělit stereo stopy na mono (L/R)")
    convert_parser.add_argument("--no-flatten", action="store_true", help="Nezplošťovat vnořené sekvence")
    convert_parser.add_argument("--also-edl", action="store_true", help="Vygenerovat také záložní CMX 3600 EDL")
    convert_parser.add_argument("--report", type=str, default=None, help="Cesta k uložení Markdown kontrolního reportu")

    subparsers.add_parser("gui", help="Spustit grafické rozhraní")

    if not argv:
        if getattr(sys, "frozen", False):
            from machete.gui import launch_gui
            launch_gui()
            return 0
        parser.print_help()
        return 0

    # If first argument looks like a file and not a command or flag, treat as convert
    if argv and argv[0] not in ("convert", "gui", "-h", "--help") and not argv[0].startswith("-"):
        argv = ["convert"] + argv

    args = parser.parse_args(argv)

    if args.gui or args.command == "gui":
        from machete.gui import launch_gui
        launch_gui()
        return 0

    if args.command == "convert":
        report = run_conversion_pipeline(
            input_path=args.input_file,
            output_path=args.output,
            embed_audio=args.embed_audio,
            split_mono=args.split_mono,
            flatten_nested=not args.no_flatten,
            also_edl=args.also_edl,
            report_path=args.report,
        )
        print(report.to_markdown())
        return 0 if report.is_valid else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
