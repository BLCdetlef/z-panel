#!/usr/bin/env python3
from __future__ import annotations

"""Z-PANEL 5.1 – sichtbare Kennzeichnung der Rubrik „Natur verstehen“.

Die Datei einmal direkt im Z-PANEL-Projektordner starten.
Sie erwartet dort:
- app.js
- styles.css
- optional news.json

Vor jeder Änderung wird eine Sicherung unter backups/ angelegt.
"""

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

JS_MARKER = "/* Z-PANEL 5.1: Beitragstypen und Grundlagenrubrik */"
CSS_START = "/* Z-PANEL 5.1 GRUNDLAGEN START */"
CSS_END = "/* Z-PANEL 5.1 GRUNDLAGEN ENDE */"

CSS_PATCH = r"""
.stage.is-explainer .story {
  background:
    linear-gradient(135deg, rgba(75, 163, 150, .09), transparent 44%),
    var(--panel);
  box-shadow: inset 5px 0 0 rgba(75, 163, 150, .78);
}

.stage.is-explainer #boundary-badge {
  letter-spacing: .13em;
  text-transform: uppercase;
}

.stage.is-explainer .article-meta {
  letter-spacing: .055em;
}

.stage.is-explainer .visual {
  background:
    radial-gradient(circle at 50% 42%, rgba(213, 231, 224, .16), transparent 58%),
    #15201c;
}

.stage.is-explainer .article-image {
  object-position: center center;
}

@media (max-width: 760px) {
  .stage.is-explainer .story {
    box-shadow: inset 0 5px 0 rgba(75, 163, 150, .78);
  }
}
"""


def find_project_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "app.js").is_file() and (candidate / "styles.css").is_file():
            return candidate
    raise FileNotFoundError(
        "Kein Z-PANEL-Projektordner gefunden. Lege das Skript in den Ordner "
        "mit app.js und styles.css."
    )


def backup_files(root: Path, files: list[Path]) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = root / "backups" / f"vor_z_panel_5_1_{stamp}"
    target.mkdir(parents=True, exist_ok=True)
    for path in files:
        if path.exists():
            shutil.copy2(path, target / path.name)
    return target


