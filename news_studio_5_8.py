#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.8 – Beitragstypen und eigene Bildsprache für Grundlagen.

Benötigt im selben Ordner:
- news_studio_5_7.py
- news_studio_5_6.py
- news_studio_5_5_2.py und deren bisherige Basisdateien

Version 5.8 ergänzt:
- contentType: news | explainer | solution | editorial
- visualMode: editorial-photo | process-schematic | symbolic | scientific
- automatische Prozess-Bildprompts für „Natur verstehen“
- Übernahme der Felder in Artikeldateien, Bildmetadaten und news.json
- rückwärtskompatible Standardwerte für ältere Beiträge
"""

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_7.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_7.py wurde nicht gefunden.\n"
        "Lege News Studio 5.8 in denselben Ordner wie Version 5.7."
    )

spec = importlib.util.spec_from_file_location("news_studio_5_7_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("News Studio 5.7 konnte nicht geladen werden.")

base58 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base58
spec.loader.exec_module(base58)

# Modulpfad: 5.7 -> 5.6 -> 5.5.2 -> 5.3 -> 5.2.1 -> 5.1
studio56 = base58.base57
studio552 = studio56.base56
base_app = getattr(studio552, "base_app", None)

tk = studio552.tk
ttk = studio552.ttk
messagebox = studio552.messagebox

PROJECT_ROOT = Path(getattr(studio552, "PROJECT_ROOT", SCRIPT_DIR))
DRAFTS_DIR = Path(
    getattr(studio552, "DRAFTS_DIR", PROJECT_ROOT / "newsredaktion" / "entwuerfe")
)
ARTICLES_DIR = Path(
    getattr(studio552, "ARTICLES_DIR", PROJECT_ROOT / "newsredaktion" / "artikel")
)
IMAGES_DIR = Path(
    getattr(base_app, "BILDER", PROJECT_ROOT / "assets" / "images")
)
OUTPUT = Path(getattr(studio56, "OUTPUT", PROJECT_ROOT / "news.json"))

CONTENT_TYPES = {
    "news": "Nachricht",
    "explainer": "Grundlage / Natur verstehen",
    "solution": "Lösung / Fortschritt",
    "editorial": "Redaktioneller Beitrag",
}
CONTENT_TYPE_BY_LABEL = {label: key for key, label in CONTENT_TYPES.items()}

VISUAL_MODES = {
    "editorial-photo": "Redaktionelles Foto",
    "process-schematic": "Schematische Prozessdarstellung",
    "symbolic": "Symbolische Darstellung",
    "scientific": "Wissenschaftliche Darstellung",
}
VISUAL_MODE_BY_LABEL = {label: key for key, label in VISUAL_MODES.items()}

EXPLAINER_CATEGORY = "Natur verstehen"


def read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def normalized_text(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def normalize_url(value: object) -> str:
    normalizer = getattr(studio552, "normalize_source_url", None)
    if callable(normalizer):
        try:
            return str(normalizer(value))
        except Exception:
            pass
    return str(value or "").strip().lower().rstrip("/")


def joined_keywords(article: dict[str, Any]) -> str:
    value = article.get("keywords", "")
    if isinstance(value, list):
        return " ".join(str(item) for item in value)
    return str(value or "")


def infer_explainer(article: dict[str, Any]) -> bool:
    category = normalized_text(article.get("category"))
    keywords = normalized_text(joined_keywords(article))
    return (
        category in {"natur verstehen", "grundlagen", "grundlage"}
        or "natur verstehen" in keywords
        or "grundlagen" in keywords
    )


def normalize_content_type(
    value: object,
    article: dict[str, Any] | None = None,
) -> str:
    raw = normalized_text(value)
    aliases = {
        "news": "news",
        "nachricht": "news",
        "meldung": "news",
        "explainer": "explainer",
        "grundlage": "explainer",
        "grundlagen": "explainer",
        "natur verstehen": "explainer",
        "solution": "solution",
        "lösung": "solution",
        "loesung": "solution",
        "fortschritt": "solution",
        "editorial": "editorial",
        "redaktion": "editorial",
    }
    if raw in aliases:
        return aliases[raw]
    if article and infer_explainer(article):
        return "explainer"
    return "news"


def normalize_visual_mode(value: object, content_type: str) -> str:
    raw = normalized_text(value)
    aliases = {
        "editorial-photo": "editorial-photo",
        "redaktionelles foto": "editorial-photo",
        "foto": "editorial-photo",
        "process-schematic": "process-schematic",
        "schematische prozessdarstellung": "process-schematic",
        "prozessdarstellung": "process-schematic",
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
    return "process-schematic" if content_type == "explainer" else "editorial-photo"


def normalize_article_fields(article: dict[str, Any]) -> tuple[str, str]:
    content_type = normalize_content_type(article.get("contentType"), article)
    visual_mode = normalize_visual_mode(article.get("visualMode"), content_type)

    article["contentType"] = content_type
    article["visualMode"] = visual_mode

    if content_type == "explainer":
        article["category"] = EXPLAINER_CATEGORY
        article["displayLabel"] = "NATUR VERSTEHEN"
    else:
        if normalized_text(article.get("category")) == normalized_text(EXPLAINER_CATEGORY):
            article.pop("category", None)
        if article.get("displayLabel") == "NATUR VERSTEHEN":
            article.pop("displayLabel", None)

    return content_type, visual_mode


def normalize_news_json(path: Path) -> tuple[int, int]:
    payload = read_json_object(path)
    if payload is None:
        return 0, 0

    articles = payload.get("articles", [])
    explainers = 0
    total = 0
    counts = {"news": 0, "explainer": 0, "solution": 0, "editorial": 0}

    if isinstance(articles, list):
        for article in articles:
            if not isinstance(article, dict):
                continue
            content_type, _visual_mode = normalize_article_fields(article)
            counts[content_type] = counts.get(content_type, 0) + 1
            total += 1
            if content_type == "explainer":
                explainers += 1

    try:
        current_schema = int(payload.get("contentSchema", 0) or 0)
    except (TypeError, ValueError):
        current_schema = 0
    payload["contentSchema"] = max(current_schema, 3)
    payload["contentTypeCounts"] = counts
    write_json_atomic(path, payload)
    return total, explainers


class NewsStudio58(base58.NewsStudio57):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.8")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.7", "ZUSTAND News Studio 5.8"
        )

        self.content_type_var = tk.StringVar(value=CONTENT_TYPES["news"])
        self.visual_mode_var = tk.StringVar(value=VISUAL_MODES["editorial-photo"])
        self._visual_fields_loading = False
        self._add_visual_fields()
        self.content_type_var.trace_add("write", self._content_type_changed)

        self.status_var.set(
            "News Studio 5.8 bereit │ Grundlagen erhalten eigene Prozess-Bildsprache"
        )

    # ---------- Oberfläche ----------
    def _add_visual_fields(self) -> None:
        form = getattr(self, "article_notes", None)
        form = form.master if form is not None else getattr(self, "article_text").master

        box = ttk.LabelFrame(
            form,
            text="Beitragstyp und Bildsprache",
            padding=10,
        )
        box.pack(fill="x", pady=(10, 4))

        content_row = ttk.Frame(box)
        content_row.pack(fill="x", pady=3)
        ttk.Label(content_row, text="Beitragstyp", width=20).pack(side="left")
        ttk.Combobox(
            content_row,
            textvariable=self.content_type_var,
            values=tuple(CONTENT_TYPES.values()),
            state="readonly",
            width=31,
        ).pack(side="left", fill="x", expand=True)

        visual_row = ttk.Frame(box)
        visual_row.pack(fill="x", pady=3)
        ttk.Label(visual_row, text="Bildmodus", width=20).pack(side="left")
        ttk.Combobox(
            visual_row,
            textvariable=self.visual_mode_var,
            values=tuple(VISUAL_MODES.values()),
            state="readonly",
            width=31,
        ).pack(side="left", fill="x", expand=True)

        ttk.Label(
            box,
            text=(
                "Bei „Grundlage / Natur verstehen“ wird automatisch eine "
                "fotorealistisch-schematische Prozessdarstellung vorgeschlagen. "
                "Der Bildmodus hat dann Vorrang vor dem bisherigen Foto-Bildstil."
            ),
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(5, 0))

    def _content_type_code(self) -> str:
        return CONTENT_TYPE_BY_LABEL.get(
            self.content_type_var.get(),
            normalize_content_type(self.content_type_var.get()),
        )

    def _visual_mode_code(self) -> str:
        return VISUAL_MODE_BY_LABEL.get(
            self.visual_mode_var.get(),
            normalize_visual_mode(
                self.visual_mode_var.get(),
                self._content_type_code(),
            ),
        )

    def _set_visual_fields(self, article: dict[str, Any]) -> None:
        self._visual_fields_loading = True
        try:
            content_type = normalize_content_type(article.get("contentType"), article)
            visual_mode = normalize_visual_mode(
                article.get("visualMode"), content_type
            )
            self.content_type_var.set(CONTENT_TYPES[content_type])
            self.visual_mode_var.set(VISUAL_MODES[visual_mode])
        finally:
            self._visual_fields_loading = False

    def _content_type_changed(self, *_args) -> None:
        if self._visual_fields_loading:
            return
        content_type = self._content_type_code()
        current = self._visual_mode_code()
        if content_type == "explainer" and current == "editorial-photo":
            self.visual_mode_var.set(VISUAL_MODES["process-schematic"])
            if hasattr(self, "image_style_var"):
                self.image_style_var.set("Wissenschaft")

    # ---------- Artikel laden und speichern ----------
    def new_article(self):
        result = super().new_article()
        self._set_visual_fields(
            {"contentType": "news", "visualMode": "editorial-photo"}
        )
        return result

    def load_selected_article(self, _event=None):
        result = super().load_selected_article(_event)
        path = getattr(self, "current_article_path", None)
        article = read_json_object(Path(path)) if path else None
        self._set_visual_fields(article or {})
        return result

    def article_payload(self, forced_status=None):
        existing: dict[str, Any] = {}
        path = getattr(self, "current_article_path", None)
        if path:
            existing = read_json_object(Path(path)) or {}

        data = super().article_payload(forced_status)
        content_type = self._content_type_code()
        visual_mode = self._visual_mode_code()

        data["contentType"] = content_type
        data["visualMode"] = visual_mode

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

    # ---------- Bildprompt ----------
    def selected_image_style(self) -> str:
        if (
            hasattr(self, "visual_mode_var")
            and self._visual_mode_code() == "process-schematic"
        ):
            return "Wissenschaft"
        return super().selected_image_style()

    def build_image_prompt(self) -> str:
        if not hasattr(self, "visual_mode_var"):
            return super().build_image_prompt()

        visual_mode = self._visual_mode_code()
        if visual_mode != "process-schematic":
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
            "Bildtyp: fotorealistisch-schematische Prozessdarstellung für die Rubrik "
            "„Natur verstehen“. Zeige nicht nur das sichtbare Ergebnis, sondern den "
            "naturwissenschaftlichen Vorgang selbst. Die Darstellung darf leicht "
            "modellhaft und didaktisch reduziert wirken, muss aber aus realistischen "
            "Materialien, Pflanzen, Wasser, Boden, Luft, Licht oder Landschaft bestehen.\n\n"
            "Stelle den Prozess in einem einzigen zusammenhängenden Bildraum dar. "
            "Nutze ein dominantes Hauptmotiv und höchstens wenige dezente, "
            "halbtransparente Prozessspuren, etwa Verdunstung, Wärmeschimmer, "
            "Luftbewegung, Lichtreflexion oder Stoffaustausch. Prozessspuren ohne "
            "Pfeilspitzen, ohne Beschriftung und ohne technische Diagrammästhetik. "
            "Eine angeschnittene Boden-, Wasser- oder Atmosphärenschicht ist zulässig, "
            "wenn sie zum Verständnis des konkreten Prozesses notwendig ist.\n\n"
            "Die Grundlagenbilder sollen sich deutlich von normalen Nachrichtenfotos "
            "unterscheiden: ruhiger neutraler Hintergrund, leicht freigestelltes Motiv, "
            "klare räumliche Ordnung, reduzierte Farb- und Objektvielfalt. Dennoch "
            "fotorealistisch, glaubwürdig und nicht wie eine Kinderbuchillustration, "
            "3D-Werbegrafik oder Science-Fiction-Szene.\n\n"
            "Komposition für den Infoscreen:\n"
            "- Hochformat im Seitenverhältnis 8:9.\n"
            "- Für die linke Hälfte eines vertikal geteilten 16:9-Bildschirms.\n"
            "- Genau ein klar erkennbares Hauptmotiv.\n"
            "- Auch aus drei bis fünf Metern Entfernung verständlich.\n"
            "- Ruhiger Hintergrund und deutliche Hell-Dunkel-Trennung.\n"
            "- Wichtige Motive mindestens zehn Prozent vom Bildrand entfernt.\n"
            "- Keine Collage und keine geteilte Vorher-nachher-Ansicht.\n"
            "- Keine Schrift, Buchstaben, Zahlen, Pfeile, Diagramme, Infografiken, "
            "Logos, Wasserzeichen oder Rahmen.\n"
            "- Keine Katastrophenästhetik und keine übertriebene Dramatik.\n\n"
            "Verbindliche ZUSTAND-Bildsprache: hochwertige deutschsprachige "
            "Wissenschaftsmagazin-Fotografie, realistische Lichtstimmung, klare "
            "Komposition, realistische Materialien, dezente Tiefenschärfe und eine "
            "unmittelbare Beziehung zum konkreten Artikelthema.\n\n"
            "Ausgabe: genau ein fertiges Bild im Hochformat 8:9, ohne Text im Bild."
        )

    def import_article_image(self, parent=None):
        result = super().import_article_image(parent=parent)
        self._update_image_metadata()
        return result

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
        for path in metadata_files:
            metadata = read_json_object(Path(path))
            if metadata is None:
                continue
            content_type = self._content_type_code()
            visual_mode = self._visual_mode_code()
            metadata["contentType"] = content_type
            metadata["visualMode"] = visual_mode
            metadata["imageFamily"] = (
                "explainer-process"
                if visual_mode == "process-schematic"
                else "editorial"
            )
            if visual_mode == "process-schematic":
                metadata["editorialNote"] = (
                    "Fotorealistisch-schematische Prozessdarstellung für die "
                    "Rubrik „Natur verstehen“; kein dokumentarisches Ereignis."
                )
            write_json_atomic(Path(path), metadata)

    # ---------- Rechercheprompt und Import ----------
    def build_research_prompt(self, period: str) -> str:
        prompt = super().build_research_prompt(period)
        return prompt + """

