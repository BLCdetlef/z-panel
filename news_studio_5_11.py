#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.11 – reduzierte Grundlagenbilder und thematische Abspielfolgen.

Benötigt im selben Ordner:
- news_studio_5_10.py
- news_studio_5_9.py
- news_studio_5_8.py
- news_studio_5_7.py
- news_studio_5_6.py
- news_studio_5_5_2.py und die bisherige Projektstruktur

Neu gegenüber 5.10:
1. Grundlagenprompt:
   - ein Bild, ein Zusammenhang
   - höchstens drei Prozessstufen
   - höchstens vier Pfeile
   - höchstens drei kurze Beschriftungen
   - Interesse und Neugier auf Forschung statt vollständiger Lehrtafel

2. Thematische Abspielfolgen:
   - News können über explainerId mit einer Grundlage verknüpft werden
   - mehrere News werden vor der passenden Grundlage abgespielt
   - news.json enthält ein entsprechend sortiertes articles-Array
   - zusätzlich: playbackOrder, playbackGroups und relatedNewsIds
"""

import importlib.util
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_10.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_10.py wurde nicht gefunden.\n"
        "Lege News Studio 5.11 in denselben Ordner wie Version 5.10."
    )

spec = importlib.util.spec_from_file_location("news_studio_5_10_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("News Studio 5.10 konnte nicht geladen werden.")

base511 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base511
spec.loader.exec_module(base511)

tk = base511.base510.tk
ttk = base511.base510.ttk

base_app = base511.base_app
OUTPUT = base511.base510.OUTPUT
DRAFTS_DIR = base511.base510.DRAFTS_DIR
ARTICLES_DIR = base511.base510.ARTICLES_DIR

read_json_object = base511.read_json_object
write_json_atomic = base511.write_json_atomic
normalized_text = base511.base510.normalized_text
normalize_content_type = base511.base510.normalize_content_type
normalize_visual_mode = base511.base510.normalize_visual_mode
normalize_image_style = base511.normalize_image_style

NO_EXPLAINER_LABEL = "— keine Grundlage —"


def article_id(article: dict[str, Any], fallback: str = "") -> str:
    return str(article.get("id") or fallback or "").strip()


def article_title(article: dict[str, Any]) -> str:
    return str(article.get("title") or "Ohne Titel").strip()


def is_explainer(article: dict[str, Any]) -> bool:
    return normalize_content_type(article.get("contentType"), article) == "explainer"


def normalize_link_fields(article: dict[str, Any]) -> None:
    content_type = normalize_content_type(article.get("contentType"), article)
    visual_mode = normalize_visual_mode(article.get("visualMode"), content_type)
    image_style = normalize_image_style(article.get("imageStyle"), content_type, visual_mode)

    article["contentType"] = content_type
    article["visualMode"] = visual_mode
    article["imageStyle"] = image_style

    if content_type == "explainer":
        article["category"] = "Natur verstehen"
        article["displayLabel"] = "NATUR VERSTEHEN"
        article.pop("explainerId", None)
    else:
        explainer_id = str(article.get("explainerId") or "").strip()
        if explainer_id:
            article["explainerId"] = explainer_id
        else:
            article.pop("explainerId", None)


def build_playback_sequence(
    articles: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], list[dict[str, Any]], list[str]]:
    """Ordnet mehrere News unmittelbar vor ihre gemeinsame Grundlage.

    Die Gruppenreihenfolge richtet sich nach dem ersten Auftreten eines
    verknüpften Beitrags oder der Grundlage in der bisherigen Artikelfolge.
    Nicht verknüpfte Grundlagen werden ans Ende gesetzt.
    """

    for article in articles:
        normalize_link_fields(article)

    explainer_index_by_id: dict[str, int] = {}
    duplicate_explainers: list[str] = []

    for index, article in enumerate(articles):
        if not is_explainer(article):
            continue
        identifier = article_id(article)
        if not identifier:
            continue
        if identifier in explainer_index_by_id:
            duplicate_explainers.append(identifier)
            continue
        explainer_index_by_id[identifier] = index

    linked_indices: dict[str, list[int]] = defaultdict(list)
    invalid_links: list[str] = []

    for index, article in enumerate(articles):
        if is_explainer(article):
            continue
        linked_id = str(article.get("explainerId") or "").strip()
        if not linked_id:
            continue
        if linked_id not in explainer_index_by_id:
            invalid_links.append(
                f"{article_id(article, f'Position {index + 1}')} → {linked_id}"
            )
            continue
        linked_indices[linked_id].append(index)

    # Rückverknüpfung direkt in die Grundlagenbeiträge schreiben.
    groups: list[dict[str, Any]] = []
    for explainer_id, explainer_index in explainer_index_by_id.items():
        news_indices = linked_indices.get(explainer_id, [])
        news_ids = [
            article_id(articles[index])
            for index in news_indices
            if article_id(articles[index])
        ]
        explainer = articles[explainer_index]
        explainer["relatedNewsIds"] = news_ids
        explainer["relatedNewsCount"] = len(news_indices)
        explainer["sequenceRole"] = "explainer-after-news"

        count = len(news_indices)
        if count == 0:
            status = "unlinked"
        elif count == 1:
            status = "thin"
        elif count <= 5:
            status = "recommended"
        else:
            status = "large"

        groups.append(
            {
                "explainerId": explainer_id,
                "explainerTitle": article_title(explainer),
                "newsIds": news_ids,
                "newsCount": count,
                "status": status,
                "recommendedNewsCount": {"min": 2, "max": 5},
            }
        )

        for index in news_indices:
            articles[index]["sequenceRole"] = "context-news"

    ordered: list[dict[str, Any]] = []
    emitted: set[int] = set()
    deferred_unlinked_explainers: list[int] = []

    def emit(index: int) -> None:
        if index in emitted:
            return
        ordered.append(articles[index])
        emitted.add(index)

    def emit_group(explainer_id: str) -> None:
        for news_index in linked_indices.get(explainer_id, []):
            emit(news_index)
        explainer_index = explainer_index_by_id.get(explainer_id)
        if explainer_index is not None:
            emit(explainer_index)

    for index, article in enumerate(articles):
        if index in emitted:
            continue

        if is_explainer(article):
            identifier = article_id(article)
            if identifier and linked_indices.get(identifier):
                emit_group(identifier)
            else:
                deferred_unlinked_explainers.append(index)
            continue

        linked_id = str(article.get("explainerId") or "").strip()
        if linked_id and linked_id in explainer_index_by_id:
            emit_group(linked_id)
        else:
            emit(index)

    # Sicherheitsnetz für noch nicht emittierte normale Beiträge.
    for index, article in enumerate(articles):
        if index not in emitted and not is_explainer(article):
            emit(index)

    # Grundlagen ohne passende News erst nach den News-Blöcken zeigen.
    for index in deferred_unlinked_explainers:
        emit(index)

    # Letztes Sicherheitsnetz.
    for index in range(len(articles)):
        emit(index)

    playback_order = [
        article_id(article)
        for article in ordered
        if article_id(article)
    ]

    warnings: list[str] = []
    if invalid_links:
        warnings.append(
            "Ungültige Grundlagen-Verknüpfungen: " + "; ".join(invalid_links)
        )
    if duplicate_explainers:
        warnings.append(
            "Doppelte Grundlagen-IDs: " + ", ".join(sorted(set(duplicate_explainers)))
        )

    return ordered, playback_order, groups, warnings


def normalize_and_order_news_json(path: Path) -> dict[str, Any]:
    payload = read_json_object(path)
    if payload is None:
        raise ValueError("news.json enthält kein gültiges JSON-Objekt.")

    raw_articles = payload.get("articles", [])
    if not isinstance(raw_articles, list):
        raise ValueError("news.json enthält keine Artikelliste.")

    articles = [article for article in raw_articles if isinstance(article, dict)]
    ordered, playback_order, groups, warnings = build_playback_sequence(articles)

    payload["articles"] = ordered
    payload["articleCount"] = len(ordered)
    payload["playbackOrder"] = playback_order
    payload["playbackGroups"] = groups
    payload["playbackPolicy"] = {
        "mode": "news-then-explainer",
        "description": (
            "Thematisch verknüpfte Nachrichten werden zuerst gezeigt; "
            "anschließend folgt der zugehörige Grundlagenbeitrag."
        ),
        "recommendedNewsPerExplainer": {"min": 2, "max": 5},
        "unlinkedExplainers": "after-news-blocks",
    }

    try:
        schema = int(payload.get("contentSchema", 0) or 0)
    except (TypeError, ValueError):
        schema = 0
    payload["contentSchema"] = max(schema, 5)

    if warnings:
        payload["playbackWarnings"] = warnings
    else:
        payload.pop("playbackWarnings", None)

    write_json_atomic(path, payload)

    return {
        "total": len(ordered),
        "groups": len(groups),
        "linked_groups": sum(1 for group in groups if group["newsCount"] > 0),
        "recommended_groups": sum(
            1 for group in groups if group["status"] == "recommended"
        ),
        "thin_groups": sum(1 for group in groups if group["status"] == "thin"),
        "unlinked_groups": sum(
            1 for group in groups if group["status"] == "unlinked"
        ),
        "warnings": warnings,
    }


class NewsStudio511(base511.NewsStudio510):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.11")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.10", "ZUSTAND News Studio 5.11"
        )

        self.explainer_link_var = tk.StringVar(value=NO_EXPLAINER_LABEL)
        self.explainer_link_info_var = tk.StringVar(
            value="Mehrere News können dieselbe Grundlage vorbereiten."
        )
        self._explainer_label_to_id: dict[str, str] = {}
        self._explainer_id_to_label: dict[str, str] = {}
        self._link_loading = False

        self._add_explainer_link_fields()
        self.content_type_var.trace_add("write", self._on_link_type_change)
        self._refresh_explainer_choices()
        self._apply_link_field_state()

        self.status_var.set(
            "News Studio 5.11 bereit │ reduzierte Grundlagenbilder und News→Grundlage-Folgen"
        )

    # ---------- UI ----------
    def _article_form_parent(self):
        notes = getattr(self, "article_notes", None)
        if notes is not None:
            return notes.master
        return getattr(self, "article_text").master

    def _add_explainer_link_fields(self) -> None:
        box = ttk.LabelFrame(
            self._article_form_parent(),
            text="Thematische Abspielfolge",
            padding=10,
        )
        box.pack(fill="x", pady=(10, 4))

        row = ttk.Frame(box)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text="Zugehörige Grundlage", width=20).pack(side="left")

        self.explainer_link_combo = ttk.Combobox(
            row,
            textvariable=self.explainer_link_var,
            values=(NO_EXPLAINER_LABEL,),
            state="readonly",
            width=55,
        )
        self.explainer_link_combo.pack(side="left", fill="x", expand=True)
        self.explainer_link_combo.bind(
            "<<ComboboxSelected>>", self._on_link_selection
        )

        ttk.Label(
            box,
            textvariable=self.explainer_link_info_var,
            wraplength=800,
            justify="left",
        ).pack(anchor="w", pady=(5, 0))

    def _all_article_records(self) -> dict[str, dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for folder in (DRAFTS_DIR, ARTICLES_DIR):
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*.json")):
                if (
                    path.name.lower() == "index.json"
                    or path.name.lower().endswith("_vorlage.json")
                ):
                    continue
                article = read_json_object(path)
                if article is None:
                    continue
                identifier = article_id(article, path.stem)
                if not identifier:
                    continue
                records[identifier] = {
                    "id": identifier,
                    "title": article_title(article),
                    "contentType": normalize_content_type(
                        article.get("contentType"), article
                    ),
                    "explainerId": str(article.get("explainerId") or "").strip(),
                    "path": str(path),
                }
        return records

    def _refresh_explainer_choices(self, selected_id: str | None = None) -> None:
        if not hasattr(self, "explainer_link_combo"):
            return

        records = self._all_article_records()
        explainers = [
            record
            for record in records.values()
            if record["contentType"] == "explainer"
        ]
        explainers.sort(key=lambda record: (record["title"].casefold(), record["id"]))

        self._explainer_label_to_id = {}
        self._explainer_id_to_label = {}

        labels = [NO_EXPLAINER_LABEL]
        for record in explainers:
            label = f'{record["id"]} — {record["title"]}'
            labels.append(label)
            self._explainer_label_to_id[label] = record["id"]
            self._explainer_id_to_label[record["id"]] = label

        self.explainer_link_combo.configure(values=tuple(labels))

        if selected_id is None:
            selected_id = self._selected_explainer_id()

        self._link_loading = True
        try:
            self.explainer_link_var.set(
                self._explainer_id_to_label.get(
                    str(selected_id or "").strip(),
                    NO_EXPLAINER_LABEL,
                )
            )
        finally:
            self._link_loading = False

        self._update_link_info(records)

    def _selected_explainer_id(self) -> str:
        label = self.explainer_link_var.get().strip()
        return self._explainer_label_to_id.get(label, "")

    def _current_article_identifier(self) -> str:
        path = getattr(self, "current_article_path", None)
        if path:
            article = read_json_object(Path(path))
            if article:
                return article_id(article, Path(path).stem)

        for key in ("id", "articleId"):
            variable = getattr(self, "article_vars", {}).get(key)
            if variable is not None:
                value = str(variable.get() or "").strip()
                if value:
                    return value
        return ""

    def _linked_news_count(self, explainer_id: str) -> tuple[int, list[str]]:
        if not explainer_id:
            return 0, []
        records = self._all_article_records()
        linked = [
            record
            for record in records.values()
            if record["contentType"] != "explainer"
            and record["explainerId"] == explainer_id
        ]
        linked.sort(key=lambda record: record["title"].casefold())
        return len(linked), [record["title"] for record in linked]

    def _update_link_info(
        self, records: dict[str, dict[str, Any]] | None = None
    ) -> None:
        content_type = self._content_type_code()

        if content_type == "explainer":
            identifier = self._current_article_identifier()
            count, titles = self._linked_news_count(identifier)
            if not identifier:
                self.explainer_link_info_var.set(
                    "Nach dem ersten Speichern zeigt das Studio hier die "
                    "verknüpften News. Empfohlen sind zwei bis fünf Meldungen."
                )
            elif count == 0:
                self.explainer_link_info_var.set(
                    "Noch keine News verknüpft. Die Grundlage wird im Export "
                    "erst nach den News-Blöcken gezeigt."
                )
            elif count == 1:
                self.explainer_link_info_var.set(
                    f"1 News verknüpft: {titles[0]}. "
                    "Für eine stärkere Einordnung sind meist zwei bis fünf sinnvoll."
                )
            else:
                preview = "; ".join(titles[:3])
                suffix = " …" if len(titles) > 3 else ""
                self.explainer_link_info_var.set(
                    f"{count} News verknüpft: {preview}{suffix}. "
                    "Im Infoscreen folgen zuerst die News, danach diese Grundlage."
                )
        else:
            selected = self._selected_explainer_id()
            if selected:
                title = (
                    records.get(selected, {}).get("title")
                    if records
                    else None
                )
                self.explainer_link_info_var.set(
                    "Diese Meldung wird vor der gewählten Grundlage abgespielt"
                    + (f": {title}." if title else ".")
                )
            else:
                self.explainer_link_info_var.set(
                    "Optional: Diese News mit einer passenden Grundlage verknüpfen. "
                    "Mehrere News dürfen dieselbe Grundlage vorbereiten."
                )

    def _apply_link_field_state(self) -> None:
        if not hasattr(self, "explainer_link_combo"):
            return
        if self._content_type_code() == "explainer":
            self._link_loading = True
            try:
                self.explainer_link_var.set(NO_EXPLAINER_LABEL)
                self.explainer_link_combo.configure(state="disabled")
            finally:
                self._link_loading = False
        else:
            self.explainer_link_combo.configure(state="readonly")
        self._update_link_info()

    def _on_link_type_change(self, *_args) -> None:
        self._apply_link_field_state()

    def _on_link_selection(self, _event=None) -> None:
        if self._link_loading:
            return
        self._update_link_info(self._all_article_records())

    # ---------- Laden, Speichern, Aktualisieren ----------
    def refresh_all(self):
        result = super().refresh_all()
        if hasattr(self, "explainer_link_combo"):
            selected = self._selected_explainer_id()
            self._refresh_explainer_choices(selected)
            self._apply_link_field_state()
        return result

    def new_article(self):
        result = super().new_article()
        if hasattr(self, "explainer_link_var"):
            self._refresh_explainer_choices("")
            self._apply_link_field_state()
        return result

    def load_selected_article(self, _event=None):
        result = super().load_selected_article(_event)
        if hasattr(self, "explainer_link_var"):
            path = getattr(self, "current_article_path", None)
            article = read_json_object(Path(path)) if path else None
            selected = str((article or {}).get("explainerId") or "").strip()
            self._refresh_explainer_choices(selected)
            self._apply_link_field_state()
        return result

    def article_payload(self, forced_status=None):
        data = super().article_payload(forced_status)
        content_type = self._content_type_code()

        if content_type == "explainer":
            data.pop("explainerId", None)
            data.pop("relatedNewsIds", None)
            data.pop("relatedNewsCount", None)
            data["sequenceRole"] = "explainer-after-news"
        else:
            selected = self._selected_explainer_id()
            if selected:
                data["explainerId"] = selected
                data["sequenceRole"] = "context-news"
            else:
                data.pop("explainerId", None)
                data.pop("sequenceRole", None)

        return data

    # ---------- Stark reduzierter Grundlagenprompt ----------
    def build_image_prompt(self) -> str:
        if not hasattr(self, "visual_mode_var"):
            return super().build_image_prompt()

        if self._visual_mode_code() != "process-sketch":
            return super().build_image_prompt()

        title = self.article_vars["title"].get().strip()
        summary = self.article_vars["summary"].get().strip()
        boundary = self.article_vars["planetaryBoundary"].get().strip()
        keywords = self.article_vars["keywords"].get().strip()

        hint_function = getattr(base_app, "article_image_hint", None)
        hint = (
            hint_function(title, summary, keywords, boundary)
            if callable(hint_function)
            else "der zentrale naturwissenschaftliche Zusammenhang"
        )

        return (
            "Erzeuge ein einzelnes Titelbild für einen öffentlichen Infoscreen.\n\n"
            f"Artikelthema: {title or 'noch ohne Titel'}.\n"
            f"Kernaussage: {summary or 'noch keine Kurzfassung'}.\n"
            f"Inhaltlicher Ausgangspunkt: {hint}.\n"
            f"Schlagwörter: {keywords or 'Natur verstehen, Grundlagen'}.\n\n"
            "Ziel des Bildes: Es soll Wissen anbahnen, vor allem aber Interesse "
            "und Neugier auf Forschung zu unseren natürlichen Lebensgrundlagen "
            "wecken. Das Bild ist ein Titelbild und keine vollständige Lehrtafel. "
            "Es öffnet die Frage; der Beitrag erklärt die Einzelheiten.\n\n"
            "Bildtyp: hochwertige wissenschaftsjournalistische Prozessskizze "
            "für die Rubrik „Natur verstehen“, in Schwarz-Weiß oder "
            "kontrastreichen Graustufen. Zeige genau eine zentrale "
            "Ursache-Wirkungs-Beziehung aus dem Artikel.\n\n"
            "Verbindliche Reduktion:\n"
            "- genau ein dominantes Hauptmotiv\n"
            "- genau eine Kernaussage\n"
            "- höchstens drei klar unterscheidbare Prozessstufen\n"
            "- höchstens vier Pfeile oder Richtungslinien\n"
            "- höchstens drei sehr kurze Beschriftungen, Kürzel oder Formelzeichen\n"
            "- höchstens ein zurückhaltender Nebenaspekt\n"
            "- das Bild muss auch ohne Lesen der Beschriftungen verständlich sein\n\n"
            "Falls der Artikel mehrere Aspekte enthält, wähle ausschließlich den "
            "für Titel und Kernaussage wichtigsten Zusammenhang. Zeige keine "
            "vollständige Prozesskette, keine Materialsammlung, keine vielen "
            "Beispiele und keine parallelen Erklärstränge.\n\n"
            "Gestaltung:\n"
            "- feine Linien, klare Umrisse und dezente Schraffuren\n"
            "- ruhiger heller oder neutraler Hintergrund\n"
            "- klare Hell-Dunkel-Trennung\n"
            "- erwachsen, hochwertig und wissenschaftsnah\n"
            "- einfache Pfeile, Symbole, Abkürzungen oder Formelzeichen sind "
            "erlaubt, aber nur wenn sie die eine Hauptidee unmittelbar klären\n"
            "- Beschriftungen auf Deutsch oder als allgemein verständliche "
            "Fachkürzel, sehr kurz und kontrastreich\n\n"
            "Unbedingt vermeiden:\n"
            "- vollständige Flussdiagramme oder Ablaufpläne\n"
            "- mehr als drei Stationen\n"
            "- viele Kreise, Kästen, Materialbehälter oder Symbolgruppen\n"
            "- lange Sätze, Erklärtexte, Legenden und Zusammenfassungsleisten\n"
            "- mehrere Landschaftsräume oder mehrere gleichwertige Hauptmotive\n"
            "- bunte Infografik, Comic, Kinderbuchstil oder CAD-Zeichnung\n"
            "- Logos, Wasserzeichen, dekorative Rahmen oder Collagen\n\n"
            "Komposition für den Infoscreen:\n"
            "- Hochformat im Seitenverhältnis 8:9\n"
            "- für die linke Hälfte eines vertikal geteilten 16:9-Bildschirms\n"
            "- aus drei bis fünf Metern Entfernung sofort erfassbar\n"
            "- wichtige Motive mindestens zehn Prozent vom Bildrand entfernt\n"
            "- eindeutige Blickführung und viel ruhige Fläche\n\n"
            "Leitgedanke: Ein Blick – ein Zusammenhang. Vermittle lieber einen "
            "klaren Gedanken als viele Details. Das Bild soll ein unmittelbares "
            "„Ach so“ auslösen und zugleich zum Weiterlesen anregen.\n\n"
            "Ausgabe: genau ein fertiges Bild im Hochformat 8:9."
        )

    def _update_image_metadata(self) -> None:
        super()._update_image_metadata()

        image_id = self.article_vars["imageId"].get().strip()
        if not image_id or self._visual_mode_code() != "process-sketch":
            return

        matcher = getattr(base_app, "image_matches", None)
        if not callable(matcher):
            return

        try:
            _images, metadata_files = matcher(image_id)
        except Exception:
            return

        for path in metadata_files:
            metadata = read_json_object(Path(path))
            if metadata is None:
                continue
            metadata["editorialPurpose"] = (
                "Grundverständnis und Neugier auf Forschung zu den "
                "natürlichen Lebensgrundlagen"
            )
            metadata["complexityLimits"] = {
                "mainIdeas": 1,
                "maxProcessStages": 3,
                "maxArrows": 4,
                "maxShortLabels": 3,
                "maxSecondaryAspects": 1,
                "mustWorkWithoutReading": True,
            }
            write_json_atomic(Path(path), metadata)

    # ---------- Rechercheprompt ----------
    def build_research_prompt(self, period: str) -> str:
        prompt = super().build_research_prompt(period)
        appendix = """

