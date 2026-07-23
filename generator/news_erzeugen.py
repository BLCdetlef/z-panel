#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
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


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"Datei fehlt: {path.relative_to(PROJECT_ROOT)}")
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Ungültiges JSON in {path.relative_to(PROJECT_ROOT)} "
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


def validate_article(article: dict, path: Path, source_ids: set[str]) -> list[str]:
    errors = []
    label = path.relative_to(PROJECT_ROOT)

    for field in REQUIRED_ARTICLE_FIELDS:
        value = article.get(field)
        if value in ("", None, []):
            errors.append(f"{label}: Pflichtfeld '{field}' fehlt.")

    if not isinstance(article.get("article"), list) or not article.get("article"):
        errors.append(
            f"{label}: 'article' muss mindestens einen Textabschnitt enthalten."
        )

    if article.get("status") not in ALLOWED_STATUS:
        errors.append(
            f"{label}: Status muss 'freigegeben' oder 'veroeffentlicht' sein."
        )

    source_id = article.get("sourceId", "")
    if source_id and source_id not in source_ids:
        errors.append(f"{label}: Quelle '{source_id}' wurde nicht gefunden.")

    if not valid_url(article.get("sourceUrl", "")):
        errors.append(f"{label}: 'sourceUrl' enthält keine gültige Webadresse.")

    image_id = article.get("imageId", "")
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


def publication_sort_key(article: dict) -> tuple[str, str]:
    return (
        article.get("publicationDate", ""),
        article.get("id", ""),
    )


def main() -> int:
    errors = []

    # Quellen automatisch einlesen
    source_ids = set()

    for source_path in json_files(QUELLEN):
        source = load_json(source_path)
        source_id = source.get("id", "").strip()

        if not source_id:
            errors.append(
                f"{source_path.relative_to(PROJECT_ROOT)}: Feld 'id' fehlt."
            )
        elif source_id in source_ids:
            errors.append(
                f"{source_path.relative_to(PROJECT_ROOT)}: "
                f"Doppelte Quellen-ID '{source_id}'."
            )
        else:
            source_ids.add(source_id)

    # Artikel automatisch einlesen
    compiled = []
    seen_ids = set()

    for article_path in json_files(ARTIKEL):
        article = load_json(article_path)
        article_id = article.get("id", "").strip()

        if article_id and article_id in seen_ids:
            errors.append(
                f"{article_path.relative_to(PROJECT_ROOT)}: "
                f"Doppelte Artikel-ID '{article_id}'."
            )
        elif article_id:
            seen_ids.add(article_id)

        errors.extend(validate_article(article, article_path, source_ids))

        image_files, metadata_files = find_image_files(article.get("imageId", ""))

        output_article = dict(article)
        output_article["imageFile"] = (
            image_files[0].relative_to(PROJECT_ROOT).as_posix()
            if len(image_files) == 1
            else ""
        )
        output_article["imageMetadata"] = (
            load_json(metadata_files[0]) if len(metadata_files) == 1 else None
        )

        compiled.append(output_article)

    if errors:
        print("\nFEHLER – news.json wurde nicht erzeugt:\n")
        for error in errors:
            print(f"- {error}")
        return 1

    # Neueste Beiträge zuerst
    compiled.sort(key=publication_sort_key, reverse=True)

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

    print(
        f"Erfolgreich: {OUTPUT.name} mit "
        f"{len(compiled)} Artikel(n) erzeugt."
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"\nFEHLER: {exc}")
        raise SystemExit(1)
