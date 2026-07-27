#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.14 – steuerbare Recherchetypen.

Benötigt im selben Ordner:
- news_studio_5_13.py
- die korrigierte news_studio_5_12.py (Version 5.12.1)
- news_studio_5_11.py und die bisherigen Basisdateien

Neu:
- Recherche-Prompt mit vier Ausgabemodi:
  * Automatisch entscheiden
  * Nur News-Beiträge
  * News plus passende Warum-Beiträge
  * Nur Warum-/Grundlagenbeiträge
- dieselbe Auswahl für „Eigene Funde“
- vorhandene Grundlagen werden mit ID und Titel in den Prompt aufgenommen
- neue News-Grundlagen-Paare werden nach dem Import automatisch verknüpft
- Import-Schlüssel werden in echte explainerId-Verweise übersetzt
"""

import importlib.util
import json
import sys
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any
from urllib.parse import urlsplit, urlunsplit

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_13.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_13.py wurde nicht gefunden.\n"
        "Lege News Studio 5.14 in denselben Ordner wie Version 5.13."
    )

spec = importlib.util.spec_from_file_location("news_studio_5_13_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("News Studio 5.13 konnte nicht geladen werden.")

base514 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base514
spec.loader.exec_module(base514)

tk = base514.tk
ttk = base514.ttk

MODE_AUTO = "Automatisch entscheiden"
MODE_NEWS = "Nur News-Beiträge"
MODE_BOTH = "News plus passende Warum-Beiträge"
MODE_EXPLAINER = "Nur Warum-/Grundlagenbeiträge"

OUTPUT_MODES = (MODE_AUTO, MODE_NEWS, MODE_BOTH, MODE_EXPLAINER)

MODE_KEYS = {
    MODE_AUTO: "auto",
    MODE_NEWS: "news-only",
    MODE_BOTH: "news-plus-explainers",
    MODE_EXPLAINER: "explainers-only",
}

MODE_HELP = {
    MODE_AUTO: (
        "Das Recherchetool entscheidet je Quelle, ob eine aktuelle News, "
        "ein zeitunabhängiger Warum-Beitrag oder ausnahmsweise beides sinnvoll ist."
    ),
    MODE_NEWS: (
        "Es werden ausschließlich aktuelle Meldungen und belastbare "
        "Lösungs-/Fortschrittsmeldungen erzeugt."
    ),
    MODE_BOTH: (
        "Der Schwerpunkt bleibt auf News. Wiederkehrende Zusammenhänge werden "
        "mit vorhandenen oder wenigen neuen Warum-Beiträgen verknüpft."
    ),
    MODE_EXPLAINER: (
        "Es werden ausschließlich zeitunabhängige Warum-Beiträge erzeugt, "
        "die sich später mit mehreren News verbinden lassen."
    ),
}


def clean_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def normalized(value: object) -> str:
    return clean_text(value).casefold()


def normalize_url(value: object) -> str:
    raw = clean_text(value)
    if not raw:
        return ""
    try:
        parts = urlsplit(raw)
        if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
            return raw.casefold().rstrip("/")
        return urlunsplit(
            (
                parts.scheme.lower(),
                parts.netloc.lower(),
                parts.path.rstrip("/") or "/",
                parts.query,
                "",
            )
        ).casefold()
    except Exception:
        return raw.casefold().rstrip("/")


def read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def raw_articles_from_import(path: Path) -> list[dict[str, Any]]:
    payload = read_json_object(path)
    if payload is None:
        return []
    articles = payload.get("articles", [])
    if not isinstance(articles, list):
        return []
    return [item for item in articles if isinstance(item, dict)]


def import_key(item: dict[str, Any]) -> str:
    for key in ("importKey", "researchKey", "pairKey", "explainerKey"):
        value = clean_text(item.get(key))
        if value:
            return value
    return ""


def explainer_reference(item: dict[str, Any]) -> str:
    for key in (
        "explainerRef",
        "relatedExplainerKey",
        "explainerImportKey",
        "pairedExplainerKey",
    ):
        value = clean_text(item.get(key))
        if value:
            return value
    return ""


class NewsStudio514(base514.NewsStudio513):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.14")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.13", "ZUSTAND News Studio 5.14"
        )

        settings = self.contact_db.setdefault("researchSettings", {})
        general_default = settings.get("generalOutputMode", MODE_BOTH)
        own_default = settings.get("ownFindOutputMode", MODE_AUTO)

        if general_default not in OUTPUT_MODES:
            general_default = MODE_BOTH
        if own_default not in OUTPUT_MODES:
            own_default = MODE_AUTO

        self.research_output_mode_var = tk.StringVar(value=general_default)
        self.find_output_mode_var = tk.StringVar(value=own_default)
        self.find_output_help_var = tk.StringVar(value=MODE_HELP[own_default])

        self._add_own_find_output_control()
        self._bind_own_find_mode()
        self.status_var.set(
            "News Studio 5.14 bereit │ Recherche unterscheidet News und Warum-Beiträge"
        )

    # ---------- Einstellungen ----------
    def _save_research_setting(self, key: str, value: str) -> None:
        self.contact_db.setdefault("researchSettings", {})[key] = value
        try:
            self._save_db()
        except Exception:
            pass

    def _set_general_mode(self, value: str) -> None:
        if value in OUTPUT_MODES:
            self.research_output_mode_var.set(value)
            self._save_research_setting("generalOutputMode", value)

    def _set_find_mode(self, value: str) -> None:
        if value not in OUTPUT_MODES:
            value = MODE_AUTO
        self.find_output_mode_var.set(value)
        self.find_output_help_var.set(MODE_HELP[value])
        self._save_research_setting("ownFindOutputMode", value)

        find_id, item = self._selected_find()
        if find_id and isinstance(item, dict):
            item["researchOutputMode"] = MODE_KEYS[value]
            try:
                self._save_db()
            except Exception:
                pass

    # ---------- vorhandene Grundlagen ----------
    def _existing_explainers(self) -> list[dict[str, str]]:
        records = self._all_article_records()
        explainers: list[dict[str, str]] = []
        for record in records.values():
            if record.get("contentType") != "explainer":
                continue
            identifier = clean_text(record.get("id"))
            title = clean_text(record.get("title"))
            if identifier and title:
                explainers.append({"id": identifier, "title": title})
        explainers.sort(key=lambda item: (item["title"].casefold(), item["id"]))
        return explainers

    def _existing_explainers_prompt(self) -> str:
        explainers = self._existing_explainers()
        if not explainers:
            return (
                "Im Studio sind derzeit keine vorhandenen Grundlagenbeiträge "
                "für eine direkte Verknüpfung bekannt."
            )

        lines = [
            "Bereits vorhandene Grundlagenbeiträge im Studio:",
            *[
                f'- {item["id"]}: {item["title"]}'
                for item in explainers[:80]
            ],
        ]
        if len(explainers) > 80:
            lines.append("- Weitere Grundlagen sind vorhanden; keine Duplikate erzeugen.")
        return "\n".join(lines)

    # ---------- gemeinsame Promptregeln ----------
    def _mode_instruction(self, mode: str, own_find: bool = False) -> str:
        mode_key = MODE_KEYS.get(mode, "auto")
        existing = self._existing_explainers_prompt()

        common = f"""