### Grundlagenzuordnung und Abspielfolge

Aktuelle News können optional mit einer bestehenden Grundlage verknüpft werden:

"explainerId": "ID_DES_GRUNDLAGENBEITRAGS"

Mehrere News dürfen dieselbe explainerId verwenden. Im Infoscreen werden diese
News zuerst abgespielt; danach folgt einmalig die zugehörige Grundlage.
Empfohlen sind zwei bis fünf News je Grundlage.

Neue Grundlagenbeiträge sollen nur vorgeschlagen werden, wenn sie einen
wiederkehrenden Zusammenhang erklären, der für mehrere aktuelle oder künftige
Meldungen nützlich ist.

### Reduktion der Grundlagenbilder

Grundlagenbilder sind Titelbilder und keine vollständigen Lehrtafeln.
Die Bildidee muss auf genau eine zentrale Ursache-Wirkungs-Beziehung reduziert
werden: höchstens drei Prozessstufen, vier Pfeile und drei kurze Beschriftungen.
Das Bild soll ein Grundverständnis vermitteln, vor allem aber Interesse und
Neugier auf Forschung zu unseren Lebensgrundlagen wecken.
"""
        if "Grundlagenzuordnung und Abspielfolge" not in prompt:
            prompt += appendix
        return prompt

    # ---------- news.json ----------
    def run_generator(self):
        super().run_generator()

        if not OUTPUT.exists():
            return

        try:
            stats = normalize_and_order_news_json(OUTPUT)
        except Exception as exc:
            self.status_var.set(
                "news.json wurde erzeugt, die News→Grundlage-Reihenfolge "
                f"konnte aber nicht aufgebaut werden: {exc}"
            )
            return

        self.status_var.set(
            f'news.json erzeugt │ {stats["total"]} Beiträge │ '
            f'{stats["linked_groups"]} verknüpfte Grundlagenfolgen'
        )

        if hasattr(self, "generator_log"):
            try:
                self.generator_log.configure(state="normal")
                self.generator_log.insert(
                    "end",
                    "\n\nTHEMATISCHE ABSPIELFOLGEN 5.11\n"
                    f'✓ {stats["total"]} Beiträge geordnet\n'
                    f'✓ {stats["linked_groups"]} Grundlagen mit News verknüpft\n'
                    f'✓ {stats["recommended_groups"]} Gruppen im empfohlenen Bereich '
                    "(2–5 News)\n"
                    f'• {stats["thin_groups"]} Gruppen mit nur einer News\n'
                    f'• {stats["unlinked_groups"]} Grundlagen ohne News\n'
                    "✓ articles-Array und playbackOrder aktualisiert\n"
                    "✓ contentSchema 5\n",
                )
                if stats["warnings"]:
                    self.generator_log.insert(
                        "end",
                        "Hinweise:\n- " + "\n- ".join(stats["warnings"]) + "\n",
                    )
                self.generator_log.configure(state="disabled")
                self.generator_log.see("end")
            except Exception:
                pass


if __name__ == "__main__":
    app = NewsStudio511()
    app.mainloop()
