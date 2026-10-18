from __future__ import annotations

from pathlib import Path
import queue
import random
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from machete.assets.resolver import get_asset_path
from machete.cli import run_conversion_pipeline
from machete.verify.aaf_inspector import VerificationReport

# Visual theme constants
COLOR_PARCHMENT = "#F3EBD8"
COLOR_PARCHMENT_DARK = "#E6D9BE"
COLOR_CHARCOAL = "#1E1E1E"
COLOR_WOOD_DARK = "#3E2723"
COLOR_ACCENT = "#8B2500"
COLOR_WHITE = "#FFFFFF"


class DwarfProgressMonitor(tk.Frame):
    """Animated progress monitor featuring the Dwarf Stonemason woodcut scene."""

    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        super().__init__(parent, bg=COLOR_PARCHMENT_DARK, bd=2, relief="groove", **kwargs)
        self.canvas_w = 480
        self.canvas_h = 270

        self.canvas = tk.Canvas(
            self,
            width=self.canvas_w,
            height=self.canvas_h,
            bg=COLOR_PARCHMENT,
            highlightthickness=1,
            highlightbackground=COLOR_CHARCOAL,
        )
        self.canvas.pack(padx=8, pady=(8, 4))

        self.status_label = tk.Label(
            self,
            text="Sekera připravena k dílu.",
            bg=COLOR_PARCHMENT_DARK,
            fg=COLOR_CHARCOAL,
            font=("Courier", 10, "bold"),
            wraplength=460,
        )
        self.status_label.pack(padx=8, pady=(0, 6))

        # Assets
        self.scene_img: tk.PhotoImage | None = None
        self._load_scene_asset()

        # State & Animation
        self.state = "IDLE"  # IDLE, WORKING, SUCCESS, ERROR
        self.percentage = 0
        self.stage_message = "Sekera připravena k dílu."

        # Flying ink stone chips particles
        self.particles: list[dict[str, float]] = []
        self._init_particles()

        self._animating = False
        self._draw_frame()

    def _load_scene_asset(self) -> None:
        try:
            scene_file = get_asset_path("dwarf_scene.png")
            self.scene_img = tk.PhotoImage(file=str(scene_file))
        except Exception:
            self.scene_img = None

    def _init_particles(self) -> None:
        self.particles = []
        for _ in range(12):
            self.particles.append(
                {
                    "x": random.uniform(80, 200),
                    "y": random.uniform(90, 200),
                    "vx": random.uniform(4.0, 9.0),
                    "vy": random.uniform(-3.0, 1.0),
                    "size": random.uniform(2.0, 4.5),
                }
            )

    def set_state(self, state: str, percentage: int = 0, message: str = "") -> None:
        self.state = state
        self.percentage = max(0, min(100, percentage))
        if message:
            self.stage_message = message
        elif state == "IDLE":
            self.stage_message = "Sekera připravena k dílu."
        elif state == "SUCCESS":
            self.stage_message = "DÍLO DOKONÁNO — Kámen sedí na vzorek přesně (100%)"
        elif state == "ERROR":
            self.stage_message = "SEKERA NARAZILA NA KŘEMEN (Chyba konverze)"

        self.status_label.config(text=self.stage_message)

        if state == "WORKING" and not self._animating:
            self._animating = True
            self._animate_loop()
        elif state != "WORKING":
            self._animating = False
            self._draw_frame()

    def set_progress(self, percentage: int, message: str) -> None:
        self.set_state("WORKING", percentage, message)

    def _animate_loop(self) -> None:
        if not self._animating or self.state != "WORKING":
            self._animating = False
            self._draw_frame()
            return

        # Update particles
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.2  # subtle gravity
            if p["x"] > 420 or p["y"] > 230:
                p["x"] = random.uniform(100, 180)
                p["y"] = random.uniform(110, 180)
                p["vx"] = random.uniform(4.0, 8.5)
                p["vy"] = random.uniform(-3.5, 0.5)

        self._draw_frame()
        self.after(60, self._animate_loop)

    def _draw_frame(self) -> None:
        self.canvas.delete("all")

        # 1. Background scene
        if self.scene_img is not None:
            self.canvas.create_image(
                self.canvas_w // 2,
                self.canvas_h // 2,
                image=self.scene_img,
                anchor="center",
            )
        else:
            self.canvas.create_rectangle(
                0,
                0,
                self.canvas_w,
                self.canvas_h,
                fill=COLOR_PARCHMENT,
                outline=COLOR_CHARCOAL,
            )
            self.canvas.create_text(
                self.canvas_w // 2,
                self.canvas_h // 2,
                text="[Křovákova Sekera — Trpasličí dílna]",
                fill=COLOR_CHARCOAL,
                font=("Courier", 12, "bold"),
            )

        # 2. Masonry wall building on the right side
        wall_x = 390
        wall_y_bottom = 230
        block_w = 32
        block_h = 14
        total_blocks = 12
        visible_blocks = int((self.percentage / 100) * total_blocks)

        for i in range(visible_blocks):
            col = i % 2
            row = i // 2
            bx = wall_x + (col * (block_w + 2))
            by = wall_y_bottom - ((row + 1) * (block_h + 2))

            fill_color = "#C8B282" if self.state == "SUCCESS" else "#BDB092"
            self.canvas.create_rectangle(
                bx,
                by,
                bx + block_w,
                by + block_h,
                fill=fill_color,
                outline=COLOR_CHARCOAL,
                width=1,
            )
            # Brick texture line
            self.canvas.create_line(
                bx + 3,
                by + block_h // 2,
                bx + block_w - 3,
                by + block_h // 2,
                fill="#8C7A58",
            )

        # 3. Flying stone chips in WORKING state
        if self.state == "WORKING":
            for p in self.particles:
                s = p["size"]
                self.canvas.create_rectangle(
                    p["x"],
                    p["y"],
                    p["x"] + s,
                    p["y"] + s,
                    fill=COLOR_CHARCOAL,
                    outline="",
                )

        # 4. Success or Error banners
        if self.state == "SUCCESS":
            self.canvas.create_rectangle(
                40,
                20,
                440,
                60,
                fill=COLOR_PARCHMENT_DARK,
                outline=COLOR_WOOD_DARK,
                width=2,
            )
            self.canvas.create_text(
                240,
                40,
                text="✦ DÍLO DOKONÁNO — ZEĎ STOJÍ PEVNĚ ✦",
                fill=COLOR_WOOD_DARK,
                font=("Courier", 11, "bold"),
            )
        elif self.state == "ERROR":
            self.canvas.create_rectangle(
                40,
                20,
                440,
                60,
                fill="#FFDDDD",
                outline=COLOR_ACCENT,
                width=2,
            )
            self.canvas.create_text(
                240,
                40,
                text="✖ SEKERA NARAZILA NA KŘEMEN ✖",
                fill=COLOR_ACCENT,
                font=("Courier", 11, "bold"),
            )

        # 5. Parchment Progress Bar
        bar_x1 = 20
        bar_y1 = 244
        bar_x2 = 460
        bar_y2 = 262

        self.canvas.create_rectangle(
            bar_x1,
            bar_y1,
            bar_x2,
            bar_y2,
            fill=COLOR_PARCHMENT,
            outline=COLOR_CHARCOAL,
            width=2,
        )

        fill_w = int(((bar_x2 - bar_x1) * self.percentage) / 100)
        if fill_w > 0:
            fill_color = COLOR_WOOD_DARK if self.state != "ERROR" else COLOR_ACCENT
            self.canvas.create_rectangle(
                bar_x1 + 1,
                bar_y1 + 1,
                bar_x1 + fill_w,
                bar_y2 - 1,
                fill=fill_color,
                outline="",
            )

        pct_text = f"{self.percentage}%"
        self.canvas.create_text(
            (bar_x1 + bar_x2) // 2,
            (bar_y1 + bar_y2) // 2,
            text=pct_text,
            fill=COLOR_WHITE if self.percentage > 50 else COLOR_CHARCOAL,
            font=("Courier", 9, "bold"),
        )