### Verbindliche Unterscheidung von News und Warum-Beiträgen

Gewählter Ausgabemodus: {mode}
Interner Modusschlüssel: {mode_key}

Eine **News** berichtet über etwas zeitlich Neues:
- neue Studie, neue Messdaten, neuer Bericht, neue Entscheidung oder erkennbare Veränderung;
- `contentType` ist `news` oder bei einer belastbaren konstruktiven Meldung `solution`;
- `visualMode` ist normalerweise `editorial-photo`;
- die Überschrift nennt die konkrete neue Aussage und nicht nur einen allgemeinen Mechanismus.

Ein **Warum-/Grundlagenbeitrag** erklärt einen länger gültigen Zusammenhang:
- naturwissenschaftlicher Mechanismus, Naturgesetz oder systemische Ursache-Wirkung;
- Titel möglichst als verständliche Warum-Frage;
- `contentType`: `explainer`;
- `category`: `Natur verstehen`;
- `visualMode`: `process-sketch`;
- `imageStyle`: `monochrome-editorial-sketch`;
- er muss für mehrere aktuelle oder künftige News wiederverwendbar sein.

{existing}

Prüfe zuerst, ob eine passende Grundlage bereits vorhanden ist. Dann erhält die
News direkt:
`"explainerId": "VORHANDENE_ID"`.