### Beitragstyp und Bildsprache

Ergänze jeden Artikel zusätzlich um:

"contentType": "news|explainer|solution|editorial",
"visualMode": "editorial-photo|process-schematic|symbolic|scientific"

Verwende "explainer" ausschließlich für zeitunabhängige Grundlagenbeiträge, die
einen naturwissenschaftlichen oder systemischen Zusammenhang erklären, zum
Beispiel Treibhauseffekt, Verdunstung, Evapotranspiration, Albedo,
Clausius-Clapeyron-Beziehung, Kohlenstoffkreislauf oder Ozeanversauerung.

Für "explainer" ist normalerweise "visualMode": "process-schematic" zu wählen.
Aktuelle Meldungen erhalten normalerweise "news" und "editorial-photo".
Belastbare Lösungs- oder Fortschrittsmeldungen dürfen "solution" erhalten.
"""

    def import_research_file(self):
        chosen: dict[str, str] = {"path": ""}
        dialog_owner = (
            getattr(studio552, "BASE_FILEDIALOG", None)
            or getattr(base_app, "filedialog", None)
        )
        original_dialog = getattr(dialog_owner, "askopenfilename", None)

        if not callable(original_dialog):
            return super().import_research_file()

        def capture_dialog(*args, **kwargs):
            selected = original_dialog(*args, **kwargs)
            chosen["path"] = selected or ""
            return selected

        dialog_owner.askopenfilename = capture_dialog
        try:
            result = super().import_research_file()
        finally:
            dialog_owner.askopenfilename = original_dialog

        if chosen["path"]:
            changed = self._sync_visual_fields_from_import(Path(chosen["path"]))
            if changed:
                self.refresh_all()
                self.status_var.set(
                    f"Rechercheimport abgeschlossen │ {changed} Beitrag/Beiträge "
                    "mit Beitragstyp und Bildmodus ergänzt"
                )
        return result

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
            visual_mode = normalize_visual_mode(
                raw.get("visualMode"), content_type
            )
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
                normalize_article_fields(article)
                write_json_atomic(article_path, article)
                changed_paths.add(article_path)

        return len(changed_paths)

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
                f"news.json erzeugt, Darstellungsfelder konnten aber nicht "
                f"normalisiert werden: {exc}"
            )
            return

        self.status_var.set(
            f"news.json erzeugt │ {total} Beiträge, davon {explainers} Grundlagen"
        )
        if hasattr(self, "generator_log"):
            try:
                self.generator_log.configure(state="normal")
                self.generator_log.insert(
                    "end",
                    "\n\nBEITRAGSTYP UND BILDSPRACHE\n"
                    f"✓ {total} Beiträge normalisiert\n"
                    f"✓ {explainers} Grundlagenbeiträge mit eigener Kennzeichnung\n"
                    "✓ contentSchema 3\n",
                )
                self.generator_log.configure(state="disabled")
                self.generator_log.see("end")
            except Exception:
                pass


if __name__ == "__main__":
    app = NewsStudio58()
    app.mainloop()