class CustomWoodButton(tk.Frame):
    """Custom high-contrast woodcut button compatible with macOS Aqua and Windows."""

    def __init__(self, parent: tk.Widget, text: str, command: Any, **kwargs: Any) -> None:
        super().__init__(parent, bg=COLOR_WOOD_DARK, bd=2, relief="raised", cursor="hand2")
        self.command = command
        self._state = "normal"
        self._default_text = text

        self.label = tk.Label(
            self,
            text=text,
            bg=COLOR_WOOD_DARK,
            fg=COLOR_WHITE,
            font=("Courier", 12, "bold"),
            pady=8,
            cursor="hand2",
        )
        self.label.pack(fill="both", expand=True)

        for w in (self, self.label):
            w.bind("<Button-1>", self._on_press)
            w.bind("<ButtonRelease-1>", self._on_release)
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _on_press(self, event: Any = None) -> None:
        if self._state == "normal":
            self.config(relief="sunken")
            self.label.config(bg="#2E1C18")

    def _on_release(self, event: Any = None) -> None:
        if self._state == "normal":
            self.config(relief="raised")
            self.label.config(bg=COLOR_WOOD_DARK)
            if self.command:
                self.command()

    def _on_enter(self, event: Any = None) -> None:
        if self._state == "normal":
            self.config(bg="#5D4037")
            self.label.config(bg="#5D4037")

    def _on_leave(self, event: Any = None) -> None:
        if self._state == "normal":
            self.config(bg=COLOR_WOOD_DARK)
            self.label.config(bg=COLOR_WOOD_DARK)

    def config(self, **kwargs: Any) -> None:
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            if self._state == "disabled":
                self.configure(cursor="arrow", bg="#795548")
                self.label.configure(cursor="arrow", bg="#795548", fg="#D7CCC8")
            else:
                self.configure(cursor="hand2", bg=COLOR_WOOD_DARK)
                self.label.configure(cursor="hand2", bg=COLOR_WOOD_DARK, fg=COLOR_WHITE)
        if "text" in kwargs:
            self.label.config(text=kwargs.pop("text"))
        if kwargs:
            super().config(**kwargs)