Nur wenn noch keine passende Grundlage existiert, darf eine neue erzeugt werden.
Für ein neu erzeugtes Paar gilt:
- die neue Grundlage erhält einen Import-Schlüssel, z. B.
  `"importKey": "GRUNDLAGE_1"`;
- jede dazugehörige News erhält
  `"explainerRef": "GRUNDLAGE_1"`;
- keine endgültigen Artikel-IDs vergeben; das Studio erzeugt sie beim Import;
- News und neue Grundlage benötigen unterschiedliche, jeweils passende
  Original- oder Grundlagenquellen. Verwende nicht dieselbe Quellen-URL für beide,
  weil der Import identische Quellen als mögliche Dublette behandelt;
- wenn keine belastbare eigenständige Grundlagenquelle vorhanden ist, keine neue
  Grundlage erzwingen.

Ergänze im Wurzelobjekt:
`"researchOutputMode": "{mode_key}"`.
"""

        if mode == MODE_NEWS:
            specific = """
### Ausgabe für diesen Auftrag

Erzeuge ausschließlich News- oder Lösungsbeiträge.
- Kein Artikel darf `contentType: "explainer"` haben.
- Verknüpfe News nach Möglichkeit mit bereits vorhandenen Grundlagen über
  `explainerId`.
- Erzeuge keine neue Grundlage und kein News-Grundlagen-Paar.
"""
        elif mode == MODE_BOTH:
            specific = """
### Ausgabe für diesen Auftrag

Der Schwerpunkt liegt klar auf aktuellen News.
- Erzeuge deutlich mehr News als neue Grundlagen.
- Im allgemeinen Recherchelauf: höchstens ein neuer Warum-Beitrag je zwei bis
  fünf thematisch passende News; neue Grundlagen nur bei wiederkehrenden
  Zusammenhängen.
- Bestehende Grundlagen haben Vorrang vor neuen.
- Eine neue Grundlage nie als bloße Umformulierung der News erzeugen, sondern
  nur als eigenständig recherchierten, länger gültigen Zusammenhang.
"""
            if own_find:
                specific += """
- Bei einem einzelnen eigenen Fund darf ein Paar aus News und Grundlage entstehen,
  wenn die Quelle sowohl eine belastbare neue Veröffentlichung als auch einen
  eigenständig belegbaren, wiederverwendbaren Mechanismus trägt.
- Ist nur eine der beiden Formen wissenschaftlich gerechtfertigt, gib nur diese
  Form aus und erzwinge kein künstliches Paar.
"""
        elif mode == MODE_EXPLAINER:
            specific = """
### Ausgabe für diesen Auftrag

Erzeuge ausschließlich Warum-/Grundlagenbeiträge.
- Jeder Artikel hat `contentType: "explainer"`.
- Keine News, keine Lösungs- oder Ereignismeldung ausgeben.
- Nutze aktuelle Veröffentlichungen höchstens als Ausgangspunkt; der fertige
  Beitrag erklärt einen länger gültigen Zusammenhang.
- Keine Grundlage erzeugen, die in der Liste vorhandener Grundlagen bereits
  inhaltlich abgedeckt ist.
"""
        else:
            specific = """
### Ausgabe für diesen Auftrag

Entscheide automatisch und begründe die Entscheidung durch die Datenstruktur:
- Normalfall bei einer neuen Veröffentlichung ist eine News.
- Ein Warum-Beitrag entsteht nur für einen eigenständigen, länger gültigen und
  wiederverwendbaren Zusammenhang.
- Ein Paar aus News und Grundlage nur dann, wenn beide redaktionell eigenständig
  und durch passende Primär- oder Grundlagenquellen belegt sind.
- Vermeide unnötige Grundlagen-Duplikate.
"""

        schema = """
### Zusätzliche Importfelder

Jeder Artikel enthält zusätzlich:
- `"contentType": "news|solution|explainer|editorial"`
- `"visualMode": "editorial-photo|process-sketch|symbolic|scientific"`
- `"imageStyle": "nature|symbolic|scientific|editorial|monochrome-editorial-sketch"`

Optional für Verknüpfungen:
- `"explainerId": "GR_..."` für eine vorhandene Grundlage
- `"importKey": "GRUNDLAGE_1"` in einer neu erzeugten Grundlage
- `"explainerRef": "GRUNDLAGE_1"` in den dazugehörigen News

