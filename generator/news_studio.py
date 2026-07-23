#!/usr/bin/env python3
from __future__ import annotations

import json
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, ttk
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REDAKTION = PROJECT_ROOT / "newsredaktion"
ARTIKEL = REDAKTION / "artikel"
QUELLEN = REDAKTION / "quellen"
BILDER = PROJECT_ROOT / "assets" / "images"
OUTPUT = PROJECT_ROOT / "news.json"

REQUIRED_ARTICLE_FIELDS = [
    "id",
    "status",
    "title",
    "summary",
    "planetaryBoundary",
    "imageId",
    "sourceId",
    "publicationDate",
    "language",
    "article",
]

ALLOWED_STATUS = {"freigegeben", "veroeffentlicht"}


def relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path):
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise ValueError(f"Datei fehlt: {relative(path)}")

    if not raw.strip():
        raise ValueError(f"Datei ist leer: {relative(path)}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Ungültiges JSON in {relative(path)} "
            f"(Zeile {exc.lineno}, Spalte {exc.colno})"
        )


def valid_url(value: str) -> bool:
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def json_files(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(
        path
        for path in folder.glob("*.json")
        if path.name.lower() != "index.json"
        and not path.name.lower().endswith("_vorlage.json")
    )


def find_image_files(image_id: str):
    if not image_id or not BILDER.exists():
        return [], []

    images = []
    metadata = []

    for path in BILDER.iterdir():
        if not path.is_file() or not path.name.startswith(image_id + "_"):
            continue

        if path.suffix.lower() == ".json":
            metadata.append(path)
        elif path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            images.append(path)

    return sorted(images), sorted(metadata)


def collect_counts() -> dict[str, int]:
    article_files = json_files(ARTIKEL)
    source_files = json_files(QUELLEN)

    image_count = 0
    metadata_count = 0

    if BILDER.exists():
        for path in BILDER.iterdir():
            if not path.is_file():
                continue
            if path.suffix.lower() == ".json":
                metadata_count += 1
            elif path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                image_count += 1

    return {
        "articles": len(article_files),
        "sources": len(source_files),
        "images": image_count,
        "metadata": metadata_count,
    }


def validate_article(article: dict, path: Path, source_ids: set[str]) -> list[str]:
    errors = []
    label = relative(path)

    for field in REQUIRED_ARTICLE_FIELDS:
        value = article.get(field)
        if value in ("", None, []):
            errors.append(f"{label}: Pflichtfeld '{field}' fehlt.")

    sections = article.get("article")
    if not isinstance(sections, list) or not sections:
        errors.append(
            f"{label}: 'article' muss mindestens einen Textabschnitt enthalten."
        )
    elif not any(
        isinstance(section, dict) and section.get("text", "").strip()
        for section in sections
    ):
        errors.append(f"{label}: Alle Textabschnitte sind leer.")

    if article.get("status") not in ALLOWED_STATUS:
        errors.append(
            f"{label}: Status muss 'freigegeben' oder 'veroeffentlicht' sein."
        )

    source_id = str(article.get("sourceId", "")).strip()
    if source_id and source_id not in source_ids:
        errors.append(f"{label}: Quelle '{source_id}' wurde nicht gefunden.")

    if not valid_url(str(article.get("sourceUrl", ""))):
        errors.append(f"{label}: 'sourceUrl' enthält keine gültige Webadresse.")

    image_id = str(article.get("imageId", "")).strip()
    if image_id:
        image_files, metadata_files = find_image_files(image_id)

        if not image_files:
            errors.append(f"{label}: Kein Bild zu imageId '{image_id}' gefunden.")
        elif len(image_files) > 1:
            errors.append(f"{label}: Mehrere Bilddateien zu '{image_id}' gefunden.")

        if not metadata_files:
            errors.append(
                f"{label}: Keine Bild-Metadatendatei zu '{image_id}' gefunden."
            )
        elif len(metadata_files) > 1:
            errors.append(
                f"{label}: Mehrere Bild-Metadatendateien zu '{image_id}' gefunden."
            )

    return errors


def build_news() -> tuple[bool, list[str], dict[str, int]]:
    errors: list[str] = []
    messages: list[str] = []
    counts = collect_counts()

    source_ids: set[str] = set()

    for source_path in json_files(QUELLEN):
        try:
            source = load_json(source_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        source_id = str(source.get("id", "")).strip()

        if not source_id:
            errors.append(f"{relative(source_path)}: Feld 'id' fehlt.")
        elif source_id in source_ids:
            errors.append(
                f"{relative(source_path)}: Doppelte Quellen-ID '{source_id}'."
            )
        else:
            source_ids.add(source_id)

    compiled = []
    seen_ids: set[str] = set()

    for article_path in json_files(ARTIKEL):
        try:
            article = load_json(article_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        article_id = str(article.get("id", "")).strip()

        if article_id and article_id in seen_ids:
            errors.append(
                f"{relative(article_path)}: Doppelte Artikel-ID '{article_id}'."
            )
        elif article_id:
            seen_ids.add(article_id)

        errors.extend(validate_article(article, article_path, source_ids))

        image_files, metadata_files = find_image_files(
            str(article.get("imageId", "")).strip()
        )

        image_metadata = None
        if len(metadata_files) == 1:
            try:
                image_metadata = load_json(metadata_files[0])
            except ValueError as exc:
                errors.append(str(exc))

        output_article = dict(article)
        output_article["imageFile"] = (
            image_files[0].relative_to(PROJECT_ROOT).as_posix()
            if len(image_files) == 1
            else ""
        )
        output_article["imageMetadata"] = image_metadata
        compiled.append(output_article)

    if errors:
        messages.append("Prüfung abgebrochen. news.json wurde nicht verändert.")
        return False, errors + ["", *messages], counts

    compiled.sort(
        key=lambda article: (
            article.get("publicationDate", ""),
            article.get("id", ""),
        ),
        reverse=True,
    )

    payload = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "articleCount": len(compiled),
        "articles": compiled,
    }

    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    messages.extend(
        [
            f"{len(source_ids)} Quelle(n) geprüft.",
            f"{len(compiled)} Artikel geprüft.",
            f"news.json erfolgreich erzeugt: {relative(OUTPUT)}",
        ]
    )
    return True, messages, counts


class NewsStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio")
        self.geometry("820x600")
        self.minsize(700, 500)

        self.status_var = tk.StringVar(value="Bereit")
        self.count_vars = {
            "articles": tk.StringVar(value="0"),
            "sources": tk.StringVar(value="0"),
            "images": tk.StringVar(value="0"),
            "metadata": tk.StringVar(value="0"),
        }

        self._build_ui()
        self.refresh_counts()

    def _build_ui(self):
        header = ttk.Frame(self, padding=(18, 16))
        header.pack(fill="x")

        ttk.Label(
            header,
            text="ZUSTAND News Studio",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            header,
            text="Artikel, Quellen und Bildmetadaten prüfen und news.json erzeugen",
        ).pack(anchor="w", pady=(3, 0))

        stats = ttk.LabelFrame(self, text="Projektübersicht", padding=14)
        stats.pack(fill="x", padx=18, pady=(0, 12))

        items = [
            ("Artikel", "articles"),
            ("Quellen", "sources"),
            ("Bilder", "images"),
            ("Bildmetadaten", "metadata"),
        ]

        for column, (label, key) in enumerate(items):
            frame = ttk.Frame(stats, padding=(10, 4))
            frame.grid(row=0, column=column, sticky="nsew")
            stats.columnconfigure(column, weight=1)

            ttk.Label(
                frame,
                textvariable=self.count_vars[key],
                font=("Segoe UI", 18, "bold"),
            ).pack()
            ttk.Label(frame, text=label).pack()

        controls = ttk.Frame(self, padding=(18, 0))
        controls.pack(fill="x")

        self.run_button = ttk.Button(
            controls,
            text="News prüfen und erzeugen",
            command=self.run_generator,
        )
        self.run_button.pack(side="left")

        ttk.Button(
            controls,
            text="Übersicht aktualisieren",
            command=self.refresh_counts,
        ).pack(side="left", padx=(8, 0))

        ttk.Button(
            controls,
            text="Projektordner öffnen",
            command=self.open_project_folder,
        ).pack(side="left", padx=(8, 0))

        log_frame = ttk.LabelFrame(self, text="Prüfbericht", padding=10)
        log_frame.pack(fill="both", expand=True, padx=18, pady=12)

        self.log = tk.Text(
            log_frame,
            wrap="word",
            font=("Consolas", 10),
            state="disabled",
        )
        scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.log.yview,
        )
        self.log.configure(yscrollcommand=scrollbar.set)
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        footer = ttk.Frame(self, padding=(18, 0, 18, 14))
        footer.pack(fill="x")
        ttk.Label(footer, textvariable=self.status_var).pack(anchor="w")

    def set_log(self, lines: list[str]):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")

        for line in lines:
            self.log.insert("end", line + "\n")

        self.log.configure(state="disabled")
        self.log.see("end")

    def refresh_counts(self):
        counts = collect_counts()
        for key, value in counts.items():
            self.count_vars[key].set(str(value))
        self.status_var.set("Projektübersicht aktualisiert")

    def run_generator(self):
        self.run_button.configure(state="disabled")
        self.status_var.set("Prüfung läuft …")
        self.update_idletasks()

        try:
            success, lines, counts = build_news()
        except Exception as exc:
            success = False
            lines = [f"Unerwarteter Fehler: {exc}"]
            counts = collect_counts()

        for key, value in counts.items():
            self.count_vars[key].set(str(value))

        prefix = "ERFOLG" if success else "FEHLER"
        self.set_log([prefix, "=" * len(prefix), "", *lines])

        self.status_var.set(
            "news.json wurde erzeugt" if success else "Fehler gefunden"
        )
        self.run_button.configure(state="normal")

        if success:
            messagebox.showinfo(
                "ZUSTAND News Studio",
                "Die Prüfung war erfolgreich. news.json wurde erzeugt.",
            )
        else:
            messagebox.showwarning(
                "ZUSTAND News Studio",
                "Es wurden Fehler gefunden. Einzelheiten stehen im Prüfbericht.",
            )

    def open_project_folder(self):
        try:
            import os
            os.startfile(PROJECT_ROOT)
        except Exception as exc:
            messagebox.showerror(
                "Ordner konnte nicht geöffnet werden",
                str(exc),
            )


if __name__ == "__main__":
    app = NewsStudio()
    app.mainloop()
