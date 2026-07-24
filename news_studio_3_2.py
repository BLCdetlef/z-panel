#!/usr/bin/env python3
from __future__ import annotations

"""
ZUSTAND News Studio 3.2

Erweiterung von News Studio 3.1:

- Titelbilder standardmäßig im Hochformat 8:9
- optimiert für die linke Hälfte eines vertikal geteilten 16:9-Infoscreens
- auswählbare Bildstile: Automatisch, Natur, Wissenschaft, Symbolisch
- automatische Stilwahl anhand von Titel, Kurztext, Grenze und Schlagwörtern
- einheitlicher Prompt-Baukasten mit Sicherheitsabstand und klarer Komposition

Die Datei wird neben news_studio_3_1.py und news_studio_3_0.py abgelegt.
"""

import importlib.util
import sys
import unicodedata
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

BASE_CANDIDATES = (
    SCRIPT_DIR / "news_studio_3_1.py",
    SCRIPT_DIR / "news_studio_3_1(1).py",
)
BASE_SCRIPT = next((path for path in BASE_CANDIDATES if path.exists()), None)

if BASE_SCRIPT is None:
    raise SystemExit(
        "news_studio_3_1.py wurde nicht gefunden.\n"
        "Lege news_studio_3_2.py in denselben Ordner wie "
        "news_studio_3_1.py und news_studio_3_0.py."
    )

spec = importlib.util.spec_from_file_location("news_studio_3_1_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("news_studio_3_1.py konnte nicht geladen werden.")

base31 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base31
spec.loader.exec_module(base31)

base = base31.base

IMAGE_STYLES = ("Automatisch", "Natur", "Wissenschaft", "Symbolisch")

STYLE_HINTS = {
    "Natur": (
        "Nutze eine natürliche, glaubwürdige Szenerie mit Landschaft, Tier, Pflanze, "
        "Wasser, Boden oder Himmel. Die Darstellung soll ruhig und nicht romantisierend sein."
    ),
    "Wissenschaft": (
        "Nutze eine glaubwürdige wissenschaftliche Bildsprache, etwa Atmosphäre, "
        "Messinstrumente, Proben, Modelle oder Prozesse. Keine Science-Fiction-Ästhetik."
    ),
    "Symbolisch": (
        "Nutze eine klare, zurückhaltende visuelle Metapher. Die Metapher soll sofort "
        "verständlich, fotorealistisch und nicht plakativ oder werblich wirken."
    ),
}

AUTO_STYLE_TERMS = {
    "Wissenschaft": (
        "aerosol", "atmosphäre", "atmosphare", "halogen", "chemie", "stickoxid",
        "modellstudie", "messung", "labor", "mikroplastik", "pfas", "emission",
        "nährstoff", "nahrstoff", "biogeochem", "ozon",
    ),
    "Symbolisch": (
        "demokratie", "bildung", "gemeinwohl", "gerechtigkeit", "frieden",
        "zusammenarbeit", "glück", "gluck", "suffizienz", "postwachstum",
        "parlament", "lobbyismus", "gesellschaft",
    ),
    "Natur": (
        "biodiversität", "biodiversitat", "vogel", "wald", "ozean", "meer",
        "wasser", "arten", "ökosystem", "okosystem", "klima", "boden",
        "pflanze", "tier", "landnutzung",
    ),
}


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.lower().split())


def automatic_style(title: str, summary: str, boundary: str, keywords: str) -> str:
    haystack = normalize(f"{title} {summary} {boundary} {keywords}")
    for style in ("Wissenschaft", "Symbolisch", "Natur"):
        if any(term in haystack for term in AUTO_STYLE_TERMS[style]):
            return style
    return "Natur"