Grundlagenbilder bleiben reduzierte Titelbilder:
eine Kernaussage, ein Hauptmotiv, höchstens drei Prozessstufen, vier Pfeile und
drei kurze Beschriftungen. Ziel sind Grundverständnis und Neugier auf Forschung,
nicht eine vollständige Lehrtafel.
"""
        return common + specific + schema

    # ---------- allgemeiner Recherche-Prompt ----------
    def _build_research_prompt_for_mode(self, period: str, mode: str) -> str:
        prompt = super().build_research_prompt(period)
        return prompt + self._mode_instruction(mode, own_find=False)

    def build_research_prompt(self, period: str) -> str:
        mode = (
            self.research_output_mode_var.get()
            if hasattr(self, "research_output_mode_var")
            else MODE_BOTH
        )
        return self._build_research_prompt_for_mode(period, mode)

    def open_research_prompt(self):
        window = tk.Toplevel(self)
        window.title("Recherche-Prompt – News und Warum-Beiträge")
        window.transient(self)
        window.geometry("980x730")
        window.minsize(760, 540)

        outer = ttk.Frame(window, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="Neue Beiträge recherchieren",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Zeitraum und gewünschte Ausgabe wählen. Das Studio gibt vorhandene "
                "Grundlagen mit ID an den Prompt weiter und verbindet neue Paare nach "
                "dem Import automatisch."
            ),
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(2, 10))

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 8))

        ttk.Label(controls, text="Zeitraum:").grid(row=0, column=0, sticky="w")
        period = tk.StringVar(value="Seit gestern")
        period_combo = ttk.Combobox(
            controls,
            textvariable=period,
            state="readonly",
            width=22,
            values=("Seit gestern", "Seit einer Woche", "Seit einem Monat"),
        )
        period_combo.grid(row=0, column=1, sticky="w", padx=(8, 20))

        ttk.Label(controls, text="Ausgabe:").grid(row=0, column=2, sticky="w")
        mode = tk.StringVar(value=self.research_output_mode_var.get())
        mode_combo = ttk.Combobox(
            controls,
            textvariable=mode,
            state="readonly",
            width=36,
            values=OUTPUT_MODES,
        )
        mode_combo.grid(row=0, column=3, sticky="ew", padx=(8, 0))
        controls.columnconfigure(3, weight=1)

        help_var = tk.StringVar(value=MODE_HELP[mode.get()])
        ttk.Label(
            outer,
            textvariable=help_var,
            wraplength=900,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        text = tk.Text(outer, wrap="word", padx=8, pady=8)
        text.pack(fill="both", expand=True)

        status = tk.StringVar(value="Bereit")

        def rebuild(*_args):
            selected_mode = mode.get()
            if selected_mode not in OUTPUT_MODES:
                selected_mode = MODE_BOTH
                mode.set(selected_mode)
            self._set_general_mode(selected_mode)
            help_var.set(MODE_HELP[selected_mode])
            text.delete("1.0", "end")
            text.insert(
                "1.0",
                self._build_research_prompt_for_mode(period.get(), selected_mode),
            )
            status.set(f"Prompt: {period.get()} │ {selected_mode}")

        def copy_prompt():
            prompt = text.get("1.0", "end").strip()
            self.clipboard_clear()
            self.clipboard_append(prompt)
            self.update()
            status.set("Prompt wurde in die Zwischenablage kopiert.")

        period_combo.bind("<<ComboboxSelected>>", rebuild)
        mode_combo.bind("<<ComboboxSelected>>", rebuild)
        rebuild()

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(10, 0))
        ttk.Label(footer, textvariable=status).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            footer, text="Prompt kopieren", command=copy_prompt
        ).pack(side="right")
        ttk.Button(
            footer, text="Schließen", command=window.destroy
        ).pack(side="right", padx=(0, 6))

        window.bind("<Escape>", lambda _event: window.destroy())
        window.bind("<Control-c>", lambda _event: copy_prompt())

    # ---------- Eigene Funde ----------
    def _add_own_find_output_control(self) -> None:
        if not hasattr(self, "find_tree"):
            return

        parent = self.find_tree.master
        frame = ttk.LabelFrame(
            parent,
            text="Ausgabe des Rechercheauftrags",
            padding=8,
        )
        frame.pack(fill="x", pady=(9, 0))

        row = ttk.Frame(frame)
        row.pack(fill="x")
        ttk.Label(row, text="Beitragstyp", width=18).pack(side="left")
        combo = ttk.Combobox(
            row,
            textvariable=self.find_output_mode_var,
            values=OUTPUT_MODES,
            state="readonly",
            width=38,
        )
        combo.pack(side="left", fill="x", expand=True)
        combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._set_find_mode(self.find_output_mode_var.get()),
        )

        ttk.Label(
            frame,
            textvariable=self.find_output_help_var,
            wraplength=950,
            justify="left",
        ).pack(anchor="w", pady=(5, 0))

    def _bind_own_find_mode(self) -> None:
        if hasattr(self, "find_tree"):
            self.find_tree.bind(
                "<<TreeviewSelect>>",
                self._load_selected_find_mode,
                add="+",
            )

    def _load_selected_find_mode(self, _event=None) -> None:
        _find_id, item = self._selected_find()
        if not isinstance(item, dict):
            return

        stored_key = clean_text(item.get("researchOutputMode"))
        selected = next(
            (label for label, key in MODE_KEYS.items() if key == stored_key),
            self.contact_db.get("researchSettings", {}).get(
                "ownFindOutputMode", MODE_AUTO
            ),
        )
        if selected not in OUTPUT_MODES:
            selected = MODE_AUTO
        self.find_output_mode_var.set(selected)
        self.find_output_help_var.set(MODE_HELP[selected])

    def copy_find_package(self) -> None:
        find_id, item = self._selected_find()
        if not item:
            messagebox.showinfo(
                "Auswahl fehlt",
                "Bitte zuerst einen Fund auswählen.",
                parent=self,
            )
            return

        mode = self.find_output_mode_var.get()
        if mode not in OUTPUT_MODES:
            mode = MODE_AUTO
        self._set_find_mode(mode)

        package = f"""Bitte prüfe dieses Fundstück für den ZUSTAND-Infoscreen und erstelle eine herunterladbare JSON-Datei für News Studio 5.14.

