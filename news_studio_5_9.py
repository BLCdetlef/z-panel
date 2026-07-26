#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.9 – Grundlagen als skizzenhafte Schwarz-Weiß-Prozessbilder.

Benötigt im selben Ordner:
- news_studio_5_8.py
- news_studio_5_7.py
- news_studio_5_6.py
- news_studio_5_5_2.py und die bisherige Projektstruktur

Version 5.9 ergänzt gegenüber 5.8:
- neuer visualMode: process-sketch
- neuer fixer Grundlagenstil: monochrome-editorial-sketch
- Grundlagen setzen automatisch:
  contentType = explainer
  visualMode = process-sketch
  imageStyle = monochrome-editorial-sketch
- das bisherige Feld „Bildstil“ wird bei Grundlagen deaktiviert,
  damit sich Bildstil und Bildmodus nicht widersprechen
- die Prompterzeugung für Grundlagen erzeugt skizzenhafte
  Schwarz-Weiß-Darstellungen statt fotorealistischer Prozessbilder
"""

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_8.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_8.py wurde nicht gefunden.\n"
        "Lege News Studio 5.9 in denselben Ordner wie Version 5.8."
    )

spec = importlib.util.spec_from_file_location("news_studio_5_8_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("News Studio 5.8 konnte nicht geladen werden.")

base59 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base59
spec.loader.exec_module(base59)

tk = base59.tk
ttk = base59.ttk

CONTENT_TYPES = dict(base59.CONTENT_TYPES)
CONTENT_TYPE_BY_LABEL = dict(base59.CONTENT_TYPE_BY_LABEL)

VISUAL_MODES = {
    "editorial-photo": "Redaktionelles Foto",
    "process-sketch": "Skizzenhafte Prozessdarstellung",
    "symbolic": "Symbolische Darstellung",
    "scientific": "Wissenschaftliche Darstellung",
}
VISUAL_MODE_BY_LABEL = {label: key for key, label in VISUAL_MODES.items()}

IMAGE_STYLE_FIXED_EXPLAINER = "monochrome-editorial-sketch"
IMAGE_STYLE_FIXED_EXPLAINER_LABEL = "Schwarz-Weiß-Skizze"
EXPLAINER_CATEGORY = base59.EXPLAINER_CATEGORY

PROJECT_ROOT = base59.PROJECT_ROOT
DRAFTS_DIR = base59.DRAFTS_DIR
ARTICLES_DIR = base59.ARTICLES_DIR
OUTPUT = base59.OUTPUT
base_app = base59.base_app


def read_json_object(path: Path) -> dict[str, Any] | None:
    return base59.read_json_object(path)


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    base59.write_json_atomic(path, data)


def normalized_text(value: object) -> str:
    return base59.normalized_text(value)


def normalize_url(value: object) -> str:
    return base59.normalize_url(value)


def infer_explainer(article: dict[str, Any]) -> bool:
    return base59.infer_explainer(article)


def normalize_content_type(value: object, article: dict[str, Any] | None = None) -> str:
    return base59.normalize_content_type(value, article)


def normalize_visual_mode(value: object, content_type: str) -> str:
    raw = normalized_text(value)
    aliases = {
        "editorial-photo": "editorial-photo",
        "redaktionelles foto": "editorial-photo",
        "foto": "editorial-photo",
        "process-sketch": "process-sketch",
        "skizzenhafte prozessdarstellung": "process-sketch",
        "prozessskizze": "process-sketch",
        "prozess-skizze": "process-sketch",
        "skizze": "process-sketch",
        "schwarz-weiß-skizze": "process-sketch",
        "schwarz weiss skizze": "process-sketch",
        "process-schematic": "process-sketch",
        "schematische prozessdarstellung": "process-sketch",
        "prozessdarstellung": "process-sketch",
        "symbolic": "symbolic",
        "symbolisch": "symbolic",
        "symbolische darstellung": "symbolic",
        "scientific": "scientific",
        "wissenschaft": "scientific",
        "wissenschaftlich": "scientific",
        "wissenschaftliche darstellung": "scientific",
    }
    if raw in aliases:
        return aliases[raw]
    return "process-sketch" if content_type == "explainer" else "editorial-photo"


def normalize_image_style(value: object, content_type: str, visual_mode: str) -> str:
    raw = normalized_text(value)
    if content_type == "explainer" or visual_mode == "process-sketch":
        return IMAGE_STYLE_FIXED_EXPLAINER
    aliases = {
        "natur": "nature",
        "nature": "nature",
        "symbolisch": "symbolic",
        "symbolic": "symbolic",
        "wissenschaft": "scientific",
        "wissenschaftlich": "scientific",
        "scientific": "scientific",
        "redaktionell": "editorial",
        "editorial": "editorial",
    }
    return aliases.get(raw, str(value or "").strip() or "nature")


def normalize_article_fields(article: dict[str, Any]) -> tuple[str, str, str]:
    content_type = normalize_content_type(article.get("contentType"), article)
    visual_mode = normalize_visual_mode(article.get("visualMode"), content_type)
    image_style = normalize_image_style(article.get("imageStyle"), content_type, visual_mode)

    article["contentType"] = content_type
    article["visualMode"] = visual_mode
    article["imageStyle"] = image_style

    if content_type == "explainer":
        article["category"] = EXPLAINER_CATEGORY
        article["displayLabel"] = "NATUR VERSTEHEN"
    else:
        if normalized_text(article.get("category")) == normalized_text(EXPLAINER_CATEGORY):
            article.pop("category", None)
        if article.get("displayLabel") == "NATUR VERSTEHEN":
            article.pop("displayLabel", None)

    return content_type, visual_mode, image_style


def normalize_news_json(path: Path) -> tuple[int, int]:
    payload = read_json_object(path)
    if payload is None:
        return 0, 0

    articles = payload.get("articles", [])
    explainers = 0
    total = 0
    counts = {"news": 0, "explainer": 0, "solution": 0, "editorial": 0}
    visual_counts = {
        "editorial-photo": 0,
        "process-sketch": 0,
        "symbolic": 0,
        "scientific": 0,
    }

    if isinstance(articles, list):
        for article in articles:
            if not isinstance(article, dict):
                continue
            content_type, visual_mode, _image_style = normalize_article_fields(article)
            counts[content_type] = counts.get(content_type, 0) + 1
            visual_counts[visual_mode] = visual_counts.get(visual_mode, 0) + 1
            total += 1
            if content_type == "explainer":
                explainers += 1

    try:
        current_schema = int(payload.get("contentSchema", 0) or 0)
    except (TypeError, ValueError):
        current_schema = 0
    payload["contentSchema"] = max(current_schema, 4)
    payload["contentTypeCounts"] = counts
    payload["visualModeCounts"] = visual_counts
    write_json_atomic(path, payload)
    return total, explainers


class NewsStudio59(base59.NewsStudio58):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.9")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.8", "ZUSTAND News Studio 5.9"
        )
        self._replace_widget_text(
            "News Studio 5.8 bereit │ Grundlagen erhalten eigene Prozess-Bildsprache",
            "News Studio 5.9 bereit │ Grundlagen nutzen skizzenhafte Schwarz-Weiß-Bilder"
        )
        self._visual_fields_loading = False
        self._replace_visual_mode_choices()
        self._replace_visual_explainer_text()
        self._bind_visual_watchers()
        self._apply_explainer_visual_lock()
        self.status_var.set(
            "News Studio 5.9 bereit │ Grundlagen nutzen skizzenhafte Schwarz-Weiß-Prozessbilder"
        )

    # ---------- UI-Helfer ----------
    def _replace_widget_text(self, old: str, new: str):
        try:
            super()._replace_widget_text(old, new)
        except Exception:
            pass

    def _replace_visual_mode_choices(self) -> None:
        # Alle Comboboxen im Fenster nach den alten Werten durchsuchen.
        def walk(widget):
            yield widget
            for child in widget.winfo_children():
                yield from walk(child)

        old_values = (
            "Redaktionelles Foto",
            "Schematische Prozessdarstellung",
            "Symbolische Darstellung",
            "Wissenschaftliche Darstellung",
        )
        new_values = tuple(VISUAL_MODES.values())

        for widget in walk(self):
            if widget.winfo_class() == "TCombobox":
                try:
                    values = tuple(widget.cget("values"))
                except Exception:
                    continue
                if values == old_values or "Schematische Prozessdarstellung" in values:
                    try:
                        widget.configure(values=new_values)
                    except Exception:
                        pass

        # StringVar auf neue Auswahl setzen
        current_label = self.visual_mode_var.get().strip()
        if current_label == "Schematische Prozessdarstellung":
            self.visual_mode_var.set(VISUAL_MODES["process-sketch"])

    def _replace_visual_explainer_text(self) -> None:
        self._replace_widget_text(
            "Bei „Grundlage / Natur verstehen“ wird automatisch eine "
            "fotorealistisch-schematische Prozessdarstellung vorgeschlagen. "
            "Der Bildmodus hat dann Vorrang vor dem bisherigen Foto-Bildstil.",
            "Bei „Grundlage / Natur verstehen“ wird automatisch eine "
            "skizzenhafte Schwarz-Weiß-Prozessdarstellung gesetzt. "
            "Der bisherige Bildstil wird dann automatisch auf "
            "„Schwarz-Weiß-Skizze“ gesetzt und im Studio deaktiviert."
        )

    def _bind_visual_watchers(self) -> None:
        self.content_type_var.trace_add("write", self._on_visual_rules_change)
        self.visual_mode_var.trace_add("write", self._on_visual_rules_change)

    def _find_combobox_for_variable(self, variable: tk.StringVar):
        var_name = str(variable)
        found = None

        def walk(widget):
            nonlocal found
            if found is not None:
                return
            try:
                if widget.winfo_class() == "TCombobox":
                    tv = str(widget.cget("textvariable"))
                    if tv == var_name:
                        found = widget
                        return
            except Exception:
                pass
            for child in widget.winfo_children():
                walk(child)

        walk(self)
        return found

    def _image_style_value_set(self, label: str) -> None:
        if hasattr(self, "image_style_var"):
            try:
                self.image_style_var.set(label)
            except Exception:
                pass

    def _image_style_value_get(self) -> str:
        if hasattr(self, "image_style_var"):
            try:
                return str(self.image_style_var.get()).strip()
            except Exception:
                return ""
        return ""

    def _set_image_style_state(self, state: str) -> None:
        if not hasattr(self, "_image_style_combo"):
            self._image_style_combo = self._find_combobox_for_variable(self.image_style_var) if hasattr(self, "image_style_var") else None
        combo = getattr(self, "_image_style_combo", None)
        if combo is not None:
            try:
                combo.configure(state=state)
            except Exception:
                pass

    def _apply_explainer_visual_lock(self) -> None:
        if getattr(self, "_visual_fields_loading", False):
            return

        content_type = self._content_type_code()
        visual_mode = self._visual_mode_code()

        if content_type == "explainer":
            self._visual_fields_loading = True
            try:
                if visual_mode != "process-sketch":
                    self.visual_mode_var.set(VISUAL_MODES["process-sketch"])
                self._image_style_value_set(IMAGE_STYLE_FIXED_EXPLAINER_LABEL)
                self._set_image_style_state("disabled")
            finally:
                self._visual_fields_loading = False
        else:
            if self._image_style_value_get() == IMAGE_STYLE_FIXED_EXPLAINER_LABEL:
                # Bei Rückwechsel auf normale Beiträge wieder eine sinnvolle freie Standardwahl setzen.
                self._image_style_value_set("Natur")
            self._set_image_style_state("readonly")

    def _on_visual_rules_change(self, *_args) -> None:
        self._apply_explainer_visual_lock()

    # ---------- Codes ----------
    def _content_type_code(self) -> str:
        return CONTENT_TYPE_BY_LABEL.get(
            self.content_type_var.get(),
            normalize_content_type(self.content_type_var.get()),
        )

    def _visual_mode_code(self) -> str:
        return VISUAL_MODE_BY_LABEL.get(
            self.visual_mode_var.get(),
            normalize_visual_mode(self.visual_mode_var.get(), self._content_type_code()),
        )

    # ---------- Laden / Speichern ----------
    def _set_visual_fields(self, article: dict[str, Any]) -> None:
        self._visual_fields_loading = True
        try:
            content_type = normalize_content_type(article.get("contentType"), article)
            visual_mode = normalize_visual_mode(article.get("visualMode"), content_type)
            image_style = normalize_image_style(article.get("imageStyle"), content_type, visual_mode)
            self.content_type_var.set(CONTENT_TYPES[content_type])
            self.visual_mode_var.set(VISUAL_MODES[visual_mode])
            if image_style == IMAGE_STYLE_FIXED_EXPLAINER:
                self._image_style_value_set(IMAGE_STYLE_FIXED_EXPLAINER_LABEL)
            elif image_style == "nature":
                self._image_style_value_set("Natur")
            elif image_style == "symbolic":
                self._image_style_value_set("Symbolisch")
            elif image_style == "scientific":
                self._image_style_value_set("Wissenschaft")
            elif image_style == "editorial":
                self._image_style_value_set("Natur")
            elif image_style:
                self._image_style_value_set(str(image_style))
        finally:
            self._visual_fields_loading = False
        self._apply_explainer_visual_lock()

    def new_article(self):
        result = super().new_article()
        self._set_visual_fields(
            {
                "contentType": "news",
                "visualMode": "editorial-photo",
                "imageStyle": "nature",
            }
        )
        return result

    def load_selected_article(self, _event=None):
        result = super().load_selected_article(_event)
        path = getattr(self, "current_article_path", None)
        article = read_json_object(Path(path)) if path else None
        self._set_visual_fields(article or {})
        return result

    def selected_image_style(self) -> str:
        content_type = self._content_type_code()
        visual_mode = self._visual_mode_code()
        if content_type == "explainer" or visual_mode == "process-sketch":
            return IMAGE_STYLE_FIXED_EXPLAINER_LABEL
        return super().selected_image_style()

    def article_payload(self, forced_status=None):
        existing: dict[str, Any] = {}
        path = getattr(self, "current_article_path", None)
        if path:
            existing = read_json_object(Path(path)) or {}

        data = super().article_payload(forced_status)
        content_type = self._content_type_code()
        visual_mode = self._visual_mode_code()
        image_style = normalize_image_style(
            self.selected_image_style(),
            content_type,
            visual_mode,
        )

        data["contentType"] = content_type
        data["visualMode"] = visual_mode
        data["imageStyle"] = image_style

        old_category = str(existing.get("category", "") or "").strip()
        if content_type == "explainer":
            data["category"] = EXPLAINER_CATEGORY
            data["displayLabel"] = "NATUR VERSTEHEN"
        elif content_type == "solution":
            data["category"] = (
                old_category
                if old_category and normalized_text(old_category) != normalized_text(EXPLAINER_CATEGORY)
                else "Lösung"
            )
            data.pop("displayLabel", None)
        elif old_category and normalized_text(old_category) != normalized_text(EXPLAINER_CATEGORY):
            data["category"] = old_category
            data.pop("displayLabel", None)
        else:
            data.pop("category", None)
            data.pop("displayLabel", None)

        return data

    # ---------- Prompt ----------
    def build_image_prompt(self) -> str:
        if not hasattr(self, "visual_mode_var"):
            return super().build_image_prompt()

        visual_mode = self._visual_mode_code()
        if visual_mode != "process-sketch":
            return super().build_image_prompt()

        title = self.article_vars["title"].get().strip()
        summary = self.article_vars["summary"].get().strip()
        boundary = self.article_vars["planetaryBoundary"].get().strip()
        keywords = self.article_vars["keywords"].get().strip()

        hint_function = getattr(base_app, "article_image_hint", None)
        hint = (
            hint_function(title, summary, keywords, boundary)
            if callable(hint_function)
            else "der im Artikel beschriebene naturwissenschaftliche Prozess"
        )

        return (
            "Erzeuge ein einzelnes Titelbild für einen öffentlichen Infoscreen.\n\n"
            f"Artikelthema: {title or 'noch ohne Titel'}.\n"
            f"Kernaussage: {summary or 'noch keine Kurzfassung'}.\n"
            f"Inhaltlicher Ausgangspunkt: {hint}.\n"
            f"Schlagwörter: {keywords or 'Natur verstehen, Grundlagen'}.\n\n"
            "Bildtyp: skizzenhafte Prozessdarstellung für die Rubrik "
            "„Natur verstehen“. Zeige nicht primär das sichtbare Ergebnis, "
            "sondern den naturwissenschaftlichen Vorgang, das Naturgesetz oder "
            "den systemischen Zusammenhang selbst.\n\n"
            "Die Darstellung soll wie eine hochwertige editorielle Schwarz-Weiß-Skizze "
            "wirken: reduziert, ruhig, klar und wissenschaftsnah. Nutze feine Linien, "
            "dezente Schraffuren, klare Umrissformen und bei Bedarf einfache Querschnitte "
            "oder sichtbare Schichten von Boden, Wasser, Luft, Pflanze oder Atmosphäre, "
            "wenn dies zum Verständnis des konkreten Prozesses beiträgt.\n\n"
            "Keine bunte Infografik, kein Comic, keine technische CAD-Zeichnung und "
            "keine fotorealistische Fotoästhetik. Die Illustration darf leicht modellhaft "
            "und didaktisch reduziert sein, soll aber erwachsen, hochwertig und "
            "wissenschaftsjournalistisch wirken.\n\n"
            "Darstellungsvorgaben:\n"
            "- vorzugsweise in Schwarz-Weiß oder feinen Graustufen\n"
            "- ruhiger, heller oder neutraler Hintergrund\n"
            "- klare Hell-Dunkel-Trennung\n"
            "- genau ein dominantes Hauptmotiv\n"
            "- Prozessverständnis durch Bildaufbau und Form, nicht durch Text\n"
            "- keine Schrift, keine Buchstaben, keine Zahlen\n"
            "- keine Pfeile, keine Diagramme, keine Infografik\n"
            "- keine Logos, Wasserzeichen oder Rahmen\n"
            "- keine Collage und keine geteilte Vorher-nachher-Ansicht\n\n"
            "Komposition für den Infoscreen:\n"
            "- Hochformat im Seitenverhältnis 8:9.\n"
            "- Für die linke Hälfte eines vertikal geteilten 16:9-Bildschirms.\n"
            "- Auch aus drei bis fünf Metern Entfernung verständlich.\n"
            "- Wichtige Motive mindestens zehn Prozent vom Bildrand entfernt.\n"
            "- Ruhige Komposition mit eindeutiger Blickführung.\n\n"
            "Verbindliche ZUSTAND-Bildsprache für Grundlagen: hochwertige "
            "wissenschaftsjournalistische Skizze in Schwarz-Weiß, reduziert, ruhig, "
            "verständlich und mit unmittelbarer Beziehung zum konkreten Artikelthema.\n\n"
            "Ausgabe: genau ein fertiges Bild im Hochformat 8:9, ohne Text im Bild."
        )

    # ---------- Bildmetadaten ----------
    def _update_image_metadata(self) -> None:
        image_id = self.article_vars["imageId"].get().strip()
        if not image_id:
            return
        matcher = getattr(base_app, "image_matches", None)
        if not callable(matcher):
            return
        try:
            _images, metadata_files = matcher(image_id)
        except Exception:
            return

        content_type = self._content_type_code()
        visual_mode = self._visual_mode_code()
        image_style = normalize_image_style(
            self.selected_image_style(),
            content_type,
            visual_mode,
        )

        for path in metadata_files:
            metadata = read_json_object(Path(path))
            if metadata is None:
                continue
            metadata["contentType"] = content_type
            metadata["visualMode"] = visual_mode
            metadata["imageStyle"] = image_style
            metadata["imageFamily"] = (
                "explainer-sketch"
                if visual_mode == "process-sketch"
                else "editorial"
            )
            if visual_mode == "process-sketch":
                metadata["editorialNote"] = (
                    "Skizzenhafte Schwarz-Weiß-Prozessdarstellung für die Rubrik "
                    "„Natur verstehen“; kein dokumentarisches Ereignis."
                )
            write_json_atomic(Path(path), metadata)

    # ---------- Rechercheimport ----------
    def _sync_visual_fields_from_import(self, path: Path) -> int:
        payload = read_json_object(path)
        if payload is None:
            return 0
        raw_articles = payload.get("articles", [])
        if not isinstance(raw_articles, list):
            return 0

        article_paths = []
        for folder in (DRAFTS_DIR, ARTICLES_DIR):
            if folder.exists():
                article_paths.extend(
                    item for item in folder.glob("*.json")
                    if item.name.lower() != "index.json"
                    and not item.name.lower().endswith("_vorlage.json")
                )

        by_url: dict[str, list[Path]] = {}
        by_title: dict[str, list[Path]] = {}
        for article_path in article_paths:
            article = read_json_object(article_path)
            if article is None:
                continue
            url = normalize_url(article.get("sourceUrl"))
            title = normalized_text(article.get("title"))
            if url:
                by_url.setdefault(url, []).append(article_path)
            if title:
                by_title.setdefault(title, []).append(article_path)

        changed_paths: set[Path] = set()
        for raw in raw_articles:
            if not isinstance(raw, dict):
                continue
            content_type = normalize_content_type(raw.get("contentType"), raw)
            visual_mode = normalize_visual_mode(raw.get("visualMode"), content_type)
            image_style = normalize_image_style(raw.get("imageStyle"), content_type, visual_mode)

            url = normalize_url(raw.get("sourceUrl"))
            title = normalized_text(raw.get("title"))
            matches = by_url.get(url, []) if url else []
            if not matches and title:
                matches = by_title.get(title, [])

            for article_path in matches:
                article = read_json_object(article_path)
                if article is None:
                    continue
                article["contentType"] = content_type
                article["visualMode"] = visual_mode
                article["imageStyle"] = image_style
                normalize_article_fields(article)
                write_json_atomic(article_path, article)
                changed_paths.add(article_path)

        return len(changed_paths)

    def build_research_prompt(self, period: str) -> str:
        prompt = super().build_research_prompt(period)
        appendix = """