class NewsStudio32(base31.NewsStudio31):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 3.2")
        self.image_style_var = base.tk.StringVar(value="Automatisch")
        self._add_image_style_selector()
        self._replace_widget_text("ZUSTAND News Studio 3.1", "ZUSTAND News Studio 3.2")
        self._replace_widget_text(
            "1. Bildprompt vorbereiten",
            "1. Bildprompt 8:9 vorbereiten",
        )
        self.status_var.set(
            "News Studio 3.2 bereit │ Recherche, automatische IDs und 8:9-Bildworkflow aktiv"
        )

    def _find_widget_by_text(self, text: str):
        def walk(widget):
            try:
                if widget.cget("text") == text:
                    return widget
            except Exception:
                pass
            for child in widget.winfo_children():
                result = walk(child)
                if result is not None:
                    return result
            return None
        return walk(self)

    def _add_image_style_selector(self) -> None:
        prompt_button = self._find_widget_by_text("1. Bildprompt vorbereiten")
        if prompt_button is None:
            return

        button_row = prompt_button.master
        image_box = button_row.master

        style_row = base.ttk.Frame(image_box)
        # Vor den Schaltflächen einfügen.
        style_row.pack(fill="x", pady=(7, 2), before=button_row)

        base.ttk.Label(style_row, text="Bildstil", width=20).pack(side="left")
        style_box = base.ttk.Combobox(
            style_row,
            textvariable=self.image_style_var,
            values=IMAGE_STYLES,
            state="readonly",
            width=20,
        )
        style_box.pack(side="left")

        base.ttk.Label(
            style_row,
            text="Automatisch wählt Natur, Wissenschaft oder Symbolisch.",
        ).pack(side="left", padx=(10, 0))

    def selected_image_style(self) -> str:
        requested = self.image_style_var.get().strip() or "Automatisch"
        if requested != "Automatisch":
            return requested

        title = self.article_vars["title"].get().strip()
        summary = self.summary_text.get("1.0", "end").strip()
        boundary = self.article_vars["planetaryBoundary"].get().strip()
        keywords = self.article_vars["keywords"].get().strip()
        return automatic_style(title, summary, boundary, keywords)

    def build_image_prompt(self) -> str:
        title = self.article_vars["title"].get().strip()
        summary = self.summary_text.get("1.0", "end").strip()
        boundary = self.article_vars["planetaryBoundary"].get().strip()
        keywords = self.article_vars["keywords"].get().strip()

        hint = base.BOUNDARY_IMAGE_HINTS.get(
            boundary,
            "eine natürliche, leicht verständliche Assoziation zum Artikel",
        )
        style = self.selected_image_style()
        style_hint = STYLE_HINTS.get(style, STYLE_HINTS["Natur"])

        subject = (
            "Erzeuge ein einzelnes Titelbild für einen öffentlichen Infoscreen.\n\n"
            f"Artikelthema: {title or 'noch ohne Titel'}.\n"
            f"Kernaussage: {summary or 'noch keine Kurzfassung'}.\n"
            f"Mögliche Bildassoziationen: {hint}.\n"
            f"Gewählter Bildstil: {style}. {style_hint}"
        )
        if keywords:
            subject += f"\nSchlagwörter: {keywords}."

        return (
            f"{subject}\n\n"
            "Zeige keine konkrete Nachrichtenszene und erfinde kein dokumentarisches "
            "Ereignis. Entwickle stattdessen eine natürliche, glaubwürdige und "
            "fotorealistische Assoziation, die den Inhalt auf den ersten Blick "
            "verständlich macht. Menschen nur dann zeigen, wenn sie inhaltlich "
            "sinnvoll sind; dann respektvoll, alltäglich und nicht posierend.\n\n"
            "Komposition für den Infoscreen:\n"
            "- Hochformat im Seitenverhältnis 8:9.\n"
            "- Das Bild füllt die linke Hälfte eines vertikal geteilten 16:9-Bildschirms.\n"
            "- Genau ein dominantes, klar erkennbares Hauptmotiv.\n"
            "- Auch aus drei bis fünf Metern Entfernung verständlich.\n"
            "- Ruhiger Hintergrund und deutliche Hell-Dunkel-Trennung.\n"
            "- Wichtige Motive mindestens zehn Prozent vom Bildrand entfernt.\n"
            "- Keine Schrift, Zahlen, Diagramme, Logos, Wasserzeichen, Rahmen oder Collagen.\n"
            "- Keine überladene Komposition und keine gestellte Werbeszene.\n\n"
            f"Verbindliche ZUSTAND-Bildsprache: {base.ZUSTAND_IMAGE_STYLE}\n\n"
            "Ausgabe: genau ein fertiges Bild im Hochformat 8:9, ohne Text im Bild."
        )


if __name__ == "__main__":
    NewsStudio32().mainloop()