Art: {item.get('kind', '')}
Arbeitstitel: {item.get('title', '')}
Link/DOI: {item.get('source', '')}
Lokale Datei: {item.get('file', '')}

Notiz/Text:
{item.get('text', '')}

Verifiziere zuerst Original- und Primärquellen. Verwende das Format
"zustand-recherche-import-v1" mit einer Artikelliste. Jeder Artikel enthält
title, summary (350–550 Zeichen), planetaryBoundary, keywords, sourceTitle,
sourceUrl, publicationDate, category und interviewPotential sowie optional
contacts.

Ergänze außerdem zwingend:
"editorial": {{
  "sourceType": "Quellentyp und Einordnung",
  "coreChange": "eigentliche Veränderung",
  "questionBehindNews": "Frage hinter der Nachricht",
  "causalChain": "Wirkungskette",
  "affectedSystems": "betroffene natürliche Systeme",
  "planetaryBoundaries": "betroffene planetare Grenzen",
  "societalRelevance": "gesellschaftliche Relevanz",
  "uncertainties": "Unsicherheiten und Grenzen",
  "interviewPotential": "Bewertung, Begründung und mögliche Fragen",
  "sources": "Original- und Primärquellen mit Herausgeber und URL",
  "imageIdea": "Bildidee und nicht zu zeigende Motive",
  "screenConnection": "kurze Zeile: Was hängt zusammen?"
}}

