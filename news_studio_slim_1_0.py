#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import tkinter as tk
from datetime import date, datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REDAKTION = PROJECT_ROOT / "newsredaktion"
ARTIKEL = REDAKTION / "artikel"
ENTWUERFE = REDAKTION / "entwuerfe"
QUELLEN = REDAKTION / "quellen"
VORLAGEN = REDAKTION / "vorlagen"
BILDER = PROJECT_ROOT / "assets" / "images"
OUTPUT = PROJECT_ROOT / "news.json"

for folder in (ARTIKEL, ENTWUERFE, QUELLEN, VORLAGEN, BILDER):
    folder.mkdir(parents=True, exist_ok=True)

BOUNDARIES = ["KL", "BD", "LN", "FW", "NP", "OA", "OZ", "AE", "NS"]
ARTICLE_STATUSES = ["entwurf", "freigegeben", "veroeffentlicht", "archiviert"]

ZUSTAND_IMAGE_STYLE = (
    "Fotorealistische, natürlich wirkende redaktionelle Fotografie für ein "
    "hochwertiges deutschsprachiges Wissenschaftsmagazin. Ruhige, glaubwürdige "
    "Bildsprache, natürliches Licht, klare Komposition, realistische Materialien "
    "und Hauttöne, dezente Tiefenschärfe. Ein einziges starkes Hauptmotiv mit "
    "verständlicher symbolischer Beziehung zum Artikel. Keine Katastrophenästhetik, "
    "keine übertriebene Dramatik, keine Collage, keine geteilte Ansicht, keine "
    "Diagramme, keine Infografik, keine Schrift, keine Buchstaben, keine Zahlen, "
    "keine Logos und keine Wasserzeichen. Für einen breiten 16:9-Infoscreen; "
    "wichtige Motive nicht direkt am Rand platzieren."
)

BOUNDARY_IMAGE_HINTS = {
    "KL": "Hitze, Sonne, blauer Himmel, Thermometer, körperliche Hitzebelastung",
    "BD": "lebendige Artenvielfalt, Wildpflanzen, Insekten, Vögel, Wald oder Gewässer",
    "LN": "Landschaft, Wald, Landwirtschaft, Versiegelung und Nutzungskonflikte",
    "FW": "Wasser, Fluss, trockener Boden, Regen, Trinkwasser oder Vegetation",
    "NP": "Landwirtschaft, Nährstoffe, Algenblüte, Ackerboden oder Gewässer",
    "OA": "Meer, Muschel, Koralle, Plankton oder empfindliches Meeresleben",
    "OZ": "Atmosphäre, Sonnenlicht und Schutzwirkung der Ozonschicht",
    "AE": "Luft, feine Partikel, Dunst, Stadt und Atemwege",
    "NS": "Kunststoffe, Chemikalien, Labor, Alltagsprodukte oder Mikroplastik",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path):
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise ValueError(f"Datei fehlt: {rel(path)}")
    if not raw.strip():
        raise ValueError(f"Datei ist leer: {rel(path)}")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Ungültiges JSON in {rel(path)} "
            f"(Zeile {exc.lineno}, Spalte {exc.colno})"
        )


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def json_files(folder: Path) -> list[Path]:
    return sorted(
        p for p in folder.glob("*.json")
        if p.name.lower() != "index.json"
        and not p.name.lower().endswith("_vorlage.json")
    )


def slug(text: str) -> str:
    table = str.maketrans({
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
    })
    text = text.translate(table).lower()
    chars = []
    previous_underscore = False
    for char in text:
        if char.isalnum():
            chars.append(char)
            previous_underscore = False
        elif not previous_underscore:
            chars.append("_")
            previous_underscore = True
    return "".join(chars).strip("_")[:60] or "beitrag"


def valid_url(value: str) -> bool:
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def image_matches(image_id: str):
    images, metadata = [], []
    if not image_id:
        return images, metadata
    for path in BILDER.iterdir():
        if not path.is_file() or not path.name.startswith(image_id + "_"):
            continue
        if path.suffix.lower() == ".json":
            metadata.append(path)
        elif path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            images.append(path)
    return sorted(images), sorted(metadata)


def collect_counts():
    images = 0
    metadata = 0
    for p in BILDER.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() == ".json":
            metadata += 1
        elif p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            images += 1
    return {
        "drafts": len(json_files(ENTWUERFE)),
        "articles": len(json_files(ARTIKEL)),
        "sources": len(json_files(QUELLEN)),
        "images": images,
        "metadata": metadata,
    }