### Aktualisierte Grundlagen-Bildsprache

Ergänze jeden Artikel zusätzlich um:

"contentType": "news|explainer|solution|editorial",
"visualMode": "editorial-photo|process-sketch|symbolic|scientific",
"imageStyle": "nature|symbolic|scientific|editorial|monochrome-editorial-sketch"

Für zeitunabhängige Grundlagenbeiträge mit naturwissenschaftlichen oder
systemischen Zusammenhängen (z. B. Treibhauseffekt, Verdunstung,
Evapotranspiration, Albedo, Ozeanversauerung) verwende:
"contentType": "explainer",
"visualMode": "process-sketch",
"imageStyle": "monochrome-editorial-sketch"

Diese Grundlagenbilder sind als skizzenhafte, schwarz-weiße,
wissenschaftsjournalistische Prozessdarstellungen gedacht.
"""
        if "Aktualisierte Grundlagen-Bildsprache" not in prompt:
            prompt += appendix
        return prompt

    # ---------- news.json ----------
    def run_generator(self):
        before = OUTPUT.read_bytes() if OUTPUT.exists() else None
        super().run_generator()
        after = OUTPUT.read_bytes() if OUTPUT.exists() else None

        if after is None or after == before:
            return

        try:
            total, explainers = normalize_news_json(OUTPUT)
        except Exception as exc:
            self.status_var.set(
                f"news.json erzeugt, neue Darstellungsfelder konnten aber nicht "
                f"normalisiert werden: {exc}"
            )
            return

        self.status_var.set(
            f"news.json erzeugt │ {total} Beiträge, davon {explainers} Grundlagen "
            f"mit Prozessskizzen"
        )
        if hasattr(self, "generator_log"):
            try:
                self.generator_log.configure(state="normal")
                self.generator_log.insert(
                    "end",
                    "\n\nBILDSPRACHE GRUNDLAGEN 5.9\n"
                    f"✓ {total} Beiträge normalisiert\n"
                    f"✓ {explainers} Grundlagenbeiträge mit Schwarz-Weiß-Skizzen\n"
                    "✓ contentSchema 4\n",
                )
                self.generator_log.configure(state="disabled")
                self.generator_log.see("end")
            except Exception:
                pass


if __name__ == "__main__":
    app = NewsStudio59()
    app.mainloop()