Keine öffentliche Prioritätszahl verwenden. Geeignete Ansprechpersonen nur mit
verifizierten beruflichen Kontaktdaten offizieller Institutionen aufnehmen.
""" + self._mode_instruction(mode, own_find=True)

        self.clipboard_clear()
        self.clipboard_append(package)
        self.update()

        if find_id and isinstance(item, dict):
            item["researchOutputMode"] = MODE_KEYS[mode]
            try:
                self._save_db()
            except Exception:
                pass

        self.status_var.set(
            f"Rechercheauftrag kopiert │ Ausgabe: {mode}"
        )

    # ---------- Import und automatische Paarverknüpfung ----------
    def _match_raw_to_local(
        self,
        raw: dict[str, Any],
        records: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        title = normalized(raw.get("title"))
        source_url = normalize_url(raw.get("sourceUrl"))

        candidates = [
            record
            for record in records.values()
            if normalized(record.get("title")) == title
        ]
        if len(candidates) == 1:
            return candidates[0]

        if candidates and source_url:
            for record in candidates:
                data = read_json_object(Path(record["path"]))
                if data and normalize_url(data.get("sourceUrl")) == source_url:
                    return record

        if source_url:
            url_matches: list[dict[str, Any]] = []
            for record in records.values():
                data = read_json_object(Path(record["path"]))
                if data and normalize_url(data.get("sourceUrl")) == source_url:
                    url_matches.append(record)
            if len(url_matches) == 1:
                return url_matches[0]

        return candidates[0] if candidates else None

    def _sync_import_explainer_links(self, path: Path) -> dict[str, Any]:
        raw_articles = raw_articles_from_import(path)
        if not raw_articles:
            return {"linked": 0, "newExplainers": 0, "unmatched": []}

        records = self._all_article_records()
        valid_explainer_ids = {
            clean_text(record.get("id"))
            for record in records.values()
            if record.get("contentType") == "explainer"
        }

        key_to_id: dict[str, str] = {}
        raw_to_local: list[
            tuple[dict[str, Any], dict[str, Any] | None]
        ] = []
        unmatched: list[str] = []

        for raw in raw_articles:
            local = self._match_raw_to_local(raw, records)
            raw_to_local.append((raw, local))
            if local is None:
                unmatched.append(clean_text(raw.get("title")) or "Ohne Titel")
                continue

            content_type = clean_text(raw.get("contentType")).casefold()
            key = import_key(raw)
            if content_type == "explainer" and key:
                key_to_id[key] = clean_text(local.get("id"))

        linked = 0
        affected_paths: set[Path] = set()

        for raw, local in raw_to_local:
            if local is None:
                continue

            content_type = clean_text(raw.get("contentType")).casefold()
            if content_type == "explainer":
                continue

            target_id = clean_text(raw.get("explainerId"))
            if target_id not in valid_explainer_ids:
                target_id = ""

            if not target_id:
                reference = explainer_reference(raw)
                target_id = key_to_id.get(reference, "")

            if not target_id:
                continue

            article_path = Path(local["path"])
            article = read_json_object(article_path)
            if article is None:
                continue

            article["explainerId"] = target_id
            article["sequenceRole"] = "context-news"
            write_json_atomic(article_path, article)
            affected_paths.add(article_path)
            linked += 1

        return {
            "linked": linked,
            "newExplainers": len(key_to_id),
            "unmatched": unmatched,
            "affected": len(affected_paths),
        }

    def import_research_file(self, selected_path: str | Path | None = None):
        chosen: dict[str, str] = {"path": str(selected_path or "")}
        original_dialog = filedialog.askopenfilename

        def capture_dialog(*args, **kwargs):
            if selected_path:
                selected = str(selected_path)
            else:
                selected = original_dialog(*args, **kwargs)
            chosen["path"] = selected or ""
            return selected

        filedialog.askopenfilename = capture_dialog
        try:
            result = super().import_research_file()
        finally:
            filedialog.askopenfilename = original_dialog

        if not chosen["path"]:
            return result

        import_path = Path(chosen["path"])
        try:
            stats = self._sync_import_explainer_links(import_path)
        except Exception as exc:
            messagebox.showwarning(
                "Beitragstypen importiert – Verknüpfung unvollständig",
                "Die Beiträge wurden importiert, aber neue News-Grundlagen-Paare "
                f"konnten nicht vollständig verbunden werden.\n\n"
                f"{type(exc).__name__}: {exc}",
                parent=self,
            )
            return result

        if stats["linked"] or stats["newExplainers"]:
            self.refresh_all()
            detail = (
                f'Import abgeschlossen │ {stats["linked"]} News mit Grundlagen '
                f'verknüpft │ {stats["newExplainers"]} neue Grundlagen-Schlüssel'
            )
            if stats["unmatched"]:
                detail += f' │ nicht zugeordnet: {len(stats["unmatched"])}'
            self.status_var.set(detail)

        return result


def main() -> None:
    app = NewsStudio514()
    app.mainloop()


if __name__ == "__main__":
    main()
