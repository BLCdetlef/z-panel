#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tkinter as tk
import urllib.error
import urllib.request
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

def detect_project_root() -> Path:
    """Findet den vorhandenen ZUSTAND-Projektordner möglichst zuverlässig."""
    script_path = Path(__file__).resolve()
    script_dir = script_path.parent

    # Optionaler manueller Vorrang, falls später benötigt.
    env_root = os.environ.get("ZUSTAND_PROJECT_ROOT", "").strip()
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if (candidate / "newsredaktion").exists():
            return candidate

    candidates = []
    for candidate in (
        script_dir,
        script_dir.parent,
        script_dir.parent.parent,
    ):
        if candidate not in candidates:
            candidates.append(candidate)

    def score(candidate: Path) -> int:
        value = 0
        redaktion = candidate / "newsredaktion"
        if redaktion.is_dir():
            value += 100
        for folder_name in ("artikel", "entwuerfe", "quellen"):
            folder = redaktion / folder_name
            if folder.is_dir():
                value += 20
                value += min(25, len(list(folder.glob("*.json"))))
        if (candidate / "assets" / "images").is_dir():
            value += 15
        if (candidate / "news.json").exists():
            value += 10
        return value

    ranked = sorted(
        ((score(candidate), index, candidate)
         for index, candidate in enumerate(candidates)),
        key=lambda item: (-item[0], item[1]),
    )

    best_score, _, best_candidate = ranked[0]
    if best_score > 0:
        return best_candidate

    # Nur wenn noch keinerlei Projektstruktur existiert, wird der Skriptordner genutzt.
    return script_dir


PROJECT_ROOT = detect_project_root()
REDAKTION = PROJECT_ROOT / "newsredaktion"
ARTIKEL = REDAKTION / "artikel"
ENTWUERFE = REDAKTION / "entwuerfe"
QUELLEN = REDAKTION / "quellen"
VORLAGEN = REDAKTION / "vorlagen"
BILDER = PROJECT_ROOT / "assets" / "images"
OUTPUT = PROJECT_ROOT / "news.json"
DEFAULT_REMOTE_NEWS_URL = "https://blcdetlef.github.io/z-panel/news.json"

for folder in (ARTIKEL, ENTWUERFE, QUELLEN, VORLAGEN, BILDER):
    folder.mkdir(parents=True, exist_ok=True)

BOUNDARIES = ["KL", "BD", "LN", "FW", "NP", "OA", "OZ", "AE", "NS", "QS"]
ARTICLE_STATUSES = ["entwurf", "freigegeben", "veroeffentlicht", "archiviert"]

ZUSTAND_IMAGE_STYLE = (
    "Fotorealistische, glaubwürdige redaktionelle Fotografie für ein "
    "hochwertiges deutschsprachiges Wissenschaftsmagazin. Ruhige, glaubwürdige "
    "Bildsprache, realistische Lichtstimmung, klare Komposition, realistische Materialien "
    "und Hauttöne, dezente Tiefenschärfe. Ein einziges starkes Hauptmotiv mit "
    "verständlicher symbolischer Beziehung zum Artikel. Keine Katastrophenästhetik, "
    "keine übertriebene Dramatik, keine Collage, keine geteilte Ansicht, keine "
    "Diagramme, keine Infografik, keine Schrift, keine Buchstaben, keine Zahlen, "
    "keine Logos und keine Wasserzeichen. Für die linke Bildhälfte eines vertikal "
    "geteilten 16:9-Infoscreens; Ausgabe im Hochformat 8:9. Wichtige Motive mit "
    "mindestens zehn Prozent Sicherheitsabstand zum Bildrand platzieren."
)


IMAGE_STYLES = ("Automatisch", "Natur", "Wissenschaft", "Symbolisch")

