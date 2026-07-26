#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.10 – Grundlagenbilder mit didaktischen Skizzenelementen.

Benötigt im selben Ordner:
- news_studio_5_9.py
- news_studio_5_8.py
- news_studio_5_7.py
- news_studio_5_6.py
- news_studio_5_5_2.py und die bisherige Projektstruktur

Version 5.10 ergänzt gegenüber 5.9:
- Prozessskizzen für Grundlagen dürfen nun gezielt didaktische Elemente nutzen
- erlaubt in der Prompterzeugung:
  * Pfeile oder Richtungslinien
  * einfache Symbole
  * kurze fachliche Abkürzungen
  * einzelne Formelzeichen
  * wenige kurze Bezeichnungen
- alles nur sparsam, klar lesbar und in kontrastreichen Graustufen
"""

import importlib.util
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_9.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_9.py wurde nicht gefunden.\n"
        "Lege News Studio 5.10 in denselben Ordner wie Version 5.9."
    )

spec = importlib.util.spec_from_file_location("news_studio_5_9_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("News Studio 5.9 konnte nicht geladen werden.")

base510 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base510
spec.loader.exec_module(base510)

base_app = base510.base_app
read_json_object = base510.read_json_object
write_json_atomic = base510.write_json_atomic
normalize_image_style = base510.normalize_image_style


class NewsStudio510(base510.NewsStudio59):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.10")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.9", "ZUSTAND News Studio 5.10"
        )
        self._replace_widget_text(
            "News Studio 5.9 bereit │ Grundlagen nutzen skizzenhafte Schwarz-Weiß-Bilder",
            "News Studio 5.10 bereit │ Grundlagen nutzen Prozessskizzen mit didaktischen Symbolen"
        )
        self._replace_widget_text(
            "News Studio 5.9 bereit │ Grundlagen nutzen skizzenhafte Schwarz-Weiß-Prozessbilder",
            "News Studio 5.10 bereit │ Grundlagen nutzen Prozessskizzen mit didaktischen Symbolen"
        )
        self.status_var.set(
            "News Studio 5.10 bereit │ Grundlagen erlauben Pfeile, Symbole und Kürzel"
        )

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
            "Die Darstellung soll wie eine hochwertige editorielle "
            "Wissenschaftsskizze wirken: reduziert, ruhig, klar und "
            "wissenschaftsnah. Nutze feine Linien, klare Umrissformen, "
            "dezente Schraffuren und bei Bedarf einfache Querschnitte oder "
            "sichtbare Schichten von Boden, Wasser, Luft, Pflanze oder "
            "Atmosphäre, wenn dies zum Verständnis des konkreten Prozesses "
            "beiträgt.\n\n"
            "Zusätzlich dürfen zur besseren Verständlichkeit einfache visuelle "
            "Erklärungselemente verwendet werden:\n"
            "- klare Pfeile oder Richtungslinien\n"
            "- einfache Symbole\n"
            "- kurze fachliche Abkürzungen\n"
            "- einzelne Formelzeichen\n"
            "- wenige kurze Bezeichnungen für zentrale Prozessbestandteile\n\n"
            "Diese Elemente sollen sparsam, klar lesbar und gestalterisch "
            "integriert sein. Verwende dafür kontrastreiche Graustufen oder "
            "Schwarz-Weiß. Die grafischen Ergänzungen sollen die Skizze "
            "verständlicher machen, aber nicht dominieren.\n\n"
            "Die Darstellung darf leicht modellhaft und didaktisch reduziert "
            "sein, soll aber nicht wie eine bunte Infografik, ein Comic, ein "
            "Kinderbuchbild oder eine technische CAD-Zeichnung wirken. "
            "Sie soll erwachsen, hochwertig und wissenschaftsjournalistisch "
            "erscheinen.\n\n"
            "Darstellungsvorgaben:\n"
            "- vorzugsweise in Schwarz-Weiß oder kontrastreichen Graustufen\n"
            "- ruhiger, heller oder neutraler Hintergrund\n"
            "- klare Hell-Dunkel-Trennung\n"
            "- genau ein dominantes Hauptmotiv\n"
            "- Prozessverständnis durch Bildaufbau und sparsame grafische "
            "Erläuterung\n"
            "- grafische Elemente nur so viel wie nötig\n"
            "- keine Logos, Wasserzeichen oder dekorativen Rahmen\n"
            "- keine Collage und keine geteilte Vorher-nachher-Ansicht\n"
            "- keine überladene Infografik\n\n"
            "Erlaubte Textelemente:\n"
            "- nur sehr kurze fachliche Kürzel, Formelzeichen oder "
            "Einzelbegriffe\n"
            "- keine langen Sätze oder Fließtexte\n"
            "- keine Zahlenkolonnen\n"
            "- keine Legendenkästen mit vielen Einträgen\n\n"
            "Komposition für den Infoscreen:\n"
            "- Hochformat im Seitenverhältnis 8:9.\n"
            "- Für die linke Hälfte eines vertikal geteilten 16:9-Bildschirms.\n"
            "- Auch aus drei bis fünf Metern Entfernung verständlich.\n"
            "- Wichtige Motive mindestens zehn Prozent vom Bildrand entfernt.\n"
            "- Ruhige Komposition mit eindeutiger Blickführung.\n\n"
            "Verbindliche ZUSTAND-Bildsprache für Grundlagen: hochwertige "
            "wissenschaftsjournalistische Skizze in Schwarz-Weiß oder "
            "kontrastreichen Graustufen, reduziert, ruhig, verständlich und "
            "mit unmittelbarer Beziehung zum konkreten Artikelthema.\n\n"
            "Ausgabe: genau ein fertiges Bild im Hochformat 8:9."
        )

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
            if visual_mode == "process-sketch":
                metadata["imageFamily"] = "explainer-sketch"
                metadata["didacticElements"] = {
                    "allowArrows": True,
                    "allowSymbols": True,
                    "allowShortLabels": True,
                    "allowFormulaSigns": True,
                    "colorMode": "grayscale-high-contrast",
                    "textDensity": "low",
                }
                metadata["editorialNote"] = (
                    "Skizzenhafte Schwarz-Weiß-Prozessdarstellung für die Rubrik "
                    "„Natur verstehen“; didaktische Elemente wie Pfeile, Symbole "
                    "und kurze Kürzel sind sparsam erlaubt."
                )
            else:
                metadata["imageFamily"] = "editorial"
            write_json_atomic(Path(path), metadata)

    def build_research_prompt(self, period: str) -> str:
        prompt = super().build_research_prompt(period)
        appendix = """

### Didaktische Elemente in Grundlagenbildern

Für Beiträge mit
"contentType": "explainer" und
"visualMode": "process-sketch"

soll die Bildidee ausdrücklich als wissenschaftsjournalistische
Schwarz-Weiß-Skizze mit sparsamen didaktischen Elementen gedacht werden.

Erlaubt und erwünscht sind dabei:
- klare Pfeile oder Richtungslinien
- einfache Symbole
- kurze fachliche Abkürzungen
- einzelne Formelzeichen
- wenige kurze Bezeichnungen

Diese Elemente sollen in kontrastreichen Graustufen oder Schwarz-Weiß
gehalten sein und die Verständlichkeit des Prozesses erhöhen, ohne die
Darstellung zu überladen.
"""
        if "Didaktische Elemente in Grundlagenbildern" not in prompt:
            prompt += appendix
        return prompt


if __name__ == "__main__":
    app = NewsStudio510()
    app.mainloop()