def validate_and_build():
    errors = []
    source_ids = set()

    for path in json_files(QUELLEN):
        try:
            source = read_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        sid = str(source.get("id", "")).strip()
        if not sid:
            errors.append(f"{rel(path)}: Feld 'id' fehlt.")
        elif sid in source_ids:
            errors.append(f"{rel(path)}: Doppelte Quellen-ID '{sid}'.")
        else:
            source_ids.add(sid)

    compiled = []
    seen_ids = set()
    for path in json_files(ARTIKEL):
        try:
            article = read_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        aid = str(article.get("id", "")).strip()
        required = [
            "id", "title", "summary", "planetaryBoundary", "imageId",
            "sourceUrl", "publicationDate", "language"
        ]
        for field in required:
            if article.get(field) in ("", None, []):
                errors.append(f"{rel(path)}: Pflichtfeld '{field}' fehlt.")

        if aid in seen_ids:
            errors.append(f"{rel(path)}: Doppelte Artikel-ID '{aid}'.")
        seen_ids.add(aid)

        if article.get("status") not in {"freigegeben", "veroeffentlicht"}:
            errors.append(
                f"{rel(path)}: Status muss 'freigegeben' oder "
                f"'veroeffentlicht' sein."
            )

        sid = str(article.get("sourceId", "")).strip()
        if sid and sid not in source_ids:
            errors.append(f"{rel(path)}: Quelle '{sid}' wurde nicht gefunden.")

        source_url = str(article.get("sourceUrl", "")).strip()
        if not source_url:
            errors.append(f"{rel(path)}: Quellen-URL fehlt.")
        elif not valid_url(source_url):
            errors.append(f"{rel(path)}: sourceUrl ist ungültig.")

        image_id = str(article.get("imageId", "")).strip()
        images, metas = image_matches(image_id)
        if len(images) != 1:
            errors.append(
                f"{rel(path)}: Zu imageId '{image_id}' wurde "
                f"{len(images)} Bilddatei(en) gefunden."
            )
        if len(metas) != 1:
            errors.append(
                f"{rel(path)}: Zu imageId '{image_id}' wurde "
                f"{len(metas)} Metadatendatei(en) gefunden."
            )

        item = dict(article)
        item["imageFile"] = (
            images[0].relative_to(PROJECT_ROOT).as_posix()
            if len(images) == 1 else ""
        )
        item["imageMetadata"] = (
            read_json(metas[0]) if len(metas) == 1 else None
        )
        compiled.append(item)

    if errors:
        return False, errors

    compiled.sort(
        key=lambda a: (a.get("publicationDate", ""), a.get("id", "")),
        reverse=True,
    )
    payload = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "articleCount": len(compiled),
        "articles": compiled,
    }
    write_json(OUTPUT, payload)
    return True, [
        f"{len(source_ids)} Quelle(n) geprüft.",
        f"{len(compiled)} Artikel geprüft.",
        f"{rel(OUTPUT)} erfolgreich erzeugt.",
    ]


class FieldRow(ttk.Frame):
    def __init__(self, parent, label, variable=None, width=60):
        super().__init__(parent)
        ttk.Label(self, text=label, width=20).pack(side="left", anchor="n")
        self.entry = ttk.Entry(self, textvariable=variable, width=width)
        self.entry.pack(side="left", fill="x", expand=True)
        self.pack(fill="x", pady=3)