STYLE_HINTS = {
    "Natur": (
        "Nutze eine natürliche, glaubwürdige Szenerie mit Landschaft, Tier, Pflanze, "
        "Wasser, Boden oder Himmel. Ruhig, realistisch und nicht romantisierend."
    ),
    "Wissenschaft": (
        "Nutze eine glaubwürdige wissenschaftliche Bildsprache, etwa Atmosphäre, "
        "Messinstrumente, Proben, Modelle oder sichtbare Prozesse. Keine "
        "Science-Fiction-Ästhetik und keine Infografik."
    ),
    "Symbolisch": (
        "Nutze eine klare, zurückhaltende visuelle Metapher. Sie soll sofort "
        "verständlich, fotorealistisch und weder plakativ noch werblich wirken."
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


def normalize_for_style(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(normalized.lower().split())


def automatic_image_style(
    title: str,
    summary: str,
    boundary: str,
    keywords: str,
) -> str:
    haystack = normalize_for_style(
        f"{title} {summary} {boundary} {keywords}"
    )
    for style in ("Wissenschaft", "Symbolisch", "Natur"):
        if any(term in haystack for term in AUTO_STYLE_TERMS[style]):
            return style
    return "Natur"


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


def article_image_hint(title: str, summary: str, keywords: str, boundary: str) -> str:
    """Wählt mit wenigen robusten Regeln eine passende Bildassoziation."""
    text = normalize_for_style(f"{title} {summary} {keywords}")

    if any(term in text for term in (
        "demokratie", "parlament", "lobby", "parteienfinanz",
        "ethikaufsicht", "wahl", "politische bildung", "medienkompetenz",
    )):
        return (
            "ein heller Sitzungssaal, ein runder Beratungstisch, eine öffentliche "
            "Bibliothek oder eine Wahlurne; keine Bäume, Wälder oder andere "
            "Naturmetaphern als Hauptmotiv"
        )

    if any(term in text for term in (
        "bildung", "schule", "unterricht", "studierende", "hochschule",
        "lernen", "lehr", "kompetenz",
    )):
        return (
            "ein glaubwürdiger Hörsaal, ein Klassenzimmer, eine Werkstatt oder "
            "eine Bibliothek; keine Naturmetapher als Hauptmotiv"
        )

    if any(term in text for term in (
        "gesundheit", "krankheit", "medizin", "prävention", "praxis",
        "patient", "psychisch", "pflege",
    )):
        return (
            "eine glaubwürdige Alltagsszene aus Praxis, Prävention, Bewegung oder "
            "Gesundheitsversorgung, alternativ ein zurückhaltendes wissenschaftliches Motiv"
        )

    if any(term in text for term in (
        "frieden", "zusammenarbeit", "gemeinwohl", "gesellschaft",
        "gerechtigkeit", "dialog",
    )):
        return (
            "Menschen im sachlichen Austausch, gemeinsames Arbeiten oder ein ruhiger "
            "öffentlicher Begegnungsort; keine gestellte Werbeszene"
        )

    if any(term in text for term in (
        "kreislaufwirtschaft", "reparatur", "recycling", "wiederverwendung",
        "ressourceneffizienz",
    )):
        return (
            "eine Reparaturwerkstatt, wiederverwendete Bauteile oder klar sortierte "
            "Materialien; kein Müllberg als Hauptmotiv"
        )

    return BOUNDARY_IMAGE_HINTS.get(
        boundary,
        "eine klare, leicht verständliche und glaubwürdige Assoziation zum Artikel",
    )


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
            "sourceId", "publicationDate", "language", "article"
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

        if not valid_url(str(article.get("sourceUrl", ""))):
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





def normalize_article_content(article: dict, path: Path, warnings: list[str]):
    """Überführt ältere Artikelstrukturen in das aktuelle Ausgabeformat."""
    content = article.get("article")

    if isinstance(content, list) and content:
        return content

    if isinstance(content, str) and content.strip():
        warnings.append(
            f"{rel(path)}: Das Feld 'article' war Text und wurde automatisch "
            "in die aktuelle Abschnittsstruktur umgewandelt."
        )
        return [{"heading": "", "text": content.strip()}]

    fallback_fields = ("text", "body", "content", "articleText", "longText")
    for field in fallback_fields:
        value = article.get(field)
        if isinstance(value, str) and value.strip():
            warnings.append(
                f"{rel(path)}: Das ältere Feld '{field}' wurde automatisch "
                "als Artikeltext übernommen."
            )
            return [{"heading": "", "text": value.strip()}]

    summary = str(article.get("summary", "")).strip()
    if summary:
        warnings.append(
            f"{rel(path)}: Kein ausführlicher Artikeltext gefunden; "
            "die Kurzfassung wird vorläufig als Artikeltext verwendet."
        )
        return [{"heading": "", "text": summary}]

    warnings.append(
        f"{rel(path)}: Kein Artikeltext vorhanden. Der Beitrag wird dennoch "
        "mit einem leeren Textabschnitt ausgegeben."
    )
    return [{"heading": "", "text": ""}]


def inspect_release(write_output: bool = False):
    """Prüft die Veröffentlichung und toleriert ältere, noch nutzbare Daten."""
    errors = []
    warnings = []
    source_ids = set()
    source_files = []

    for path in json_files(QUELLEN):
        source_files.append(path)
        try:
            source = read_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        sid = str(source.get("id", "")).strip()
        if not sid:
            warnings.append(f"{rel(path)}: Feld 'id' fehlt; Quelle wird nur über den Dateinamen geführt.")
        elif sid in source_ids:
            errors.append(f"{rel(path)}: Doppelte Quellen-ID '{sid}'.")
        else:
            source_ids.add(sid)

    compiled = []
    article_files = []
    image_files = []
    metadata_files = []
    seen_ids = set()

    for path in json_files(ARTIKEL):
        article_files.append(path)
        try:
            article = read_json(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        aid = str(article.get("id", "")).strip()
        title = str(article.get("title", "")).strip()

        if not aid:
            errors.append(f"{rel(path)}: Artikel-ID fehlt.")
        elif aid in seen_ids:
            errors.append(f"{rel(path)}: Doppelte Artikel-ID '{aid}'.")
        seen_ids.add(aid)

        if not title:
            errors.append(f"{rel(path)}: Titel fehlt.")

        # Nur wirklich unverzichtbare Felder führen zum Abbruch.
        for field in ("summary", "planetaryBoundary", "imageId", "publicationDate"):
            if article.get(field) in ("", None, []):
                warnings.append(f"{rel(path)}: Feld '{field}' fehlt oder ist leer.")

        status = str(article.get("status", "")).strip()
        if status not in {"freigegeben", "veroeffentlicht"}:
            errors.append(
                f"{rel(path)}: Status muss 'freigegeben' oder "
                f"'veroeffentlicht' sein."
            )

        # sourceId und sourceTitle sind seit Version 4.6 optional.
        # Ältere Artikel dürfen sie weiterhin enthalten; für neue Artikel genügt
        # die direkt eingetragene Quellen-URL.
        sid = str(article.get("sourceId", "")).strip()
        if sid and source_ids and sid not in source_ids:
            warnings.append(
                f"{rel(path)}: Die ältere Quellen-ID '{sid}' wurde nicht als "
                "eigene Quelldatei gefunden. Die Quellen-URL wird trotzdem verwendet."
            )

        source_url = str(article.get("sourceUrl", "")).strip()
        if source_url and not valid_url(source_url):
            warnings.append(f"{rel(path)}: sourceUrl ist ungültig und sollte geprüft werden.")

        image_id = str(article.get("imageId", "")).strip()
        images, metas = image_matches(image_id)

        if len(images) == 1:
            image_files.append(images[0])
        elif len(images) == 0:
            warnings.append(
                f"{rel(path)}: Zu imageId '{image_id}' wurde kein Bild gefunden. "
                "Der Infoscreen verwendet gegebenenfalls sein Ersatzbild."
            )
        else:
            warnings.append(
                f"{rel(path)}: Zu imageId '{image_id}' wurden {len(images)} Bilder "
                "gefunden; es wird kein Bild automatisch ausgewählt."
            )

        if len(metas) == 1:
            metadata_files.append(metas[0])
        elif len(metas) == 0:
            warnings.append(
                f"{rel(path)}: Zu imageId '{image_id}' wurden keine Bildmetadaten gefunden."
            )
        else:
            warnings.append(
                f"{rel(path)}: Zu imageId '{image_id}' wurden {len(metas)} "
                "Metadatendateien gefunden."
            )

        item = dict(article)
        item["language"] = str(article.get("language", "")).strip() or "de"
        item["article"] = normalize_article_content(article, path, warnings)
        if sid:
            item["sourceId"] = sid
        else:
            item.pop("sourceId", None)
        item.pop("sourceTitle", None)
        item.pop("subtitle", None)
        item.pop("editor", None)
        item["imageFile"] = (
            images[0].relative_to(PROJECT_ROOT).as_posix()
            if len(images) == 1 else ""
        )

        if len(metas) == 1:
            try:
                item["imageMetadata"] = read_json(metas[0])
            except ValueError as exc:
                warnings.append(str(exc))
                item["imageMetadata"] = None
        else:
            item["imageMetadata"] = None

        compiled.append(item)

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

    if not compiled:
        warnings.append("Es wurden keine freigegebenen Artikel gefunden.")

    if write_output and not errors:
        write_json(OUTPUT, payload)

    release_files = []
    for path in article_files + source_files + image_files + metadata_files:
        if path not in release_files:
            release_files.append(path)
    if write_output and not errors:
        release_files.insert(0, OUTPUT)

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "payload": payload,
        "article_count": len(compiled),
        "source_count": len(source_ids),
        "image_count": len(image_files),
        "metadata_count": len(metadata_files),
        "release_files": release_files,
    }


def git_status_lines():
    """Liest den lokalen Git-Status, ohne Dateien zu verändern."""
    try:
        result = subprocess.run(
            ["git", "-C", str(PROJECT_ROOT), "status", "--short"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except FileNotFoundError:
        return False, [
            "Git wurde auf diesem Rechner nicht gefunden.",
            "Die Veröffentlichung kann trotzdem mit GitHub Desktop erfolgen."
        ]
    except Exception as exc:
        return False, [f"Git-Status konnte nicht gelesen werden: {exc}"]

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        return False, [
            "Der Projektordner ist möglicherweise kein Git-Repository.",
            detail or "Git meldete einen unbekannten Fehler."
        ]

    lines = [line.rstrip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        lines = ["Keine lokalen Git-Änderungen gefunden."]
    return True, lines


def fetch_remote_news(url: str):
    """Lädt die veröffentlichte news.json mit Cache-Busting."""
    separator = "&" if "?" in url else "?"
    request_url = f"{url}{separator}v={int(datetime.now().timestamp())}"
    request = urllib.request.Request(
        request_url,
        headers={
            "User-Agent": "ZUSTAND-News-Studio/4.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8-sig")
        data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise ValueError(f"GitHub Pages antwortet mit HTTP {exc.code}.")
    except urllib.error.URLError as exc:
        raise ValueError(f"GitHub Pages ist nicht erreichbar: {exc.reason}")
    except json.JSONDecodeError:
        raise ValueError("Die veröffentlichte Datei ist kein gültiges JSON.")

    articles = data.get("articles", [])
    count = data.get("articleCount")
    if not isinstance(count, int):
        count = len(articles) if isinstance(articles, list) else 0

    ids = []
    if isinstance(articles, list):
        ids = [
            str(article.get("id", "")).strip()
            for article in articles
            if isinstance(article, dict) and article.get("id")
        ]

    return {
        "count": count,
        "ids": ids,
        "generatedAt": data.get("generatedAt", ""),
    }


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
        self.title("ZUSTAND News Studio 5.0")
        self.geometry("1220x780")
        self.minsize(880, 540)

        self.current_article_path = None
        self.current_source_path = None
        self.image_style_var = tk.StringVar(value="Automatisch")

        self._build()
        self.refresh_all()
        self.after(250, self._check_project_location)

    def _check_project_location(self):
        counts = collect_counts()
        total_content = counts["drafts"] + counts["articles"] + counts["sources"]

        self.status_var.set(
            f"Projektordner: {PROJECT_ROOT} │ "
            f"{counts['drafts']} Entwurf/Entwürfe │ "
            f"{counts['articles']} freigegebene Artikel"
        )

        if total_content == 0:
            messagebox.showwarning(
                "Keine vorhandenen Redaktionsdaten gefunden",
                (
                    "Im automatisch erkannten Projektordner wurden keine Artikel, "
                    "Entwürfe oder Quellen gefunden.\n\n"
                    f"Verwendeter Projektordner:\n{PROJECT_ROOT}\n\n"
                    "Bitte prüfe, ob News Studio 5.0 im richtigen Projektordner liegt. "
                    "Die vorhandenen Daten wurden nicht gelöscht."
                ),
            )

    def _build(self):
        header = ttk.Frame(self, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(
            header, text="ZUSTAND News Studio 5.0",
            font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")
        ttk.Label(
            header,
            text="Beiträge erstellen, Bildprompts vorbereiten, Titelbilder übernehmen und news.json veröffentlichen"
        ).pack(anchor="w")

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.overview_tab = ttk.Frame(self.tabs)
        self.article_tab = ttk.Frame(self.tabs)
        self.generator_tab = ttk.Frame(self.tabs)

        self.tabs.add(self.overview_tab, text="Start")
        self.tabs.add(self.article_tab, text="Beiträge")
        self.tabs.add(self.generator_tab, text="Veröffentlichen")

        self._build_overview()
        self._build_articles()
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
                           ("drafts", "articles", "images")}
        labels = [
            ("Entwürfe", "drafts"),
            ("Freigegebene Beiträge", "articles"),
            ("Titelbilder", "images"),
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
            actions, text="1. Recherche-Prompt",
            command=self.open_research_prompt
        ).pack(side="left")
        ttk.Button(
            actions, text="2. Recherche-Datei importieren",
            command=self.import_research_file
        ).pack(side="left", padx=8)
        ttk.Button(
            actions, text="3. Neuen Beitrag anlegen",
            command=self.new_article
        ).pack(side="left")
        ttk.Button(
            actions, text="4. Veröffentlichen",
            command=self.run_generator
        ).pack(side="left", padx=8)
        ttk.Button(
            actions, text="Projektordner öffnen",
            command=lambda: os.startfile(PROJECT_ROOT)
        ).pack(side="right")

        project_info = ttk.LabelFrame(
            outer, text="Verwendeter Projektordner", padding=12
        )
        project_info.pack(fill="x", pady=(0, 12))
        self.project_root_var = tk.StringVar(value=str(PROJECT_ROOT))
        ttk.Label(
            project_info,
            textvariable=self.project_root_var,
            font=("Consolas", 10),
            wraplength=1050,
            justify="left",
        ).pack(side="left", fill="x", expand=True)
        ttk.Button(
            project_info,
            text="Ordner öffnen",
            command=lambda: os.startfile(PROJECT_ROOT),
        ).pack(side="right", padx=(10, 0))

        info = ttk.LabelFrame(outer, text="Arbeitsweise", padding=16)
        info.pack(fill="both", expand=True)
        text = (
            "1. Recherche-Prompt erzeugen und hier in ChatGPT einfügen.\n"
            "2. Die von ChatGPT erzeugte Recherche-Datei importieren.\n"
            "3. Beitrag prüfen, Bildprompt erzeugen und Titelbild übernehmen.\n"
            "4. Beitrag freigeben.\n"
            "5. Unter „Veröffentlichen“ news.json erzeugen und anschließend mit GitHub Desktop pushen.\n\n"
            "Eine separate Quellenverwaltung ist nicht mehr nötig: Die Quellen-URL steht direkt im Beitrag."
        )
        ttk.Label(info, text=text, justify="left").pack(anchor="w")

    def _build_articles(self):
        paned = ttk.Panedwindow(self.article_tab, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(paned, padding=6)
        right = ttk.Frame(paned, padding=8)
        paned.add(left, weight=1)
        paned.add(right, weight=3)

        ttk.Label(left, text="Beiträge",
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
        ttk.Button(btns, text="Recherche-Prompt",
                   command=self.open_research_prompt).pack(side="left", padx=5)
        ttk.Button(btns, text="Recherche importieren",
                   command=self.import_research_file).pack(side="left", padx=(0, 5))
        ttk.Button(btns, text="Aktualisieren",
                   command=self.refresh_article_list).pack(side="left")

        self.article_vars = {
            "id": tk.StringVar(),
            "status": tk.StringVar(value="entwurf"),
            "title": tk.StringVar(),
            "summary": tk.StringVar(),
            "planetaryBoundary": tk.StringVar(),
            "keywords": tk.StringVar(),
            "imageId": tk.StringVar(),
            "sourceUrl": tk.StringVar(),
            "publicationDate": tk.StringVar(value=date.today().isoformat()),
            "author": tk.StringVar(),
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

        ttk.Label(form, text="Beitrag bearbeiten",
                  font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 3))
        ttk.Label(
            form,
            text=(
                "Vereinfachte Eingabe: Untertitel, Quellen-ID, Quellentitel "
                "und Redaktion sind nicht mehr erforderlich."
            ),
            wraplength=760,
            justify="left",
        ).pack(anchor="w", pady=(0, 8))

        FieldRow(form, "ID", self.article_vars["id"])
        status_row = ttk.Frame(form)
        ttk.Label(status_row, text="Status", width=20).pack(side="left")
        ttk.Combobox(
            status_row, textvariable=self.article_vars["status"],
            values=ARTICLE_STATUSES, state="readonly"
        ).pack(side="left", fill="x", expand=True)
        status_row.pack(fill="x", pady=3)

        FieldRow(form, "Titel", self.article_vars["title"])
        FieldRow(form, "Kurzfassung", self.article_vars["summary"])

        pb_row = ttk.Frame(form)
        ttk.Label(pb_row, text="Planetare Grenze", width=20).pack(side="left")
        ttk.Combobox(
            pb_row, textvariable=self.article_vars["planetaryBoundary"],
            values=BOUNDARIES
        ).pack(side="left", fill="x", expand=True)
        pb_row.pack(fill="x", pady=3)

        FieldRow(form, "Schlagwörter", self.article_vars["keywords"])
        FieldRow(form, "Bild-ID", self.article_vars["imageId"])

        image_style_row = ttk.Frame(form)
        ttk.Label(image_style_row, text="Bildstil", width=20).pack(side="left")
        ttk.Combobox(
            image_style_row,
            textvariable=self.image_style_var,
            values=IMAGE_STYLES,
            state="readonly",
            width=20,
        ).pack(side="left")
        ttk.Label(
            image_style_row,
            text="Automatisch wählt Natur, Wissenschaft oder Symbolisch.",
        ).pack(side="left", padx=(10, 0))
        image_style_row.pack(fill="x", pady=(3, 4))

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
        source_help = ttk.Frame(form)
        ttk.Label(source_help, text="", width=20).pack(side="left")
        ttk.Label(
            source_help,
            text=(
                "Eine vollständige Quellen-URL genügt. Quellen-ID und "
                "Quellentitel werden nicht mehr manuell gepflegt."
            ),
            wraplength=680,
            justify="left",
        ).pack(side="left", fill="x", expand=True)
        source_help.pack(fill="x", pady=(0, 4))
        FieldRow(form, "Veröffentlichungsdatum",
                 self.article_vars["publicationDate"])
        FieldRow(form, "Autor/in", self.article_vars["author"])

        ttk.Label(form, text="Artikeltext").pack(anchor="w", pady=(10, 3))
        self.article_text = tk.Text(form, height=13, wrap="word")
        self.article_text.pack(fill="x")

        ttk.Label(form, text="Notizen").pack(anchor="w", pady=(10, 3))
        self.article_notes = tk.Text(form, height=5, wrap="word")
        self.article_notes.pack(fill="x")

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




    def build_research_prompt(self, period: str) -> str:
        period_text = {
            "Seit gestern": "seit gestern",
            "Seit einer Woche": "seit einer Woche",
            "Seit einem Monat": "seit einem Monat",
        }.get(period, period.strip() or "seit gestern")

        return (
            f"Recherchiere die wichtigsten neuen Meldungen {period_text} aus seriösen "
            "Primärquellen für den ZUSTAND-Infoscreen. Berücksichtige drei Gruppen: "
            "(1) Zustandsmeldungen zu planetaren Grenzen, (2) belastbare Lösungs- und "
            "Fortschrittsmeldungen und (3) Querschnittsthemen wie Gesundheit, "
            "Glücksforschung, Demokratie, Frieden, Bildung, Gemeinwohl, Suffizienz, "
            "Postwachstum, Kreislaufwirtschaft, Baukultur, Kunst und Zusammenarbeit.\n\n"
            "Bevorzuge neue Studien, Messdaten, Berichte und offizielle Mitteilungen. "
            "Vermeide PR, Greenwashing, bloße Meinungsbeiträge und Wiederholungen. "
            "Schlage höchstens 10 Meldungen vor und achte auf eine ausgewogene Mischung, "
            "darunter möglichst mindestens zwei positive oder konstruktive Meldungen.\n\n"
            "Prüfe besonders seriöse Primärquellen wie PIK Potsdam, Copernicus Climate, "
            "Copernicus Marine, WMO, UNEP, Stockholm Resilience Centre, AWI, GEOMAR, "
            "Umweltbundesamt, Bundesamt für Naturschutz, Thünen-Institut, European "
            "Environment Agency, Our World in Data und Deutsche Umwelthilfe, soweit "
            "dort tatsächlich neue belastbare Inhalte vorliegen.\n\n"
            "Gib für jede Meldung Titel, kurze Kernaussage, Originalquelle, Veröffentlichungsdatum, "
            "Quellen-URL, passende Schlagwörter, Kategorie und Priorität an. Erzeuge anschließend "
            "eine JSON-Datei zum Import in ZUSTAND News Studio 5.0. Verwende exakt dieses Grundformat:\n\n"
            "{\n"
            "  \"format\": \"zustand-recherche-import-v1\",\n"
            "  \"articles\": [\n"
            "    {\n"
            "      \"title\": \"...\",\n"
            "      \"summary\": \"...\",\n"
            "      \"planetaryBoundary\": \"KL|BD|LN|FW|NP|OA|OZ|AE|NS|QS\",\n"
            "      \"keywords\": [\"...\"],\n"
            "      \"sourceTitle\": \"...\",\n"
            "      \"sourceUrl\": \"https://...\",\n"
            "      \"publicationDate\": \"YYYY-MM-DD\",\n"
            "      \"category\": \"Zustand|Lösung|Querschnitt\",\n"
            "      \"priority\": 1\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Vergib keine Artikel-IDs und keine Bild-IDs; diese werden beim Import automatisch und "
            "kollisionsfrei nach der bestehenden Logik erzeugt. Stelle die JSON-Datei zum Herunterladen bereit."
        )

    def open_research_prompt(self):
        window = tk.Toplevel(self)
        window.title("Recherche-Prompt")
        window.transient(self)
        window.geometry("900x650")
        window.minsize(680, 480)

        outer = ttk.Frame(window, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Neue Meldungen recherchieren",
                  font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(outer, text=(
            "Zeitraum wählen, Prompt kopieren und hier in ChatGPT einfügen. "
            "Die Recherche selbst läuft weiterhin im Chat."
        ), wraplength=820, justify="left").pack(anchor="w", pady=(2, 10))

        row = ttk.Frame(outer)
        row.pack(fill="x", pady=(0, 8))
        ttk.Label(row, text="Zeitraum:").pack(side="left")
        period = tk.StringVar(value="Seit gestern")
        combo = ttk.Combobox(row, textvariable=period, state="readonly", width=22,
                             values=("Seit gestern", "Seit einer Woche", "Seit einem Monat"))
        combo.pack(side="left", padx=(8, 0))

        text = tk.Text(outer, wrap="word", padx=8, pady=8)
        text.pack(fill="both", expand=True)

        status = tk.StringVar(value="Bereit")

        def rebuild(*_args):
            text.delete("1.0", "end")
            text.insert("1.0", self.build_research_prompt(period.get()))
            status.set(f"Prompt für: {period.get()}")

        def copy_prompt():
            prompt = text.get("1.0", "end").strip()
            self.clipboard_clear()
            self.clipboard_append(prompt)
            self.update()
            status.set("Prompt wurde in die Zwischenablage kopiert.")

        combo.bind("<<ComboboxSelected>>", rebuild)
        rebuild()

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(10, 0))
        ttk.Label(footer, textvariable=status).pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Prompt kopieren", command=copy_prompt).pack(side="right")
        ttk.Button(footer, text="Schließen", command=window.destroy).pack(side="right", padx=(0, 6))

        window.bind("<Escape>", lambda _e: window.destroy())
        window.bind("<Control-c>", lambda _e: copy_prompt())

    @staticmethod
    def _research_prefix(item: dict) -> str:
        boundary = str(item.get("planetaryBoundary", "")).strip().upper()
        if boundary in BOUNDARIES:
            return boundary

        category = normalize_for_style(item.get("category", ""))
        if any(term in category for term in ("querschnitt", "gesundheit", "demokratie", "bildung", "frieden", "gemeinwohl")):
            return "QS"
        return "QS"

    @staticmethod
    def _used_article_ids() -> set[str]:
        used = set()
        for folder in (ENTWUERFE, ARTIKEL):
            for path in json_files(folder):
                try:
                    value = str(read_json(path).get("id", "")).strip()
                except Exception:
                    value = ""
                if value:
                    used.add(value)
        return used

    @staticmethod
    def _next_article_id(prefix: str, used_ids: set[str]) -> str:
        highest = 0
        needle = prefix + "_"
        for value in used_ids:
            if not value.startswith(needle):
                continue
            suffix = value[len(needle):]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
        candidate = f"{prefix}_{highest + 1:04d}"
        while candidate in used_ids:
            highest += 1
            candidate = f"{prefix}_{highest + 1:04d}"
        used_ids.add(candidate)
        return candidate

    def import_research_file(self):
        selected = filedialog.askopenfilename(
            parent=self,
            title="ZUSTAND-Recherche-Datei auswählen",
            filetypes=[("JSON-Datei", "*.json"), ("Alle Dateien", "*.*")],
        )
        if not selected:
            return

        try:
            payload = read_json(Path(selected))
        except ValueError as exc:
            messagebox.showerror("Import nicht möglich", str(exc), parent=self)
            return

        if isinstance(payload, list):
            items = payload
        elif isinstance(payload, dict):
            items = payload.get("articles") or payload.get("drafts") or payload.get("meldungen") or []
        else:
            items = []

        if not isinstance(items, list) or not items:
            messagebox.showwarning(
                "Keine Meldungen gefunden",
                "Die Datei enthält keine Liste unter 'articles'.",
                parent=self,
            )
            return

        existing_urls = set()
        existing_titles = set()
        for folder in (ENTWUERFE, ARTIKEL):
            for path in json_files(folder):
                try:
                    data = read_json(path)
                except Exception:
                    continue
                url = str(data.get("sourceUrl", "")).strip().lower()
                title = normalize_for_style(data.get("title", ""))
                if url:
                    existing_urls.add(url)
                if title:
                    existing_titles.add(title)

        used_ids = self._used_article_ids()
        imported = []
        skipped = []
        errors = []
        today = date.today().isoformat()

        for index, raw in enumerate(items, start=1):
            if not isinstance(raw, dict):
                errors.append(f"Eintrag {index}: kein gültiges Objekt")
                continue

            title = str(raw.get("title", "")).strip()
            summary = str(raw.get("summary", raw.get("coreStatement", ""))).strip()
            source_url = str(raw.get("sourceUrl", raw.get("url", ""))).strip()
            publication_date = str(raw.get("publicationDate", raw.get("date", today))).strip() or today
            if not title:
                errors.append(f"Eintrag {index}: Titel fehlt")
                continue

            normalized_title = normalize_for_style(title)
            if (source_url and source_url.lower() in existing_urls) or normalized_title in existing_titles:
                skipped.append(title)
                continue

            prefix = self._research_prefix(raw)
            article_id = self._next_article_id(prefix, used_ids)
            keywords = raw.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [part.strip() for part in keywords.split(",") if part.strip()]
            elif not isinstance(keywords, list):
                keywords = []
            keywords = [str(value).strip() for value in keywords if str(value).strip()]

            category = str(raw.get("category", "")).strip()
            priority = raw.get("priority", "")
            if category and category not in keywords:
                keywords.append(category)
            priority_text = str(priority).strip()
            if priority_text and f"Priorität {priority_text}" not in keywords:
                keywords.append(f"Priorität {priority_text}")

            source_title = str(raw.get("sourceTitle", raw.get("source", ""))).strip()
            notes_parts = ["Importiert über Recherche-Assistent 5.0"]
            if category:
                notes_parts.append(f"Meldungsart: {category}")
            if priority_text:
                notes_parts.append(f"Priorität: {priority_text}")
            if source_title:
                notes_parts.append(f"Originalquelle: {source_title}")

            data = {
                "id": article_id,
                "status": "entwurf",
                "title": title,
                "summary": summary,
                "planetaryBoundary": prefix,
                "keywords": keywords,
                "imageId": f"{article_id}_01",
                "sourceUrl": source_url,
                "publicationDate": publication_date,
                "author": "",
                "created": today,
                "lastModified": today,
                "language": "de",
                "article": [],
                "facts": [],
                "links": [],
                "license": "",
                "notes": "; ".join(notes_parts),
            }
            target = ENTWUERFE / f"{article_id}_{slug(title)}.json"
            try:
                write_json(target, data)
            except Exception as exc:
                errors.append(f"{title}: {exc}")
                used_ids.discard(article_id)
                continue

            imported.append((article_id, title))
            if source_url:
                existing_urls.add(source_url.lower())
            existing_titles.add(normalized_title)

        self.refresh_all()
        self.tabs.select(self.article_tab)

        lines = [f"Importiert: {len(imported)}"]
        if skipped:
            lines.append(f"Übersprungen (bereits vorhanden): {len(skipped)}")
        if errors:
            lines.append(f"Fehler: {len(errors)}")
        if imported:
            lines.append("")
            lines.extend(f"{article_id} – {title}" for article_id, title in imported[:10])
        if skipped:
            lines.append("")
            lines.append("Bereits vorhanden:")
            lines.extend(skipped[:5])
        if errors:
            lines.append("")
            lines.append("Fehler:")
            lines.extend(errors[:5])

        self.status_var.set(f"Rechercheimport abgeschlossen: {len(imported)} neue Entwürfe")
        messagebox.showinfo("Recherche importiert", "\n".join(lines), parent=self)

    def selected_image_style(self) -> str:
        requested = self.image_style_var.get().strip() or "Automatisch"
        if requested != "Automatisch":
            return requested

        return automatic_image_style(
            self.article_vars["title"].get().strip(),
            self.article_vars["summary"].get().strip(),
            self.article_vars["planetaryBoundary"].get().strip(),
            self.article_vars["keywords"].get().strip(),
        )

    def build_image_prompt(self) -> str:
        title = self.article_vars["title"].get().strip()
        summary = self.article_vars["summary"].get().strip()
        boundary = self.article_vars["planetaryBoundary"].get().strip()
        keywords = self.article_vars["keywords"].get().strip()

        hint = article_image_hint(title, summary, keywords, boundary)
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
            "Ereignis. Entwickle stattdessen eine glaubwürdige und fotorealistische "
            "Assoziation, die den Inhalt auf den ersten Blick "
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
            f"Verbindliche ZUSTAND-Bildsprache: {ZUSTAND_IMAGE_STYLE}\n\n"
            "Das Hauptmotiv soll sich unmittelbar aus dem Artikelthema ergeben und "
            "nicht aus einer allgemeinen Naturmetapher.\n\n"
            "Ausgabe: genau ein fertiges Bild im Hochformat 8:9, ohne Text im Bild."
        )

    @staticmethod
    def _fit_and_center(window, parent=None) -> None:
        window.update_idletasks()

        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()

        max_w = max(680, screen_w - 80)
        max_h = max(480, screen_h - 140)

        width = min(940, max_w)
        height = min(690, max_h)

        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2 - 10)

        window.geometry(f"{width}x{height}+{x}+{y}")
        window.minsize(min(680, width), min(460, height))

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
        window.transient(self)
        self._fit_and_center(window, self)

        window.rowconfigure(0, weight=1)
        window.columnconfigure(0, weight=1)

        outer = ttk.Frame(window, padding=14)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(0, weight=1)

        ttk.Label(
            outer,
            text="ZUSTAND-Bildprompt 8:9",
            font=("Segoe UI", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            outer,
            text=(
                "Der Prompt wird aus dem Artikel und dem gewählten Bildstil gebildet. "
                "Kopiere ihn anschließend in ChatGPT, erzeuge dort ein Bild und "
                "übernimm die gespeicherte Bilddatei wieder in das News Studio."
            ),
            wraplength=820,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(2, 10))

        prompt_frame = ttk.Frame(outer)
        prompt_frame.grid(row=2, column=0, sticky="nsew")
        prompt_frame.rowconfigure(0, weight=1)
        prompt_frame.columnconfigure(0, weight=1)

        prompt_text = tk.Text(
            prompt_frame,
            wrap="word",
            undo=True,
            padx=8,
            pady=8,
        )
        prompt_text.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(
            prompt_frame,
            orient="vertical",
            command=prompt_text.yview,
        )
        y_scroll.grid(row=0, column=1, sticky="ns")
        prompt_text.configure(yscrollcommand=y_scroll.set)

        x_scroll = ttk.Scrollbar(
            prompt_frame,
            orient="horizontal",
            command=prompt_text.xview,
        )
        x_scroll.grid(row=1, column=0, sticky="ew")
        prompt_text.configure(xscrollcommand=x_scroll.set)

        prompt_text.insert("1.0", self.build_image_prompt())

        footer = ttk.Frame(outer)
        footer.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        footer.columnconfigure(0, weight=1)

        status = tk.StringVar(
            value=f"Bildstil: {self.selected_image_style()} │ Ausgabe: 8:9"
        )
        ttk.Label(
            footer,
            textvariable=status,
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=(0, 10))

        buttons = ttk.Frame(footer)
        buttons.grid(row=0, column=1, sticky="e")

        def rebuild_prompt():
            prompt_text.delete("1.0", "end")
            prompt_text.insert("1.0", self.build_image_prompt())
            prompt_text.see("1.0")
            status.set(
                f"Prompt neu gebildet │ Bildstil: {self.selected_image_style()} │ 8:9"
            )

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
            text="Neu bilden",
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
        ).pack(side="left", padx=(0, 6))
        ttk.Button(
            buttons,
            text="Schließen",
            command=window.destroy,
        ).pack(side="left")

        window.bind("<Escape>", lambda _event: window.destroy())
        window.bind("<Control-c>", lambda _event: copy_prompt())
        window.after_idle(lambda: self._fit_and_center(window, self))

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
        summary = self.article_vars["summary"].get().strip()
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

        # Grid statt reinem Pack-Layout: Kopf und Fuß bleiben immer sichtbar.
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)

        title_row = ttk.Frame(outer)
        title_row.grid(row=0, column=0, sticky="ew")
        ttk.Label(
            title_row,
            text="Veröffentlichungsassistent",
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")

        button_row = ttk.Frame(outer)
        button_row.grid(row=1, column=0, sticky="ew", pady=(12, 8))

        ttk.Button(
            button_row,
            text="1. Veröffentlichung simulieren",
            command=self.simulate_release,
        ).pack(side="left")

        ttk.Button(
            button_row,
            text="2. Prüfen und news.json erzeugen",
            command=self.run_generator,
        ).pack(side="left", padx=6)

        ttk.Button(
            button_row,
            text="3. Git-Status prüfen",
            command=self.show_git_status,
        ).pack(side="left")

        ttk.Button(
            button_row,
            text="GitHub Desktop öffnen",
            command=self.open_github_desktop,
        ).pack(side="left", padx=6)

        remote_box = ttk.LabelFrame(
            outer,
            text="Veröffentlichung auf GitHub Pages prüfen",
            padding=10,
        )
        remote_box.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        remote_box.columnconfigure(0, weight=1)

        self.remote_news_url = tk.StringVar(value=DEFAULT_REMOTE_NEWS_URL)
        ttk.Entry(
            remote_box,
            textvariable=self.remote_news_url,
        ).grid(row=0, column=0, sticky="ew")
        ttk.Button(
            remote_box,
            text="4. Lokale und veröffentlichte Version vergleichen",
            command=self.check_remote_release,
        ).grid(row=0, column=1, padx=(8, 0))

        log_frame = ttk.Frame(outer)
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(4, 8))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.generator_log = tk.Text(
            log_frame,
            wrap="word",
            font=("Consolas", 10),
            state="disabled",
            height=8,
        )
        self.generator_log.grid(row=0, column=0, sticky="nsew")

        log_scrollbar = ttk.Scrollbar(
            log_frame,
            orient="vertical",
            command=self.generator_log.yview,
        )
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.generator_log.configure(yscrollcommand=log_scrollbar.set)

        # Die Schaltflächenleiste liegt in einer eigenen festen Grid-Zeile.
        footer = ttk.Frame(outer)
        footer.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        ttk.Separator(footer, orient="horizontal").pack(fill="x", pady=(0, 8))

        footer_buttons = ttk.Frame(footer)
        footer_buttons.pack(fill="x")
        ttk.Button(
            footer_buttons,
            text="news.json öffnen",
            command=self.open_news_json,
        ).pack(side="left")
        ttk.Button(
            footer_buttons,
            text="Projektordner öffnen",
            command=lambda: os.startfile(PROJECT_ROOT),
        ).pack(side="left", padx=6)

    def _set_generator_log(self, heading: str, lines):
        self.generator_log.configure(state="normal")
        self.generator_log.delete("1.0", "end")
        content = heading.strip() + "\n\n" + "\n".join(str(line) for line in lines)
        self.generator_log.insert("1.0", content)
        self.generator_log.configure(state="disabled")
        self.generator_log.see("1.0")

    def simulate_release(self):
        self.tabs.select(self.generator_tab)
        report = inspect_release(write_output=False)

        lines = [
            f"Projektordner: {PROJECT_ROOT}",
            "",
            f"Freigegebene Artikel: {report['article_count']}",
            f"Verwendete Quellen: {report['source_count']}",
            f"Gefundene Bilder: {report['image_count']}",
            f"Gefundene Bildmetadaten: {report['metadata_count']}",
            "",
        ]

        if report["errors"]:
            lines.append("VERÖFFENTLICHUNG NICHT MÖGLICH")
            lines.extend(f"✗ {item}" for item in report["errors"])
        else:
            lines.append("VERÖFFENTLICHUNG MÖGLICH")
            lines.append("Es wurden keine Dateien verändert.")
            if report["warnings"]:
                lines.append("")
                lines.append("HINWEISE – Veröffentlichung bleibt möglich:")
                lines.extend(f"⚠ {item}" for item in report["warnings"])
            lines.append("")
            lines.append("Diese Artikel würden veröffentlicht:")
            for article in report["payload"]["articles"]:
                lines.append(
                    f"✓ {article.get('id', '')} – {article.get('title', '')}"
                )

        self._set_generator_log("SIMULATION", lines)
        self.status_var.set(
            f"Simulation abgeschlossen │ {report['article_count']} Artikel"
        )

    def show_git_status(self):
        self.tabs.select(self.generator_tab)
        success, lines = git_status_lines()
        heading = "GIT-STATUS" if success else "GIT-STATUS – HINWEIS"
        self._set_generator_log(heading, lines)
        self.status_var.set(
            "Git-Status wurde gelesen."
            if success else "Git-Status konnte nicht vollständig gelesen werden."
        )

    def open_github_desktop(self):
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "GitHubDesktop" / "GitHubDesktop.exe",
            Path(os.environ.get("LOCALAPPDATA", ""))
            / "GitHubDesktop" / "app-3.4.18" / "GitHubDesktop.exe",
            Path(os.environ.get("PROGRAMFILES", ""))
            / "GitHub Desktop" / "GitHubDesktop.exe",
        ]

        executable = next((path for path in candidates if path.is_file()), None)
        try:
            if executable:
                subprocess.Popen([str(executable), str(PROJECT_ROOT)])
                self.status_var.set("GitHub Desktop wurde geöffnet.")
                return

            # Windows-Protokoll; funktioniert bei regulärer GitHub-Desktop-Installation.
            os.startfile(f"x-github-client://openRepo/{PROJECT_ROOT.as_posix()}")
            self.status_var.set("GitHub Desktop wurde geöffnet.")
        except Exception:
            messagebox.showinfo(
                "GitHub Desktop",
                (
                    "GitHub Desktop konnte nicht automatisch geöffnet werden.\n\n"
                    f"Projektordner:\n{PROJECT_ROOT}\n\n"
                    "Öffne GitHub Desktop bitte manuell und wähle dieses Repository."
                ),
            )

    def check_remote_release(self):
        self.tabs.select(self.generator_tab)
        url = self.remote_news_url.get().strip()
        if not valid_url(url):
            messagebox.showwarning(
                "Ungültige Adresse",
                "Bitte eine vollständige https-Adresse zur veröffentlichten news.json eingeben.",
            )
            return

        try:
            local = read_json(OUTPUT)
        except ValueError as exc:
            self._set_generator_log(
                "VERÖFFENTLICHUNGSPRÜFUNG",
                [
                    "Lokale news.json konnte nicht gelesen werden.",
                    str(exc),
                    "",
                    "Erzeuge die Datei zunächst mit Schritt 2.",
                ],
            )
            return

        try:
            remote = fetch_remote_news(url)
        except ValueError as exc:
            self._set_generator_log(
                "VERÖFFENTLICHUNGSPRÜFUNG",
                [
                    f"Lokale Artikelzahl: {local.get('articleCount', 0)}",
                    f"Adresse: {url}",
                    "",
                    f"✗ {exc}",
                ],
            )
            self.status_var.set("GitHub Pages konnte nicht geprüft werden.")
            return

        local_articles = local.get("articles", [])
        local_ids = {
            str(article.get("id", "")).strip()
            for article in local_articles
            if isinstance(article, dict) and article.get("id")
        }
        remote_ids = set(remote["ids"])

        local_count = local.get("articleCount")
        if not isinstance(local_count, int):
            local_count = len(local_articles) if isinstance(local_articles, list) else 0

        missing_remote = sorted(local_ids - remote_ids)
        unexpected_remote = sorted(remote_ids - local_ids)
        same = local_count == remote["count"] and not missing_remote and not unexpected_remote

        lines = [
            f"Lokale news.json: {local_count} Artikel",
            f"GitHub Pages:     {remote['count']} Artikel",
            f"Adresse: {url}",
        ]
        if remote["generatedAt"]:
            lines.append(f"Remote erzeugt am: {remote['generatedAt']}")
        lines.append("")

        if same:
            lines.append("✓ Veröffentlichung ist vollständig und aktuell.")
        else:
            lines.append("⚠ Lokale und veröffentlichte Version unterscheiden sich.")
            if missing_remote:
                lines.append("")
                lines.append("Auf GitHub Pages noch fehlend:")
                lines.extend(f"  - {article_id}" for article_id in missing_remote)
            if unexpected_remote:
                lines.append("")
                lines.append("Nur auf GitHub Pages vorhanden:")
                lines.extend(f"  - {article_id}" for article_id in unexpected_remote)
            lines.extend([
                "",
                "Bitte in GitHub Desktop committen und „Push origin“ ausführen.",
                "Danach etwa eine Minute warten und diese Prüfung wiederholen.",
            ])

        self._set_generator_log("VERÖFFENTLICHUNGSPRÜFUNG", lines)
        self.status_var.set(
            "Veröffentlichung bestätigt."
            if same else "GitHub Pages ist noch nicht auf dem lokalen Stand."
        )

    def refresh_all(self):
        self.refresh_counts()
        self.refresh_article_list()

    def refresh_counts(self):
        counts = collect_counts()
        for key in self.count_vars:
            self.count_vars[key].set(str(counts.get(key, 0)))

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
        self.article_text.delete("1.0", "end")
        self.article_notes.delete("1.0", "end")
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

        text_parts = []
        for section in data.get("article", []):
            if isinstance(section, dict):
                heading = section.get("heading", "").strip()
                text = section.get("text", "").strip()
                if heading:
                    text_parts.append(heading)
                if text:
                    text_parts.append(text)
        self.article_text.delete("1.0", "end")
        self.article_text.insert("1.0", "\n\n".join(text_parts))
        self.article_notes.delete("1.0", "end")
        self.article_notes.insert("1.0", data.get("notes", ""))
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
            "summary": self.article_vars["summary"].get().strip(),
            "planetaryBoundary":
                self.article_vars["planetaryBoundary"].get().strip(),
            "keywords": [
                x.strip() for x in self.article_vars["keywords"].get().split(",")
                if x.strip()
            ],
            "imageId": self.article_vars["imageId"].get().strip(),
            "sourceUrl": self.article_vars["sourceUrl"].get().strip(),
            "publicationDate":
                self.article_vars["publicationDate"].get().strip(),
            "author": self.article_vars["author"].get().strip(),
            "created": created,
            "lastModified": now,
            "language": "de",
            "article": [{
                "heading": "",
                "text": self.article_text.get("1.0", "end").strip(),
            }],
            "facts": [],
            "links": [],
            "license": "",
            "notes": self.article_notes.get("1.0", "end").strip(),
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
        report = inspect_release(write_output=True)

        lines = [
            f"Projektordner: {PROJECT_ROOT}",
            "",
            f"Freigegebene Artikel: {report['article_count']}",
            f"Verwendete Quellen: {report['source_count']}",
            f"Gefundene Bilder: {report['image_count']}",
            f"Gefundene Bildmetadaten: {report['metadata_count']}",
            "",
        ]

        if not report["ok"]:
            lines.append("FEHLER – news.json wurde nicht verändert.")
            lines.extend(f"✗ {item}" for item in report["errors"])
            self._set_generator_log("VERÖFFENTLICHUNG ABGEBROCHEN", lines)
            self.status_var.set("Generatorfehler – news.json wurde nicht verändert.")
            messagebox.showwarning(
                "Veröffentlichung nicht möglich",
                "Es wurden Fehler gefunden. Die vorhandene news.json wurde nicht überschrieben.",
            )
            return

        lines.extend([
            "✓ Keine blockierenden Fehler gefunden.",
            f"✓ news.json mit {report['article_count']} Artikel(n) erzeugt.",
            f"✓ Datei: {rel(OUTPUT)}",
        ])

        if report["warnings"]:
            lines.extend([
                "",
                "HINWEISE – news.json wurde trotzdem erzeugt:",
            ])
            lines.extend(f"⚠ {item}" for item in report["warnings"])

        lines.extend([
            "",
            "Zur Veröffentlichung gehörende Dateien:",
        ])
        lines.extend(f"  {rel(path)}" for path in report["release_files"])

        git_ok, git_lines = git_status_lines()
        lines.extend(["", "Lokaler Git-Status:"])
        lines.extend(f"  {line}" for line in git_lines)

        lines.extend([
            "",
            "Nächster Schritt:",
            "1. GitHub Desktop öffnen.",
            "2. Änderungen committen.",
            "3. „Push origin“ ausführen.",
            "4. Anschließend Schritt 4 des Assistenten verwenden.",
        ])

        self._set_generator_log("NEWS.JSON ERFOLGREICH ERZEUGT", lines)
        self.refresh_counts()
        self.status_var.set(
            f"news.json mit {report['article_count']} Artikel(n) erzeugt"
        )
        messagebox.showinfo(
            "news.json erfolgreich erzeugt",
            (
                f"news.json enthält jetzt {report['article_count']} Artikel.\n\n"
                "Die Dateien sind lokal vorbereitet. Bitte anschließend mit "
                "GitHub Desktop committen und pushen."
            ),
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
