#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.6 – redaktionelle Zwischenscreens.

Benötigt im selben Ordner:
- news_studio_5_5_2.py
- dessen bisherige Basisdateien

Version 5.6 nutzt die bereits vorhandenen Felder „Leitbild“ und
„Redaktionskodex“. Beim erfolgreichen Erzeugen von news.json werden daraus
redaktionelle Zwischenscreens. Es entstehen keine doppelten Texteingaben.
"""

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_5_2.py"
if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_5_2.py wurde nicht gefunden.\n"
        "Lege News Studio 5.6 in denselben Ordner wie Version 5.5.2."
    )

spec = importlib.util.spec_from_file_location("news_studio_5_5_2_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("News Studio 5.5.2 konnte nicht geladen werden.")
base56 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base56
spec.loader.exec_module(base56)

PROJECT_ROOT = Path(getattr(base56, "PROJECT_ROOT", SCRIPT_DIR))
base_app = getattr(base56, "base_app", None)
OUTPUT = Path(getattr(base_app, "OUTPUT", PROJECT_ROOT / "news.json"))

ARTICLE_SECONDS = 30
EDITORIAL_SECONDS = 18
EDITORIAL_EVERY = 8


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def clean_one_line(value: object, limit: int = 120) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit].rstrip()


def infer_source_title(value: object) -> str:
    """Gewinnt aus dem vorhandenen Quellenfeld eine knappe Herausgeberzeile."""
    lines = [line.strip(" •\t") for line in str(value or "").splitlines()]
    for line in lines:
        if not line or line.lower().startswith(("http://", "https://", "url:")):
            continue
        lowered = line.lower()
        for prefix in ("herausgeber:", "institution:", "quelle:"):
            if lowered.startswith(prefix):
                return clean_one_line(line[len(prefix):], 100)
    for line in lines:
        if line and "http://" not in line.lower() and "https://" not in line.lower():
            return clean_one_line(line, 100)
    return ""


def build_editorial_screens(editorial_data: dict[str, Any]) -> list[dict[str, Any]]:
    guide = editorial_data.get("guide", {})
    if not isinstance(guide, dict):
        guide = {}

    mission = str(guide.get("mission", "") or "").strip()
    code = str(guide.get("code", "") or "").strip()
    screens: list[dict[str, Any]] = []

    if mission:
        screens.append(
            {
                "id": "redaktion_leitbild",
                "type": "editorial",
                "editorialType": "mission",
                "label": "Leitbild",
                "kicker": "ZUSTAND · Wofür wir arbeiten",
                "title": "Wofür ZUSTAND steht",
                "text": mission,
                "visualLabel": "Leitbild",
                "durationSeconds": EDITORIAL_SECONDS,
                "enabled": True,
            }
        )

    if code:
        screens.append(
            {
                "id": "redaktion_kodex",
                "type": "editorial",
                "editorialType": "code",
                "label": "Redaktionskodex",
                "kicker": "ZUSTAND · So arbeiten wir",
                "title": "Unser Redaktionskodex",
                "text": code,
                "visualLabel": "Kodex",
                "durationSeconds": 24,
                "enabled": True,
            }
        )

    return screens


def augment_news_payload(
    payload: dict[str, Any], editorial_data: dict[str, Any]
) -> dict[str, Any]:
    articles = payload.get("articles", [])
    article_editorial = editorial_data.get("articles", {})
    if not isinstance(article_editorial, dict):
        article_editorial = {}

    if isinstance(articles, list):
        for article in articles:
            if not isinstance(article, dict):
                continue
            article_id = str(article.get("id", "") or "").strip()
            details = article_editorial.get(article_id, {})
            if not isinstance(details, dict):
                continue

            source_type = clean_one_line(details.get("sourceType"), 90)
            connection = str(details.get("screenConnection", "") or "").strip()
            source_title = infer_source_title(details.get("sources"))

            if source_type:
                article["sourceType"] = source_type
            else:
                article.pop("sourceType", None)

            if connection:
                article["screenConnection"] = connection
            else:
                article.pop("screenConnection", None)

            if source_title and not str(article.get("sourceTitle", "") or "").strip():
                article["sourceTitle"] = source_title

    screens = build_editorial_screens(editorial_data)
    payload["contentSchema"] = 2
    payload["rotation"] = {
        "articleSeconds": ARTICLE_SECONDS,
        "editorialSeconds": EDITORIAL_SECONDS,
        "editorialEvery": EDITORIAL_EVERY,
    }
    payload["editorialScreenCount"] = len(screens)
    payload["editorialScreens"] = screens
    payload["editorialGeneratedAt"] = now_iso()
    return payload


def augment_news_json(editorial_data: dict[str, Any]) -> tuple[bool, str]:
    if not OUTPUT.exists():
        return False, "news.json wurde nicht gefunden."
    try:
        payload = json.loads(OUTPUT.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise ValueError("news.json enthält kein JSON-Objekt.")
        augment_news_payload(payload, editorial_data)
        temp = OUTPUT.with_suffix(".json.tmp")
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temp.replace(OUTPUT)
        count = len(payload.get("editorialScreens", []))
        return True, f"{count} redaktionelle Zwischenscreen(s) ergänzt."
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return False, f"Redaktionelle Screens konnten nicht ergänzt werden: {exc}"


class NewsStudio56(base56.NewsStudio552):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.6")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.5.2", "ZUSTAND News Studio 5.6"
        )
        self._replace_widget_text(
            (
                "Hier werden Leitbild, Redaktionsregeln und die Zusammenhänge hinter "
                "den Meldungen dauerhaft festgehalten. Die Angaben bleiben lokal und "
                "werden noch nicht automatisch auf dem Infoscreen veröffentlicht."
            ),
            (
                "Hier werden Leitbild, Redaktionsregeln und die Zusammenhänge hinter "
                "den Meldungen dauerhaft festgehalten. Leitbild und Redaktionskodex "
                "werden beim Erzeugen von news.json automatisch als ruhige "
                "Zwischenscreens veröffentlicht."
            ),
        )
        self.status_var.set(
            "News Studio 5.6 bereit │ Leitbild und Redaktionskodex werden in news.json übernommen"
        )

    def run_generator(self):
        before = OUTPUT.read_bytes() if OUTPUT.exists() else None
        super().run_generator()
        after = OUTPUT.read_bytes() if OUTPUT.exists() else None

        # Bei einem Generatorfehler bleibt die bestehende news.json unverändert.
        if after is None or after == before:
            return

        # Neueste Eingaben aus dem Reiter Redaktion übernehmen, auch wenn direkt
        # vor dem Veröffentlichen noch nicht zu einem anderen Reiter gewechselt wurde.
        if hasattr(self, "editorial_guide_widgets"):
            for key, widget in self.editorial_guide_widgets.items():
                self.editorial_data.setdefault("guide", {})[key] = widget.get(
                    "1.0", "end"
                ).strip()
            self.editorial_data["updatedAt"] = now_iso()
            base56.write_editorial_file(self.editorial_data)

        success, message = augment_news_json(self.editorial_data)
        self.status_var.set(
            f"news.json erzeugt │ {message}" if success else message
        )
        if hasattr(self, "generator_log"):
            try:
                self.generator_log.configure(state="normal")
                self.generator_log.insert(
                    "end",
                    "\n\nREDAKTIONELLE ZWISCHENSCREENS\n"
                    + ("✓ " if success else "⚠ ")
                    + message,
                )
                self.generator_log.configure(state="disabled")
                self.generator_log.see("end")
            except Exception:
                pass


if __name__ == "__main__":
    app = NewsStudio56()
    app.mainloop()