def patch_app_js(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    if JS_MARKER in content:
        return False

    old_start = 'function updateArticleText(article) {\n  stage.classList.remove("is-editorial");'
    new_start = (
        "function updateArticleText(article) {\n"
        f"  {JS_MARKER}\n"
        '  stage.classList.remove("is-editorial", "is-explainer", "is-solution");\n'
        '  const contentType = String(article.contentType || "news").trim();\n'
        '  stage.classList.toggle("is-explainer", contentType === "explainer");\n'
        '  stage.classList.toggle("is-solution", contentType === "solution");'
    )
    if old_start not in content:
        raise RuntimeError(
            "Die Funktion updateArticleText wurde nicht in der erwarteten "
            "Z-PANEL-5.0-Struktur gefunden."
        )
    content = content.replace(old_start, new_start, 1)

    old_boundary = (
        "  const boundary =\n"
        "    boundaryNames[article.planetaryBoundary] ||\n"
        "    article.planetaryBoundary ||\n"
        '    "ZUSTAND";'
    )
    new_boundary = (
        "  const boundary = contentType === \"explainer\"\n"
        '    ? (article.displayLabel || "NATUR VERSTEHEN")\n'
        "    : (\n"
        "        boundaryNames[article.planetaryBoundary] ||\n"
        "        article.planetaryBoundary ||\n"
        '        "ZUSTAND"\n'
        "      );"
    )
    if old_boundary not in content:
        raise RuntimeError(
            "Die bisherige Grenzbezeichnung in app.js wurde nicht gefunden."
        )
    content = content.replace(old_boundary, new_boundary, 1)
    path.write_text(content, encoding="utf-8")
    return True


def patch_styles(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    block = f"{CSS_START}\n{CSS_PATCH.strip()}\n{CSS_END}"
    pattern = re.compile(
        re.escape(CSS_START) + r".*?" + re.escape(CSS_END),
        re.S,
    )
    if pattern.search(content):
        new_content = pattern.sub(block, content, count=1)
    else:
        new_content = content.rstrip() + "\n\n" + block + "\n"
    changed = new_content != content
    if changed:
        path.write_text(new_content, encoding="utf-8")
    return changed


def normalized_text(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def infer_explainer(article: dict[str, Any]) -> bool:
    keywords = article.get("keywords", "")
    if isinstance(keywords, list):
        keywords = " ".join(str(item) for item in keywords)
    category = normalized_text(article.get("category"))
    keywords = normalized_text(keywords)
    return (
        category in {"natur verstehen", "grundlagen", "grundlage"}
        or "natur verstehen" in keywords
        or "grundlagen" in keywords
    )


def normalize_news(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("news.json enthält kein JSON-Objekt.")

    total = 0
    explainers = 0
    counts = {"news": 0, "explainer": 0, "solution": 0, "editorial": 0}

    articles = payload.get("articles", [])
    if isinstance(articles, list):
        for article in articles:
            if not isinstance(article, dict):
                continue
            content_type = normalized_text(article.get("contentType"))
            if content_type not in counts:
                content_type = "explainer" if infer_explainer(article) else "news"
            visual_mode = normalized_text(article.get("visualMode"))
            if visual_mode not in {
                "editorial-photo",
                "process-schematic",
                "symbolic",
                "scientific",
            }:
                visual_mode = (
                    "process-schematic"
                    if content_type == "explainer"
                    else "editorial-photo"
                )

            article["contentType"] = content_type
            article["visualMode"] = visual_mode
            if content_type == "explainer":
                article["category"] = "Natur verstehen"
                article["displayLabel"] = "NATUR VERSTEHEN"
                explainers += 1
            counts[content_type] += 1
            total += 1

    try:
        schema = int(payload.get("contentSchema", 0) or 0)
    except (TypeError, ValueError):
        schema = 0
    payload["contentSchema"] = max(schema, 3)
    payload["contentTypeCounts"] = counts

    temp = path.with_suffix(".json.tmp")
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)
    return total, explainers


def main() -> None:
    root = find_project_root(Path(__file__).resolve().parent)
    app_path = root / "app.js"
    styles_path = root / "styles.css"
    news_path = root / "news.json"

    backup = backup_files(root, [app_path, styles_path, news_path])
    js_changed = patch_app_js(app_path)
    css_changed = patch_styles(styles_path)
    total, explainers = normalize_news(news_path)

    print("Z-PANEL 5.1 – Grundlagenrubrik wurde vorbereitet.")
    print(f"Projektordner: {root}")
    print(f"Sicherung: {backup}")
    print("")
    print("Geändert:")
    print(
        "- app.js: Grundlagen werden als „NATUR VERSTEHEN“ erkannt"
        if js_changed else
        "- app.js: war bereits angepasst"
    )
    print(
        "- styles.css: dezente eigene Grundlagen-Gestaltung ergänzt"
        if css_changed else
        "- styles.css: Grundlagen-Gestaltung war bereits aktuell"
    )
    if news_path.exists():
        print(f"- news.json: {total} Beiträge normalisiert, davon {explainers} Grundlagen")
    else:
        print("- news.json fehlt noch; News Studio 5.8 ergänzt die Felder beim Veröffentlichen")
    print("")
    print("Danach:")
    print("1. news_studio_5_8.py starten.")
    print("2. Grundlagenbeiträge im Beitragseditor kennzeichnen.")
    print("3. Bildprompt neu erzeugen und Bild übernehmen.")
    print("4. news.json veröffentlichen.")
    print("5. Lokal prüfen, dann mit GitHub Desktop committen und pushen.")


if __name__ == "__main__":
    main()