class NewsStudio(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio Slim 1.0")
        self.geometry("1080x720")
        self.minsize(880, 540)

        self.current_article_path = None
        self.current_source_path = None

        self._build()
        self.refresh_all()

    def _build(self):
        header = ttk.Frame(self, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(
            header, text="ZUSTAND News Studio Slim 1.0",
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Kurzmeldungen, Quellenlinks und Titelbilder für den Infoscreen verwalten"
        ).pack(anchor="w")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.overview_tab = ttk.Frame(self.tabs)
        self.article_tab = ttk.Frame(self.tabs)
        self.source_tab = ttk.Frame(self.tabs)
        self.image_tab = ttk.Frame(self.tabs)
        self.generator_tab = ttk.Frame(self.tabs)

        self.tabs.add(self.overview_tab, text="Übersicht")
        self.tabs.add(self.article_tab, text="Artikel")
        self.tabs.add(self.image_tab, text="Bilder")
        self.tabs.add(self.generator_tab, text="Generator")

        self._build_overview()
        self._build_articles()
        self._build_sources()
        self._build_images()
        self._build_generator()

        self.status_var = tk.StringVar(value="Bereit")
        self.status_bar = ttk.Label(
            self, textvariable=self.status_var, anchor="w", relief="sunken",
            padding=(8, 4)
        )
        self.status_bar.pack(fill="x", side="bottom")

    def _build_overview(self):
        outer = ttk.Frame(self.overview_tab, padding=18)
        outer.pack(fill="both", expand=True)

        self.count_vars = {k: tk.StringVar(value="0") for k in
                           ("drafts", "articles", "sources", "images", "metadata")}
        labels = [
            ("Entwürfe", "drafts"),
            ("Freigegebene Artikel", "articles"),
            ("Bilder", "images"),
            ("Bildmetadaten", "metadata"),
        ]
        cards = ttk.Frame(outer)
        cards.pack(fill="x")
        for i, (label, key) in enumerate(labels):
            card = ttk.LabelFrame(cards, text=label, padding=16)
            card.grid(row=0, column=i, padx=5, sticky="nsew")
            cards.columnconfigure(i, weight=1)
            ttk.Label(
                card, textvariable=self.count_vars[key],
                font=("Segoe UI", 22, "bold")
            ).pack()

        actions = ttk.LabelFrame(outer, text="Schnellzugriff", padding=16)
        actions.pack(fill="x", pady=18)
        ttk.Button(
            actions, text="Neuen Artikel anlegen",
            command=self.new_article
        ).pack(side="left")
        ttk.Button(
            actions, text="News prüfen und erzeugen",
            command=self.run_generator
        ).pack(side="left")
        ttk.Button(
            actions, text="Projektordner öffnen",
            command=lambda: os.startfile(PROJECT_ROOT)
        ).pack(side="left", padx=8)

        info = ttk.LabelFrame(outer, text="Arbeitsweise", padding=16)
        info.pack(fill="both", expand=True)
        text = (
            "1. Titel, Kurztext, planetare Grenze und Quellenlink eintragen.\n"
            "2. Bild-ID vergeben und einen Bildprompt vorbereiten.\n"
            "3. Bild in ChatGPT erzeugen und über „Bild übernehmen“ einfügen.\n"
            "4. Meldung freigeben und news.json erzeugen.\n"
            "5. Änderungen mit GitHub Desktop committen und pushen."
        )
        ttk.Label(info, text=text, justify="left").pack(anchor="w")

    def _build_articles(self):
        paned = ttk.Panedwindow(self.article_tab, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(paned, padding=6)
        right = ttk.Frame(paned, padding=8)
        paned.add(left, weight=1)
        paned.add(right, weight=3)

        ttk.Label(left, text="Artikel und Entwürfe",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.article_list = ttk.Treeview(
            left, columns=("status", "id", "title"), show="headings",
            selectmode="browse"
        )
        self.article_list.heading("status", text="Status")
        self.article_list.heading("id", text="ID")
        self.article_list.heading("title", text="Titel")
        self.article_list.column("status", width=105, anchor="w", stretch=False)
        self.article_list.column("id", width=90, anchor="w", stretch=False)
        self.article_list.column("title", width=280, anchor="w")
        self.article_list.pack(fill="both", expand=True, pady=6)
        self.article_list.bind("<<TreeviewSelect>>", self.load_selected_article)
        self.article_list.bind("<Double-1>", self.load_selected_article)

        btns = ttk.Frame(left)
        btns.pack(fill="x")
        ttk.Button(btns, text="Neu", command=self.new_article).pack(side="left")
        ttk.Button(btns, text="Aktualisieren",
                   command=self.refresh_article_list).pack(side="left", padx=5)

        self.article_vars = {
            "id": tk.StringVar(),
            "status": tk.StringVar(value="entwurf"),
            "title": tk.StringVar(),
            "subtitle": tk.StringVar(),
            "summary": tk.StringVar(),
            "planetaryBoundary": tk.StringVar(),
            "keywords": tk.StringVar(),
            "imageId": tk.StringVar(),
            "sourceId": tk.StringVar(),
            "sourceTitle": tk.StringVar(),
            "sourceUrl": tk.StringVar(),
            "publicationDate": tk.StringVar(value=date.today().isoformat()),
            "author": tk.StringVar(),
            "editor": tk.StringVar(),
        }

        editor_area = ttk.Frame(right)
        editor_area.pack(fill="both", expand=True)

        form_canvas = tk.Canvas(editor_area, highlightthickness=0)
        scrollbar = ttk.Scrollbar(editor_area, orient="vertical",
                                  command=form_canvas.yview)
        form = ttk.Frame(form_canvas)
        form_window = form_canvas.create_window((0, 0), window=form, anchor="nw")

        def update_scrollregion(_event=None):
            form_canvas.configure(scrollregion=form_canvas.bbox("all"))

        def fit_form_width(event):
            form_canvas.itemconfigure(form_window, width=event.width)

        form.bind("<Configure>", update_scrollregion)
        form_canvas.bind("<Configure>", fit_form_width)
        form_canvas.configure(yscrollcommand=scrollbar.set)
        form_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def mousewheel(event):
            form_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        form_canvas.bind_all("<MouseWheel>", mousewheel)

        ttk.Label(form, text="Artikel bearbeiten",
                  font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))

        FieldRow(form, "ID", self.article_vars["id"])
        status_row = ttk.Frame(form)
        ttk.Label(status_row, text="Status", width=20).pack(side="left")
        ttk.Combobox(
            status_row, textvariable=self.article_vars["status"],
            values=ARTICLE_STATUSES, state="readonly"
        ).pack(side="left", fill="x", expand=True)
        status_row.pack(fill="x", pady=3)

        FieldRow(form, "Titel", self.article_vars["title"])
        ttk.Label(form, text="Kurztext für den Infoscreen").pack(anchor="w", pady=(10, 3))
        self.summary_text = tk.Text(form, height=7, wrap="word")
        self.summary_text.pack(fill="x")

        pb_row = ttk.Frame(form)
        ttk.Label(pb_row, text="Planetare Grenze", width=20).pack(side="left")
        ttk.Combobox(
            pb_row, textvariable=self.article_vars["planetaryBoundary"],
            values=BOUNDARIES
        ).pack(side="left", fill="x", expand=True)
        pb_row.pack(fill="x", pady=3)

        FieldRow(form, "Schlagwörter", self.article_vars["keywords"])
        FieldRow(form, "Bild-ID", self.article_vars["imageId"])

        image_ai_row = ttk.Frame(form)
        ttk.Label(image_ai_row, text="", width=20).pack(side="left")
        ttk.Button(
            image_ai_row,
            text="Bildprompt vorbereiten …",
            command=self.open_image_workflow,
        ).pack(side="left")
        ttk.Button(
            image_ai_row,
            text="Bild übernehmen …",
            command=self.import_article_image,
        ).pack(side="left", padx=(6, 0))
        ttk.Button(
            image_ai_row,
            text="Bild anzeigen",
            command=self.open_article_image,
        ).pack(side="left", padx=(6, 0))
        self.image_ai_status = ttk.Label(image_ai_row, text="")
        self.image_ai_status.pack(side="left", padx=10)
        image_ai_row.pack(fill="x", pady=(1, 7))

        FieldRow(form, "Quellen-URL", self.article_vars["sourceUrl"])
        FieldRow(form, "Veröffentlichungsdatum",
                 self.article_vars["publicationDate"])

        # Feste Schaltflächenleiste: bleibt auch auf kleinen Bildschirmen sichtbar.
        actionbar = ttk.Frame(right, padding=(0, 8, 0, 0))
        actionbar.pack(fill="x", side="bottom")
        ttk.Separator(actionbar, orient="horizontal").pack(fill="x", pady=(0, 8))
        buttons = ttk.Frame(actionbar)
        buttons.pack(fill="x")
        ttk.Button(
            buttons, text="Als Entwurf speichern",
            command=lambda: self.save_article("entwurf")
        ).pack(side="left")
        ttk.Button(
            buttons, text="Speichern",
            command=self.save_article_current_status
        ).pack(side="left", padx=6)
        ttk.Button(
            buttons, text="Freigeben und verschieben",
            command=lambda: self.save_article("freigegeben")
        ).pack(side="left")
        ttk.Button(
            buttons, text="Datei löschen",
            command=self.delete_article
        ).pack(side="right")

    def _build_sources(self):
        paned = ttk.Panedwindow(self.source_tab, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=10)
        left = ttk.Frame(paned, padding=6)
        right = ttk.Frame(paned, padding=8)
        paned.add(left, weight=1)
        paned.add(right, weight=3)

        ttk.Label(left, text="Quellen",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w")
        self.source_list = tk.Listbox(left, exportselection=False)
        self.source_list.pack(fill="both", expand=True, pady=6)
        self.source_list.bind("<<ListboxSelect>>", self.load_selected_source)
        ttk.Button(left, text="Neue Quelle",
                   command=self.new_source).pack(anchor="w")

        self.source_vars = {
            "id": tk.StringVar(),
            "name": tk.StringVar(),
            "shortName": tk.StringVar(),
            "website": tk.StringVar(),
            "country": tk.StringVar(),
            "type": tk.StringVar(),
            "trustLevel": tk.StringVar(value="high"),
        }
        ttk.Label(right, text="Quelle bearbeiten",
                  font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))
        for label, key in [
            ("ID", "id"), ("Name", "name"), ("Kurzname", "shortName"),
            ("Website", "website"), ("Land/Region", "country"),
            ("Typ", "type"), ("Vertrauensniveau", "trustLevel"),
        ]:
            FieldRow(right, label, self.source_vars[key])

        ttk.Label(right, text="Notizen").pack(anchor="w", pady=(10, 3))
        self.source_notes = tk.Text(right, height=8, wrap="word")
        self.source_notes.pack(fill="x")
        ttk.Button(right, text="Quelle speichern",
                   command=self.save_source).pack(anchor="w", pady=10)

    def _build_images(self):
        outer = ttk.Frame(self.image_tab, padding=12)
        outer.pack(fill="both", expand=True)

        toolbar = ttk.Frame(outer)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="Bildordner öffnen",
                   command=lambda: os.startfile(BILDER)).pack(side="left")
        ttk.Button(toolbar, text="Liste aktualisieren",
                   command=self.refresh_image_list).pack(side="left", padx=6)

        self.image_tree = ttk.Treeview(
            outer, columns=("type", "id", "file"), show="headings"
        )
        self.image_tree.heading("type", text="Typ")
        self.image_tree.heading("id", text="ID")
        self.image_tree.heading("file", text="Datei")
        self.image_tree.column("type", width=140)
        self.image_tree.column("id", width=130)
        self.image_tree.column("file", width=650)
        self.image_tree.pack(fill="both", expand=True, pady=10)


    def build_image_prompt(self) -> str:
        title = self.article_vars["title"].get().strip()
        summary = self.summary_text.get("1.0", "end").strip()
        boundary = self.article_vars["planetaryBoundary"].get().strip()
        keywords = self.article_vars["keywords"].get().strip()
        hint = BOUNDARY_IMAGE_HINTS.get(
            boundary,
            "eine natürliche, leicht verständliche Assoziation zum Artikel",
        )

        subject = (
            f"Erzeuge ein einzelnes Titelbild für einen öffentlichen Infoscreen.\n\n"
            f"Artikelthema: {title or 'noch ohne Titel'}.\n"
            f"Kernaussage: {summary or 'noch keine Kurzfassung'}.\n"
            f"Mögliche Bildassoziationen: {hint}."
        )
        if keywords:
            subject += f"\nSchlagwörter: {keywords}."

        return (
            f"{subject}\n\n"
            "Zeige keine konkrete Nachrichtenszene und erfinde kein dokumentarisches "
            "Ereignis. Entwickle stattdessen eine natürliche, glaubwürdige, "
            "fotorealistische Assoziation, die den Inhalt auf den ersten Blick "
            "verständlich macht. Menschen nur dann zeigen, wenn sie inhaltlich "
            "sinnvoll sind; dann respektvoll, alltäglich und nicht posierend.\n\n"
            f"Verbindliche ZUSTAND-Bildsprache: {ZUSTAND_IMAGE_STYLE}\n\n"
            "Ausgabe: ein einziges Bild im breiten Querformat für einen 16:9-Infoscreen."
        )

    def open_image_workflow(self):
        image_id = self.article_vars["imageId"].get().strip()
        if not image_id:
            messagebox.showwarning(
                "Bild-ID fehlt",
                "Bitte zuerst eine Bild-ID eintragen, zum Beispiel KL_0001_01."
            )
            return

        window = tk.Toplevel(self)
        window.title(f"Bildworkflow – {image_id}")
        window.geometry("940x690")
        window.minsize(740, 540)
        window.transient(self)

        outer = ttk.Frame(window, padding=16)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="ZUSTAND-Bildprompt",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Der Prompt wird aus dem Artikel gebildet. Kopiere ihn anschließend "
                "in ChatGPT, erzeuge dort ein Bild und übernimm die gespeicherte "
                "Bilddatei danach wieder in das News Studio."
            ),
            wraplength=880,
            justify="left",
        ).pack(anchor="w", pady=(2, 12))

        prompt_text = tk.Text(outer, wrap="word", height=22)
        prompt_text.pack(fill="both", expand=True)
        prompt_text.insert("1.0", self.build_image_prompt())

        status = tk.StringVar(value="Bereit")
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        ttk.Label(footer, textvariable=status).pack(side="left")

        buttons = ttk.Frame(footer)
        buttons.pack(side="right")

        def rebuild_prompt():
            prompt_text.delete("1.0", "end")
            prompt_text.insert("1.0", self.build_image_prompt())
            status.set("Prompt wurde neu aus dem Artikel gebildet.")

        def copy_prompt():
            prompt = prompt_text.get("1.0", "end").strip()
            if not prompt:
                messagebox.showwarning(
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
            target = filedialog.asksaveasfilename(
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

        ttk.Button(
            buttons,
            text="Aus Artikel neu bilden",
            command=rebuild_prompt,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            buttons,
            text="Als TXT speichern",
            command=save_prompt,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            buttons,
            text="Prompt kopieren",
            command=copy_prompt,
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            buttons,
            text="Bild übernehmen …",
            command=lambda: self.import_article_image(parent=window),
        ).pack(side="left")

    def import_article_image(self, parent=None):
        image_id = self.article_vars["imageId"].get().strip()
        if not image_id:
            messagebox.showwarning(
                "Bild-ID fehlt",
                "Bitte zuerst eine Bild-ID eintragen, zum Beispiel KL_0001_01.",
                parent=parent or self,
            )
            return

        selected = filedialog.askopenfilename(
            parent=parent or self,
            title="Erzeugtes Titelbild auswählen",
            filetypes=[
                ("Bilddateien", "*.png *.jpg *.jpeg *.webp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("WebP", "*.webp"),
                ("Alle Dateien", "*.*"),
            ],
        )
        if not selected:
            return

        source = Path(selected)
        if source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            messagebox.showerror(
                "Ungeeignete Datei",
                "Bitte eine PNG-, JPG-, JPEG- oder WebP-Datei auswählen.",
                parent=parent or self,
            )
            return

        existing_images, existing_metadata = image_matches(image_id)
        if existing_images or existing_metadata:
            replace = messagebox.askyesno(
                "Vorhandenes Titelbild ersetzen?",
                (
                    f"Für {image_id} existieren bereits "
                    f"{len(existing_images)} Bilddatei(en) und "
                    f"{len(existing_metadata)} Metadatendatei(en).\n\n"
                    "Sollen diese durch das ausgewählte Bild ersetzt werden?"
                ),
                parent=parent or self,
            )
            if not replace:
                return
            for path in existing_images + existing_metadata:
                path.unlink(missing_ok=True)

        suffix = ".jpg" if source.suffix.lower() == ".jpeg" else source.suffix.lower()
        target = BILDER / f"{image_id}_zustand{suffix}"
        shutil.copy2(source, target)

        title = self.article_vars["title"].get().strip()
        summary = self.summary_text.get("1.0", "end").strip()
        prompt = self.build_image_prompt()
        metadata_path = BILDER / f"{image_id}_zustand.json"
        metadata = {
            "id": image_id,
            "type": "ai-generated-or-editorial-image",
            "created": datetime.now(timezone.utc).isoformat(),
            "sourceFile": source.name,
            "prompt": prompt,
            "altText": summary or title or f"Symbolisches Titelbild zu {image_id}",
            "license": "Titelbild für ZUSTAND; Nutzungsrechte redaktionell prüfen",
            "editorialNote": (
                "Symbolisches Titelbild für den Infoscreen. "
                "Keine dokumentarische Aufnahme eines konkreten Ereignisses, "
                "sofern es KI-generiert wurde."
            ),
        }
        write_json(metadata_path, metadata)

        self.refresh_all()
        self.image_ai_status.configure(text="✓ Bild vorhanden")
        self.status_var.set(f"Titelbild {target.name} wurde übernommen.")

        messagebox.showinfo(
            "Titelbild übernommen",
            (
                f"Das Titelbild wurde richtig benannt und gespeichert.\n\n"
                f"Bild: {rel(target)}\n"
                f"Metadaten: {rel(metadata_path)}"
            ),
            parent=parent or self,
        )

        try:
            os.startfile(target)
        except OSError:
            pass

    def open_article_image(self):
        image_id = self.article_vars["imageId"].get().strip()
        if not image_id:
            messagebox.showinfo("Bild-ID fehlt", "Bitte zuerst eine Bild-ID eintragen.")
            return
        images, _ = image_matches(image_id)
        if len(images) != 1:
            messagebox.showinfo(
                "Bild nicht eindeutig",
                f"Für {image_id} wurden {len(images)} Bilddateien gefunden."
            )
            return
        try:
            os.startfile(images[0])
        except OSError as exc:
            messagebox.showerror("Bild konnte nicht geöffnet werden", str(exc))

    def _build_generator(self):
        outer = ttk.Frame(self.generator_tab, padding=16)
        outer.pack(fill="both", expand=True)

        buttons = ttk.Frame(outer)
        buttons.pack(fill="x")
        ttk.Button(
            buttons, text="News prüfen und erzeugen",
            command=self.run_generator
        ).pack(side="left")
        ttk.Button(
            buttons, text="news.json öffnen",
            command=self.open_news_json
        ).pack(side="left", padx=6)

        self.generator_log = tk.Text(
            outer, wrap="word", font=("Consolas", 10), state="disabled"
        )
        self.generator_log.pack(fill="both", expand=True, pady=12)

    def refresh_all(self):
        self.refresh_counts()
        self.refresh_article_list()
        self.refresh_source_list()
        self.refresh_image_list()

    def refresh_counts(self):
        counts = collect_counts()
        for key, value in counts.items():
            self.count_vars[key].set(str(value))

    def refresh_article_list(self):
        self.article_paths = {}
        for row in self.article_list.get_children():
            self.article_list.delete(row)

        status_labels = {
            "entwurf": "Entwurf",
            "freigegeben": "Freigegeben",
            "veroeffentlicht": "Veröffentlicht",
            "archiviert": "Archiviert",
        }

        for folder, fallback in [(ENTWUERFE, "entwurf"), (ARTIKEL, "freigegeben")]:
            for path in json_files(folder):
                try:
                    data = read_json(path)
                    status = str(data.get("status", fallback))
                    article_id = str(data.get("id", path.stem))
                    title = str(data.get("title", path.name))
                except Exception:
                    status = "fehler"
                    article_id = path.stem
                    title = "Datei nicht lesbar"

                item_id = self.article_list.insert(
                    "", "end",
                    values=(status_labels.get(status, status), article_id, title)
                )
                self.article_paths[item_id] = path

        counts = collect_counts()
        if hasattr(self, "status_var"):
            self.status_var.set(
                f"Bereit │ {counts['drafts']} Entwurf/Entwürfe │ "
                f"{counts['articles']} freigegebene Artikel"
            )

    def refresh_source_list(self):
        self.source_paths = json_files(QUELLEN)
        self.source_list.delete(0, "end")
        source_ids = []
        for path in self.source_paths:
            self.source_list.insert("end", path.name)
            try:
                source_ids.append(str(read_json(path).get("id", "")))
            except Exception:
                pass
        if hasattr(self, "article_source_combo"):
            self.article_source_combo["values"] = sorted(x for x in source_ids if x)

    def refresh_image_list(self):
        for row in self.image_tree.get_children():
            self.image_tree.delete(row)
        for path in sorted(BILDER.iterdir()):
            if not path.is_file():
                continue
            if path.suffix.lower() == ".json":
                typ = "Metadaten"
            elif path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                typ = "Bild"
            else:
                continue
            iid = path.stem.split("_", 2)
            image_id = "_".join(iid[:2]) if len(iid) >= 2 else path.stem
            self.image_tree.insert("", "end", values=(typ, image_id, path.name))

    def new_article(self):
        self.tabs.select(self.article_tab)
        self.current_article_path = None
        for var in self.article_vars.values():
            var.set("")
        self.article_vars["status"].set("entwurf")
        self.article_vars["publicationDate"].set(date.today().isoformat())
        self.summary_text.delete("1.0", "end")
        if hasattr(self, "image_ai_status"):
            self.image_ai_status.configure(text="")
        if hasattr(self, "status_var"):
            self.status_var.set("Neuer Artikel – noch nicht gespeichert")

    def load_selected_article(self, _event=None):
        selection = self.article_list.selection()
        if not selection:
            return
        path = self.article_paths.get(selection[0])
        if path is None:
            return
        try:
            data = read_json(path)
        except ValueError as exc:
            messagebox.showerror("Artikel konnte nicht geöffnet werden", str(exc))
            return
        self.current_article_path = path
        for key, var in self.article_vars.items():
            value = data.get(key, "")
            if key == "keywords" and isinstance(value, list):
                value = ", ".join(value)
            var.set(value)

        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", data.get("summary", ""))
        if hasattr(self, "image_ai_status"):
            images, metas = image_matches(str(data.get("imageId", "")).strip())
            self.image_ai_status.configure(
                text="✓ Bild vorhanden" if len(images) == 1 and len(metas) == 1
                else "Bild fehlt oder ist nicht eindeutig"
            )
        if hasattr(self, "status_var"):
            self.status_var.set(
                f"Geöffnet: {data.get('id', path.stem)} │ "
                f"Status: {data.get('status', 'unbekannt')}"
            )

    def article_payload(self, forced_status=None):
        status = forced_status or self.article_vars["status"].get() or "entwurf"
        article_id = self.article_vars["id"].get().strip()
        title = self.article_vars["title"].get().strip()
        if not article_id:
            raise ValueError("Bitte eine Artikel-ID eintragen.")
        if not title:
            raise ValueError("Bitte einen Titel eintragen.")
        summary = self.summary_text.get("1.0", "end").strip()
        if not summary:
            raise ValueError("Bitte einen Kurztext für den Infoscreen eintragen.")
        source_url = self.article_vars["sourceUrl"].get().strip()
        if not valid_url(source_url) or not source_url:
            raise ValueError("Bitte einen gültigen Quellenlink mit http:// oder https:// eintragen.")

        now = date.today().isoformat()
        created = now
        if self.current_article_path and self.current_article_path.exists():
            try:
                created = read_json(self.current_article_path).get("created", now)
            except Exception:
                pass

        return {
            "id": article_id,
            "status": status,
            "title": title,
            "subtitle": "",
            "summary": self.summary_text.get("1.0", "end").strip(),
            "planetaryBoundary":
                self.article_vars["planetaryBoundary"].get().strip(),
            "keywords": [
                x.strip() for x in self.article_vars["keywords"].get().split(",")
                if x.strip()
            ],
            "imageId": self.article_vars["imageId"].get().strip(),
            "sourceId": self.article_vars["sourceId"].get().strip(),
            "sourceTitle": "",
            "sourceUrl": self.article_vars["sourceUrl"].get().strip(),
            "publicationDate":
                self.article_vars["publicationDate"].get().strip(),
            "author": "",
            "editor": "",
            "created": created,
            "lastModified": now,
            "language": "de",
            "article": [],
            "facts": [],
            "links": [],
            "license": "",
            "notes": "",
        }

    def save_article_current_status(self):
        self.save_article(self.article_vars["status"].get() or "entwurf")

    def save_article(self, status):
        try:
            data = self.article_payload(status)
        except ValueError as exc:
            messagebox.showwarning("Angaben fehlen", str(exc))
            return

        target_folder = ENTWUERFE if status == "entwurf" else ARTIKEL
        filename = f"{data['id']}_{slug(data['title'])}.json"
        target = target_folder / filename

        if self.current_article_path and self.current_article_path != target:
            if self.current_article_path.exists():
                self.current_article_path.unlink()

        write_json(target, data)
        self.current_article_path = target
        self.article_vars["status"].set(status)
        self.refresh_all()
        action = (
            "freigegeben und in den Artikelordner verschoben"
            if status == "freigegeben"
            else "als Entwurf gespeichert"
            if status == "entwurf"
            else f"mit Status '{status}' gespeichert"
        )
        self.status_var.set(f"{data['id']} wurde {action}.")
        messagebox.showinfo(
            "Artikel erfolgreich gespeichert",
            f"{data['id']} wurde {action}.\n\nDatei: {rel(target)}"
        )

    def delete_article(self):
        if not self.current_article_path:
            return
        if messagebox.askyesno(
            "Artikel löschen",
            f"Soll {self.current_article_path.name} wirklich gelöscht werden?"
        ):
            self.current_article_path.unlink(missing_ok=True)
            self.new_article()
            self.refresh_all()

    def new_source(self):
        self.tabs.select(self.source_tab)
        self.current_source_path = None
        for var in self.source_vars.values():
            var.set("")
        self.source_vars["trustLevel"].set("high")
        self.source_notes.delete("1.0", "end")

    def load_selected_source(self, _event=None):
        selection = self.source_list.curselection()
        if not selection:
            return
        path = self.source_paths[selection[0]]
        try:
            data = read_json(path)
        except ValueError as exc:
            messagebox.showerror("Quelle konnte nicht geöffnet werden", str(exc))
            return
        self.current_source_path = path
        for key, var in self.source_vars.items():
            var.set(data.get(key, ""))
        self.source_notes.delete("1.0", "end")
        self.source_notes.insert("1.0", data.get("notes", ""))

    def save_source(self):
        sid = self.source_vars["id"].get().strip()
        name = self.source_vars["name"].get().strip()
        if not sid or not name:
            messagebox.showwarning(
                "Angaben fehlen", "Bitte mindestens ID und Name eintragen."
            )
            return
        data = {key: var.get().strip()
                for key, var in self.source_vars.items()}
        data["notes"] = self.source_notes.get("1.0", "end").strip()
        target = QUELLEN / f"{sid}.json"

        if self.current_source_path and self.current_source_path != target:
            self.current_source_path.unlink(missing_ok=True)
        write_json(target, data)
        self.current_source_path = target
        self.refresh_all()
        self.status_var.set(f"Quelle {sid} wurde gespeichert.")
        messagebox.showinfo(
            "Quelle erfolgreich gespeichert",
            f"Quelle {sid} wurde gespeichert.\n\nDatei: {rel(target)}"
        )

    def run_generator(self):
        self.tabs.select(self.generator_tab)
        success, lines = validate_and_build()
        self.generator_log.configure(state="normal")
        self.generator_log.delete("1.0", "end")
        self.generator_log.insert(
            "1.0",
            ("ERFOLG\n\n" if success else "FEHLER\n\n") + "\n".join(lines)
        )
        self.generator_log.configure(state="disabled")
        self.refresh_counts()
        if success:
            article_count = collect_counts()["articles"]
            self.status_var.set(
                f"Generator erfolgreich │ news.json mit {article_count} Artikel(n) erzeugt"
            )
            messagebox.showinfo(
                "Generator erfolgreich",
                f"news.json wurde erfolgreich mit {article_count} Artikel(n) erzeugt.\n\n"
                f"Datei: {rel(OUTPUT)}"
            )
        else:
            self.status_var.set("Generatorfehler – Details im Prüfbericht")
            messagebox.showwarning(
                "Generatorfehler",
                "Es wurden Fehler gefunden. Details stehen im Prüfbericht."
            )

    def open_news_json(self):
        if OUTPUT.exists():
            os.startfile(OUTPUT)
        else:
            messagebox.showinfo(
                "news.json fehlt",
                "Die Datei wurde noch nicht erzeugt."
            )


if __name__ == "__main__":
    NewsStudio().mainloop()