class KrovakSekeraGUI:
    """Desktop GUI application for Křovákova Sekera."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Křovákova Sekera — Adobe -> Avid Překladač")
        self.root.geometry("740x660")
        self.root.minsize(700, 600)
        self.root.configure(bg=COLOR_PARCHMENT)

        self._set_app_icon()

        self.queue: queue.Queue[tuple[str, Any, Any]] = queue.Queue()

        self._build_ui()

    def _set_app_icon(self) -> None:
        try:
            icon_path = get_asset_path("dwarf_seal.png")
            self.icon_photo = tk.PhotoImage(file=str(icon_path))
            self.root.iconphoto(True, self.icon_photo)
        except Exception:
            pass

        try:
            icns_path = get_asset_path("dwarf_seal.icns")
            if sys.platform == "darwin":
                try:
                    self.root.iconbitmap(str(icns_path))
                except Exception:
                    pass
        except Exception:
            pass

    def _build_ui(self) -> None:
        # Top title banner
        banner = tk.Frame(self.root, bg=COLOR_PARCHMENT_DARK, bd=1, relief="ridge")
        banner.pack(fill="x", padx=10, pady=(10, 6))

        title_lbl = tk.Label(
            banner,
            text="⚔ KŘOVÁKOVA SEKERA — ADOBE -> AVID PŘEKLADAČ ⚔",
            bg=COLOR_PARCHMENT_DARK,
            fg=COLOR_WOOD_DARK,
            font=("Courier", 13, "bold"),
        )
        title_lbl.pack(pady=6)

        # File selection frame
        file_frame = tk.LabelFrame(
            self.root,
            text=" 1. Výběr kamenického díla ",
            bg=COLOR_PARCHMENT,
            fg=COLOR_CHARCOAL,
            font=("Courier", 10, "bold"),
            bd=2,
            relief="groove",
        )
        file_frame.pack(fill="x", padx=10, pady=4)

        # Input file
        tk.Label(
            file_frame,
            text="Vstupní projekt Adobe (.prproj / .sesx):",
            bg=COLOR_PARCHMENT,
            fg=COLOR_CHARCOAL,
            font=("Courier", 9, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            file_frame,
            textvariable=self.input_var,
            bg=COLOR_WHITE,
            fg=COLOR_CHARCOAL,
            font=("Courier", 9),
            insertbackground=COLOR_CHARCOAL,
        )
        self.input_entry.grid(row=1, column=0, sticky="ew", padx=(8, 4), pady=(0, 6))

        btn_browse_in = tk.Button(
            file_frame,
            text="Procházet...",
            command=self._browse_input,
            bg=COLOR_PARCHMENT_DARK,
            fg=COLOR_CHARCOAL,
            font=("Courier", 9),
            relief="raised",
        )
        btn_browse_in.grid(row=1, column=1, padx=(0, 8), pady=(0, 6))

        # Output file
        tk.Label(
            file_frame,
            text="Výstupní Avid AAF soubor (.aaf):",
            bg=COLOR_PARCHMENT,
            fg=COLOR_CHARCOAL,
            font=("Courier", 9, "bold"),
        ).grid(row=2, column=0, sticky="w", padx=8, pady=(4, 2))

        self.output_var = tk.StringVar()
        self.output_entry = tk.Entry(
            file_frame,
            textvariable=self.output_var,
            bg=COLOR_WHITE,
            fg=COLOR_CHARCOAL,
            font=("Courier", 9),
            insertbackground=COLOR_CHARCOAL,
        )
        self.output_entry.grid(row=3, column=0, sticky="ew", padx=(8, 4), pady=(0, 8))

        btn_browse_out = tk.Button(
            file_frame,
            text="Uložit jako...",
            command=self._browse_output,
            bg=COLOR_PARCHMENT_DARK,
            fg=COLOR_CHARCOAL,
            font=("Courier", 9),
            relief="raised",
        )
        btn_browse_out.grid(row=3, column=1, padx=(0, 8), pady=(0, 8))

        file_frame.columnconfigure(0, weight=1)

        # Options checkboxes frame
        opts_frame = tk.LabelFrame(
            self.root,
            text=" 2. Pravidla opracování ",
            bg=COLOR_PARCHMENT,
            fg=COLOR_CHARCOAL,
            font=("Courier", 10, "bold"),
            bd=2,
            relief="groove",
        )
        opts_frame.pack(fill="x", padx=10, pady=4)

        self.flatten_var = tk.BooleanVar(value=True)
        self.embed_var = tk.BooleanVar(value=False)
        self.split_var = tk.BooleanVar(value=False)
        self.edl_var = tk.BooleanVar(value=True)

        cb1 = tk.Checkbutton(
            opts_frame,
            text="Zploštit vnořené sekvence (Flatten Nested Sequences)",
            variable=self.flatten_var,
            bg=COLOR_PARCHMENT,
            fg=COLOR_CHARCOAL,
            font=("Courier", 9),
            activebackground=COLOR_PARCHMENT,
        )
        cb1.grid(row=0, column=0, sticky="w", padx=8, pady=2)

        cb2 = tk.Checkbutton(
            opts_frame,
            text="Vložit WAV zvuk přímo do AAF (Embedded Audio pro Pro Tools)",
            variable=self.embed_var,
            bg=COLOR_PARCHMENT,
            fg=COLOR_CHARCOAL,
            font=("Courier", 9),
            activebackground=COLOR_PARCHMENT,
        )
        cb2.grid(row=0, column=1, sticky="w", padx=8, pady=2)

        cb3 = tk.Checkbutton(
            opts_frame,
            text="Rozdělit stereo stopy na mono (A1.L / A2.R)",
            variable=self.split_var,
            bg=COLOR_PARCHMENT,
            fg=COLOR_CHARCOAL,
            font=("Courier", 9),
            activebackground=COLOR_PARCHMENT,
        )
        cb3.grid(row=1, column=0, sticky="w", padx=8, pady=2)

        cb4 = tk.Checkbutton(
            opts_frame,
            text="Vygenerovat záložní CMX 3600 EDL a kontrolní report",
            variable=self.edl_var,
            bg=COLOR_PARCHMENT,
            fg=COLOR_CHARCOAL,
            font=("Courier", 9),
            activebackground=COLOR_PARCHMENT,
        )
        cb4.grid(row=1, column=1, sticky="w", padx=8, pady=2)

        # Prominent Action Button
        self.btn_run = CustomWoodButton(
            self.root,
            text="⚔ PROSEKAT DO AVIDU (ZATNOUT SEKERU) ⚔",
            command=self._start_conversion,
        )
        self.btn_run.pack(fill="x", padx=10, pady=8)

        # Middle section: Animated Dwarf Progress Monitor
        self.monitor = DwarfProgressMonitor(self.root)
        self.monitor.pack(padx=10, pady=4)

        # Bottom section: Diagnostic Markdown Report Panel
        report_frame = tk.LabelFrame(
            self.root,
            text=" 3. Kamenický kontrolní zápis (Roundtrip Report) ",
            bg=COLOR_PARCHMENT,
            fg=COLOR_CHARCOAL,
            font=("Courier", 10, "bold"),
            bd=2,
            relief="groove",
        )
        report_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        scrollbar = tk.Scrollbar(report_frame)
        scrollbar.pack(side="right", fill="y")

        self.report_text = tk.Text(
            report_frame,
            bg="#FAF6EE",
            fg=COLOR_CHARCOAL,
            font=("Courier", 9),
            yscrollcommand=scrollbar.set,
            bd=1,
            relief="sunken",
        )
        self.report_text.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        scrollbar.config(command=self.report_text.yview)

    def _browse_input(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Vyberte projekt Adobe Premiere (.prproj) nebo Audition (.sesx)",
            filetypes=[
                ("Adobe Projekty", "*.prproj *.sesx"),
                ("Premiere Pro (.prproj)", "*.prproj"),
                ("Audition (.sesx)", "*.sesx"),
                ("Všechny soubory", "*.*"),
            ],
        )
        if file_path:
            self.input_var.set(file_path)
            if not self.output_var.get():
                auto_out = str(Path(file_path).with_suffix(".aaf"))
                self.output_var.set(auto_out)

    def _browse_output(self) -> None:
        file_path = filedialog.asksaveasfilename(
            title="Uložit výsledný Avid AAF soubor",
            defaultextension=".aaf",
            filetypes=[
                ("Avid AAF (*.aaf)", "*.aaf"),
                ("Všechny soubory", "*.*"),
            ],
        )
        if file_path:
            self.output_var.set(file_path)

    def _start_conversion(self) -> None:
        in_path_str = self.input_var.get().strip()
        if not in_path_str:
            messagebox.showwarning("Chybí vstupní soubor", "Vyberte prosím soubor .prproj nebo .sesx.")
            return

        in_path = Path(in_path_str)
        if not in_path.exists():
            messagebox.showerror("Soubor nenalezen", f"Vstupní soubor neexistuje:\n{in_path}")
            return

        out_path_str = self.output_var.get().strip()
        if not out_path_str:
            out_path = in_path.with_suffix(".aaf")
            self.output_var.set(str(out_path))
        else:
            out_path = Path(out_path_str)

        # Disable button during work
        self.btn_run.config(state="disabled", text="⏳ OSEKÁVÁM ZDIVO...")
        self.monitor.set_state("WORKING", 5, "Zatínám sekeru do projektu...")
        self.report_text.delete("1.0", tk.END)

        def worker() -> None:
            try:
                def progress_cb(pct: int, msg: str) -> None:
                    self.queue.put(("progress", pct, msg))

                report_path = out_path.with_suffix(".md") if self.edl_var.get() else None

                report = run_conversion_pipeline(
                    input_path=in_path,
                    output_path=out_path,
                    embed_audio=self.embed_var.get(),
                    split_mono=self.split_var.get(),
                    flatten_nested=self.flatten_var.get(),
                    also_edl=self.edl_var.get(),
                    report_path=report_path,
                    progress_callback=progress_cb,
                )
                self.queue.put(("success", report, None))
            except Exception as e:
                import traceback
                self.queue.put(("error", str(e), traceback.format_exc()))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        self.root.after(100, self._poll_queue)

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                action, data1, data2 = item

                if action == "progress":
                    self.monitor.set_progress(int(data1), str(data2))
                elif action == "success":
                    report: VerificationReport = data1
                    status_msg = (
                        "DÍLO DOKONÁNO — Kámen sedí na vzorek přesně (100%)"
                        if report.is_valid
                        else "VAROVÁNÍ — Nalezeny neshody při inspekci"
                    )
                    self.monitor.set_state("SUCCESS", 100, status_msg)
                    self.report_text.delete("1.0", tk.END)
                    self.report_text.insert(tk.END, report.to_markdown())
                    self.btn_run.config(state="normal", text="⚔ PROSEKAT DO AVIDU (ZATNOUT SEKERU) ⚔")
                    return
                elif action == "error":
                    err_msg, tb = str(data1), str(data2)
                    self.monitor.set_state("ERROR", 0, f"SEKERA NARAZILA NA KŘEMEN: {err_msg}")
                    self.report_text.delete("1.0", tk.END)
                    self.report_text.insert(
                        tk.END,
                        f"# CHYBA PŘI OSEKÁVÁNÍ PROJEKTU\n\n{err_msg}\n\n```\n{tb}\n```",
                    )
                    self.btn_run.config(state="normal", text="⚔ PROSEKAT DO AVIDU (ZATNOUT SEKERU) ⚔")
                    return
        except queue.Empty:
            pass

        self.root.after(100, self._poll_queue)


def launch_gui() -> None:
    """Launch the Křovákova Sekera desktop GUI application."""
    try:
        root = tk.Tk()
    except (tk.TclError, Exception) as e:
        print(f"Nelze spustit grafické rozhraní (chybí displej nebo Tcl/Tk): {e}")
        return

    app = KrovakSekeraGUI(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
