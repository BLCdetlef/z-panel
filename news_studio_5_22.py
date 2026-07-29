#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.22 – Kurztitel für die Themenauswahl."""

import importlib.util
import json
import sys
from pathlib import Path
from tkinter import messagebox

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_21.py"

if not BASE_SCRIPT.exists():
    raise SystemExit("news_studio_5_21.py wurde nicht gefunden.")

spec = importlib.util.spec_from_file_location("news_studio_5_21_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("News Studio 5.21 konnte nicht geladen werden.")

base522 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base522
spec.loader.exec_module(base522)

tk = base522.tk
ttk = base522.ttk


def clean(value):
    return " ".join(str(value or "").strip().split())


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("Artikeldatei enthält kein JSON-Objekt.")
    return value


def write_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


class NewsStudio522(base522.NewsStudio521):
    def __init__(self):
        self._selection_label_ready = False
        super().__init__()
        self.title("ZUSTAND News Studio 5.22")
        self._replace_widget_text("ZUSTAND News Studio 5.21", "ZUSTAND News Studio 5.22")
        self.after_idle(self._install_selection_label_editor)
        self.status_var.set("News Studio 5.22 bereit │ Kurztitel für vorhandene Grundlagen")

    def _install_selection_label_editor(self):
        if self._selection_label_ready:
            return
        tab = getattr(self, "playback_tab", None)
        if tab is None:
            self.after(250, self._install_selection_label_editor)
            return

        box = ttk.LabelFrame(tab, text="Kurztitel der ausgewählten Grundlage", padding=8)
        box.pack(fill="x", pady=(10, 0))
        row = ttk.Frame(box)
        row.pack(fill="x")

        ttk.Label(row, text="Themenauswahl:").pack(side="left")
        self.selection_label_var = tk.StringVar()
        self.selection_label_entry = ttk.Entry(row, textvariable=self.selection_label_var, width=32)
        self.selection_label_entry.pack(side="left", padx=(8, 8))
        self.selection_label_entry.configure(state="disabled")

        self.selection_label_save_button = ttk.Button(
            row, text="Kurztitel speichern", command=self._save_selection_label, state="disabled"
        )
        self.selection_label_save_button.pack(side="left")

        self.selection_label_hint_var = tk.StringVar(
            value="Eine Grundlage auswählen. Ohne Kurztitel wird ihr vollständiger Titel verwendet."
        )
        ttk.Label(box, textvariable=self.selection_label_hint_var, wraplength=1050).pack(
            anchor="w", pady=(6, 0)
        )

        self.playback_tree.bind("<<TreeviewSelect>>", self._on_selection_label_selection, add="+")
        self.selection_label_entry.bind("<Return>", lambda _event: self._save_selection_label())
        self._selection_label_ready = True

    def _selected_explainer_record(self):
        try:
            _item_id, meta = self._selected_meta()
        except Exception:
            return None
        if not meta:
            return None
        record = self._playback_records.get(meta.get("id", ""))
        if not record or record.get("contentType") != "explainer":
            return None
        return record

    def _on_selection_label_selection(self, _event=None):
        if not self._selection_label_ready:
            return
        record = self._selected_explainer_record()
        if record is None:
            self.selection_label_var.set("")
            self.selection_label_entry.configure(state="disabled")
            self.selection_label_save_button.configure(state="disabled")
            self.selection_label_hint_var.set("Bitte eine Grundlage auswählen.")
            return

        article = record.get("article") or {}
        label = clean(article.get("selectionLabel"))
        self.selection_label_var.set(label)
        self.selection_label_entry.configure(state="normal")
        self.selection_label_save_button.configure(state="normal")
        self.selection_label_hint_var.set(
            "Vorschau: " + (label or record.get("title", record.get("id", "")))
        )

    def _save_selection_label(self):
        record = self._selected_explainer_record()
        if record is None:
            return
        path = Path(record["path"])
        try:
            article = read_json(path)
            label = clean(self.selection_label_var.get())
            if label:
                article["selectionLabel"] = label
            else:
                article.pop("selectionLabel", None)
            write_json(path, article)
        except Exception as exc:
            messagebox.showerror("Kurztitel konnte nicht gespeichert werden", str(exc), parent=self)
            return

        record["article"] = article
        self.selection_label_hint_var.set(
            "Gespeichert. Vorschau: " + (label or record.get("title", record.get("id", "")))
        )
        self.status_var.set("Kurztitel gespeichert │ " + record.get("id", ""))


if __name__ == "__main__":
    NewsStudio522().mainloop()
