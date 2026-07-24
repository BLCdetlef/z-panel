#!/usr/bin/env python3
from __future__ import annotations

"""
ZUSTAND News Studio 3.3

Erweiterung von News Studio 3.2:

- Bildprompt-Fenster passt sich automatisch an die Bildschirmgröße an
- Fenster wird zentriert und bleibt vollständig innerhalb des sichtbaren Bereichs
- untere Schaltflächenleiste bleibt immer sichtbar
- nur der Promptbereich wächst bzw. scrollt
- vertikale und horizontale Scrollleiste für den Prompt

Die Datei wird neben news_studio_3_2.py, news_studio_3_1.py
und news_studio_3_0.py abgelegt.
"""

import importlib.util
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_3_2.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_3_2.py wurde nicht gefunden.\n"
        "Lege news_studio_3_3.py in denselben Ordner wie "
        "news_studio_3_2.py, news_studio_3_1.py und news_studio_3_0.py."
    )

spec = importlib.util.spec_from_file_location("news_studio_3_2_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("news_studio_3_2.py konnte nicht geladen werden.")

base32 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base32
spec.loader.exec_module(base32)

base = base32.base


class NewsStudio33(base32.NewsStudio32):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 3.3")
        self._replace_widget_text("ZUSTAND News Studio 3.2", "ZUSTAND News Studio 3.3")
        self.status_var.set(
            "News Studio 3.3 bereit │ responsives Bildprompt-Fenster aktiv"
        )

    @staticmethod
    def _fit_and_center(window, parent=None) -> None:
        """Passt das Fenster an den nutzbaren Bildschirm an und zentriert es."""
        window.update_idletasks()

        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()

        # Genügend Abstand für Taskleiste, Fensterrand und kleine Displays.
        max_w = max(680, screen_w - 80)
        max_h = max(480, screen_h - 140)

        width = min(940, max_w)
        height = min(690, max_h)

        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2 - 10)

        window.geometry(f"{width}x{height}+{x}+{y}")
        window.minsize(min(680, width), min(460, height))

    def open_image_workflow(self):
        image_id = self.article_vars["imageId"].get().strip()
        if not image_id:
            base.messagebox.showwarning(
                "Bild-ID fehlt",
                "Bitte zuerst eine Bild-ID eintragen, zum Beispiel KL_0001_01."
            )
            return

        window = base.tk.Toplevel(self)
        window.title(f"Bildworkflow – {image_id}")
        window.transient(self)
        self._fit_and_center(window, self)

        # Grid sorgt dafür, dass die Fußzeile immer sichtbar bleibt.
        window.rowconfigure(0, weight=1)
        window.columnconfigure(0, weight=1)

        outer = base.ttk.Frame(window, padding=14)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(0, weight=1)

        base.ttk.Label(
            outer,
            text="ZUSTAND-Bildprompt",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")

        base.ttk.Label(
            outer,
            text=(
                "Der Prompt wird aus dem Artikel gebildet. Kopiere ihn anschließend "
                "in ChatGPT, erzeuge dort ein Bild und übernimm die gespeicherte "
                "Bilddatei danach wieder in das News Studio."
            ),
            wraplength=820,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(2, 10))

        prompt_frame = base.ttk.Frame(outer)
        prompt_frame.grid(row=2, column=0, sticky="nsew")
        prompt_frame.rowconfigure(0, weight=1)
        prompt_frame.columnconfigure(0, weight=1)

        prompt_text = base.tk.Text(
            prompt_frame,
            wrap="word",
            undo=True,
            padx=8,
            pady=8,
        )
        prompt_text.grid(row=0, column=0, sticky="nsew")

        y_scroll = base.ttk.Scrollbar(
            prompt_frame,
            orient="vertical",
            command=prompt_text.yview,
        )
        y_scroll.grid(row=0, column=1, sticky="ns")
        prompt_text.configure(yscrollcommand=y_scroll.set)

        x_scroll = base.ttk.Scrollbar(
            prompt_frame,
            orient="horizontal",
            command=prompt_text.xview,
        )
        x_scroll.grid(row=1, column=0, sticky="ew")
        prompt_text.configure(xscrollcommand=x_scroll.set)

        prompt_text.insert("1.0", self.build_image_prompt())

        # Diese Zeile bleibt unabhängig von der Fensterhöhe sichtbar.
        footer = base.ttk.Frame(outer)
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)

        status = base.tk.StringVar(value="Bereit")
        base.ttk.Label(
            footer,
            textvariable=status,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10))

        buttons = base.ttk.Frame(footer)
        buttons.grid(row=0, column=1, sticky="e")

        def rebuild_prompt():
            prompt_text.delete("1.0", "end")
            prompt_text.insert("1.0", self.build_image_prompt())
            prompt_text.see("1.0")
            status.set("Prompt wurde neu aus dem Artikel gebildet.")

        def copy_prompt():
            prompt = prompt_text.get("1.0", "end").strip()
            if not prompt:
                base.messagebox.showwarning(
                    "Prompt fehlt",
                    "Bitte zuerst eine Bildbeschreibung eintragen.",
                    parent=window,
                )
                return
            self.clipboard_clear()
            self.clipboard_append(prompt)
            self.update()
            status.set("Prompt wurde in die Zwischenablage kopiert.")

        def save_prompt():
            prompt = prompt_text.get("1.0", "end").strip()
            if not prompt:
                return

            default_name = f"{image_id}_bildprompt.txt"
            target = base.filedialog.asksaveasfilename(
                parent=window,
                title="Bildprompt speichern",
                initialfile=default_name,
                defaultextension=".txt",
                filetypes=[("Textdatei", "*.txt"), ("Alle Dateien", "*.*")],
            )
            if not target:
                return

            Path(target).write_text(prompt + "\n", encoding="utf-8")
            status.set(f"Prompt gespeichert: {Path(target).name}")

        base.ttk.Button(
            buttons,
            text="Neu bilden",
            command=rebuild_prompt,
        ).pack(side="left", padx=(0, 6))

        base.ttk.Button(
            buttons,
            text="Als TXT speichern",
            command=save_prompt,
        ).pack(side="left", padx=(0, 6))

        base.ttk.Button(
            buttons,
            text="Prompt kopieren",
            command=copy_prompt,
        ).pack(side="left", padx=(0, 6))

        base.ttk.Button(
            buttons,
            text="Bild übernehmen …",
            command=lambda: self.import_article_image(parent=window),
        ).pack(side="left", padx=(0, 6))

        base.ttk.Button(
            buttons,
            text="Schließen",
            command=window.destroy,
        ).pack(side="left")

        # Tastaturkürzel für kompakte Bedienung.
        window.bind("<Escape>", lambda _event: window.destroy())
        window.bind("<Control-c>", lambda _event: copy_prompt())
        window.after_idle(lambda: self._fit_and_center(window, self))


if __name__ == "__main__":
    NewsStudio33().mainloop()
