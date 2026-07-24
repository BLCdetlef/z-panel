#!/usr/bin/env python3
from __future__ import annotations

"""
ZUSTAND News Studio 3.1

Diese Datei wird neben news_studio_3_0.py abgelegt und gestartet.
Sie übernimmt die Oberfläche der Version 3.0 und korrigiert:

- automatische Artikel-IDs nach ZUSTAND-Logik, z. B. KL_0002
- automatische Bild-ID, z. B. KL_0002_01
- QS-Präfix für Querschnittsmeldungen
- kollisionsfreie Nummerierung über Entwürfe, Artikel und news.json
- sauberes Speichern ohne verwaiste Doppelfassungen
- Löschen aller Fassungen derselben Meldung aus Entwürfen und Artikeln
- Entfernen gelöschter Meldungen aus news.json
- Mehrfachauswahl beim Löschen
- Schutz vor erneutem Import derselben Originalquelle

Vorhandene Bilder werden beim Löschen bewusst NICHT automatisch entfernt.
"""

import importlib.util
import json
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_3_0.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_3_0.py wurde nicht gefunden.\n"
        "Lege news_studio_3_1.py in denselben Ordner wie news_studio_3_0.py."
    )

spec = importlib.util.spec_from_file_location("news_studio_3_0_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("news_studio_3_0.py konnte nicht geladen werden.")

base = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base
spec.loader.exec_module(base)

if "QS" not in base.BOUNDARIES:
    base.BOUNDARIES.append("QS")
base.BOUNDARY_IMAGE_HINTS.setdefault(
    "QS",
    "Menschen im sachlichen Austausch, Bildung, Demokratie, Zusammenarbeit "
    "oder Gemeinwohl ohne gestellte Werbeszene",
)

VALID_PREFIXES = ("KL", "BD", "LN", "FW", "NP", "OA", "OZ", "AE", "NS", "QS")
ID_PATTERN = re.compile(
    r"^(KL|BD|LN|FW|NP|OA|OZ|AE|NS|QS)_(\d{4})$",
    re.IGNORECASE,
)


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.lower().replace("–", "-").split())


def prefix_for_content(
    boundary: object = "",
    kind: object = "",
    title: object = "",
    summary: object = "",
) -> str:
    """Ordnet eine Meldung einer primären ZUSTAND-ID-Gruppe zu."""
    raw_boundary = str(boundary or "").strip().upper()
    if raw_boundary in VALID_PREFIXES:
        return raw_boundary

    kind_text = normalize_text(kind)
    text = normalize_text(f"{boundary} {title} {summary}")

    if "querschnitt" in kind_text:
        return "QS"

    # Spezifische Stoff- und Belastungsthemen zuerst prüfen.
    if any(term in text for term in (
        "neuartige substanz", "novel entit", "mikroplast", "plastik",
        "kunststoff", "pcb", "pfas", "chemikal", "schadstoff",
    )):
        return "NS"
    if any(term in text for term in (
        "atmospharische aerosol", "aerosol", "luftqualitat",
        "feinstaub", "stickoxid", "halogen",
    )):
        return "AE"
    if any(term in text for term in (
        "integritat der biosphare", "biosphare", "biodiversitat",
        "artenvielfalt", "artenruckgang", "vogel", "okosystem",
    )):
        return "BD"
    if any(term in text for term in (
        "biogeochem", "stickstoff", "phosphor", "nahrstoff",
        "eutroph", "algenblute",
    )):
        return "NP"
    if any(term in text for term in (
        "ozeanversauer", "ocean acid", "versauerung der meere",
    )):
        return "OA"
    if any(term in text for term in (
        "ozonschicht", "stratospharisches ozon", "ozonabbau",
    )):
        return "OZ"
    if any(term in text for term in (
        "susswasser", "frischwasser", "wasserhaushalt", "grundwasser",
        "fluss", "durre", "wasserknapp",
    )):
        return "FW"
    if any(term in text for term in (
        "landnutzung", "land-system", "entwald", "waldverlust",
        "versiegelung", "bodenflache",
    )):
        return "LN"
    if any(term in text for term in (
        "klimawandel", "klima", "co2", "dekarbon", "treibhaus",
        "erneuerbare", "kohle", "methan", "energiewende",
    )):
        return "KL"

    return "QS"


def iter_article_files():
    for folder in (base.ENTWUERFE, base.ARTIKEL):
        for path in base.json_files(folder):
            yield path


def read_article_id(path: Path) -> str:
    try:
        return str(base.read_json(path).get("id", "")).strip().upper()
    except Exception:
        return ""


def read_source_url(path: Path) -> str:
    try:
        return str(base.read_json(path).get("sourceUrl", "")).strip()
    except Exception:
        return ""


def all_used_ids() -> set[str]:
    used: set[str] = set()

    for path in iter_article_files():
        article_id = read_article_id(path)
        if article_id:
            used.add(article_id)

    if base.OUTPUT.exists():
        try:
            payload = base.read_json(base.OUTPUT)
            for article in payload.get("articles", []):
                article_id = str(article.get("id", "")).strip().upper()
                if article_id:
                    used.add(article_id)
        except Exception:
            pass

    return used


def next_article_id(prefix: str, additionally_reserved: set[str] | None = None) -> str:
    prefix = prefix.upper()
    if prefix not in VALID_PREFIXES:
        prefix = "QS"

    used = all_used_ids()
    if additionally_reserved:
        used.update(item.upper() for item in additionally_reserved)

    highest = 0
    for article_id in used:
        match = ID_PATTERN.fullmatch(article_id)
        if match and match.group(1).upper() == prefix:
            highest = max(highest, int(match.group(2)))

    return f"{prefix}_{highest + 1:04d}"


def files_for_article_id(article_id: str) -> list[Path]:
    article_id = str(article_id or "").strip().upper()
    if not article_id:
        return []

    matches: list[Path] = []
    for path in iter_article_files():
        stored_id = read_article_id(path)
        if stored_id == article_id or path.name.upper().startswith(article_id + "_"):
            matches.append(path)
    return sorted(set(matches))


def remove_ids_from_news_json(article_ids: set[str]) -> int:
    """Entfernt IDs aus der erzeugten news.json, ohne andere Artikel anzutasten."""
    normalized = {item.strip().upper() for item in article_ids if item.strip()}
    if not normalized or not base.OUTPUT.exists():
        return 0

    try:
        payload = base.read_json(base.OUTPUT)
    except Exception:
        return 0

    articles = payload.get("articles")
    if not isinstance(articles, list):
        return 0

    kept = [
        article for article in articles
        if str(article.get("id", "")).strip().upper() not in normalized
    ]
    removed = len(articles) - len(kept)
    if not removed:
        return 0

    payload["articles"] = kept
    payload["articleCount"] = len(kept)
    payload["generatedAt"] = datetime.now(timezone.utc).isoformat()
    base.write_json(base.OUTPUT, payload)
    return removed


def remove_article_files(article_ids: set[str], keep: Path | None = None) -> int:
    keep_resolved = keep.resolve() if keep else None
    deleted = 0

    for article_id in article_ids:
        for path in files_for_article_id(article_id):
            try:
                if keep_resolved and path.resolve() == keep_resolved:
                    continue
            except OSError:
                pass
            path.unlink(missing_ok=True)
            deleted += 1

    return deleted


def existing_source_urls() -> set[str]:
    urls = {url for path in iter_article_files() if (url := read_source_url(path))}
    if base.OUTPUT.exists():
        try:
            payload = base.read_json(base.OUTPUT)
            for article in payload.get("articles", []):
                url = str(article.get("sourceUrl", "")).strip()
                if url:
                    urls.add(url)
        except Exception:
            pass
    return urls


class NewsStudio31(base.NewsStudio):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 3.1")

        if hasattr(self, "article_list"):
            self.article_list.configure(selectmode="extended")
            self.article_list.bind("<Delete>", lambda _event: self.delete_article())

        self._replace_widget_text("ZUSTAND News Studio 3.0", "ZUSTAND News Studio 3.1")
        self._replace_widget_text("Datei löschen", "Auswahl überall löschen")
        self.status_var.set(
            "News Studio 3.1 bereit │ automatische IDs und bereinigtes Löschen aktiv"
        )

    def _replace_widget_text(self, old: str, new: str) -> None:
        def walk(widget):
            try:
                if widget.cget("text") == old:
                    widget.configure(text=new)
            except Exception:
                pass
            for child in widget.winfo_children():
                walk(child)

        walk(self)

    def _ensure_valid_editor_ids(self) -> tuple[str, str | None]:
        old_id = self.article_vars["id"].get().strip()
        current_id = old_id.upper()

        title = self.article_vars["title"].get().strip()
        summary = self.summary_text.get("1.0", "end").strip()
        boundary = self.article_vars["planetaryBoundary"].get().strip()

        if not ID_PATTERN.fullmatch(current_id):
            prefix = prefix_for_content(boundary, "", title, summary)
            current_id = next_article_id(prefix)
            self.article_vars["id"].set(current_id)
            self.article_vars["planetaryBoundary"].set(prefix)

        image_id = self.article_vars["imageId"].get().strip()
        if (
            not image_id
            or (old_id and image_id.upper().startswith(old_id.upper() + "_"))
        ):
            self.article_vars["imageId"].set(f"{current_id}_01")

        return current_id, old_id or None

    def save_article(self, status):
        article_id, old_id = self._ensure_valid_editor_ids()

        try:
            data = self.article_payload(status)
        except ValueError as exc:
            base.messagebox.showwarning("Angaben fehlen", str(exc))
            return

        target_folder = base.ENTWUERFE if status == "entwurf" else base.ARTIKEL
        filename = f"{data['id']}_{base.slug(data['title'])}.json"
        target = target_folder / filename

        ids_to_clean = {article_id}
        if old_id and old_id.upper() != article_id:
            ids_to_clean.add(old_id.upper())

        # Die aktuell geöffnete Datei kann eine alte oder falsch benannte Fassung sein.
        if self.current_article_path and self.current_article_path != target:
            self.current_article_path.unlink(missing_ok=True)

        remove_article_files(ids_to_clean, keep=target)
        base.write_json(target, data)

        # Ein wieder zum Entwurf gemachter Artikel darf nicht veraltet in news.json bleiben.
        if status == "entwurf":
            remove_ids_from_news_json({article_id})

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
        self.status_var.set(f"{article_id} wurde {action}.")
        base.messagebox.showinfo(
            "Meldung erfolgreich gespeichert",
            f"{article_id} wurde {action}.\n\n"
            f"Artikel-ID: {article_id}\n"
            f"Bild-ID: {data['imageId']}\n"
            f"Datei: {base.rel(target)}",
        )

    def delete_article(self):
        selected_paths: list[Path] = []
        if hasattr(self, "article_list"):
            for item in self.article_list.selection():
                path = self.article_paths.get(item)
                if path:
                    selected_paths.append(path)

        if not selected_paths and self.current_article_path:
            selected_paths = [self.current_article_path]

        if not selected_paths:
            base.messagebox.showinfo(
                "Keine Meldung ausgewählt",
                "Bitte eine oder mehrere Meldungen auswählen.",
            )
            return

        article_ids: set[str] = set()
        fallback_paths: set[Path] = set()

        for path in selected_paths:
            article_id = read_article_id(path)
            if article_id:
                article_ids.add(article_id)
            else:
                fallback_paths.add(path)

        display_ids = ", ".join(sorted(article_ids)) or "ausgewählte Datei(en)"
        confirmed = base.messagebox.askyesno(
            "Meldung überall löschen",
            (
                f"Sollen {len(selected_paths)} ausgewählte Meldung(en) wirklich "
                f"gelöscht werden?\n\n"
                f"IDs: {display_ids}\n\n"
                "Gelöscht werden alle Fassungen mit derselben Artikel-ID aus:\n"
                "• newsredaktion/entwuerfe\n"
                "• newsredaktion/artikel\n"
                "• dem Artikelbestand in news.json\n\n"
                "Vorhandene Bilddateien und Bildmetadaten bleiben zur Sicherheit erhalten."
            ),
        )
        if not confirmed:
            return

        deleted_files = remove_article_files(article_ids)
        for path in fallback_paths:
            if path.exists():
                path.unlink(missing_ok=True)
                deleted_files += 1

        removed_output = remove_ids_from_news_json(article_ids)

        self.new_article()
        self.refresh_all()
        self.status_var.set(
            f"{deleted_files} Artikeldatei(en) und "
            f"{removed_output} news.json-Eintrag/Einträge gelöscht."
        )
        base.messagebox.showinfo(
            "Löschen abgeschlossen",
            (
                f"{deleted_files} Artikeldatei(en) wurden entfernt.\n"
                f"{removed_output} Eintrag/Einträge wurden aus news.json entfernt.\n\n"
                "Bilder wurden nicht gelöscht."
            ),
        )

    def import_research_json(self, raw_text, dialog=None):
        raw_text = raw_text.strip()
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()

        try:
            items = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            base.messagebox.showerror(
                "JSON konnte nicht gelesen werden",
                f"Zeile {exc.lineno}, Spalte {exc.colno}: {exc.msg}",
            )
            return

        if not isinstance(items, list):
            base.messagebox.showerror(
                "Falsches Format",
                "Die ChatGPT-Antwort muss ein JSON-Array mit Meldungen sein.",
            )
            return

        imported = 0
        skipped: list[str] = []
        today = date.today().isoformat()
        reserved_ids: set[str] = set()
        known_urls = existing_source_urls()

        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                skipped.append(f"Meldung {index}: kein JSON-Objekt")
                continue

            title = str(item.get("title", "")).strip()
            summary = str(item.get("summary", "")).strip()
            source_url = str(item.get("sourceUrl", "")).strip()
            source_title = str(item.get("sourceTitle", "")).strip()
            publication_date = str(item.get("publicationDate", "")).strip()
            boundary_label = str(item.get("boundary", "")).strip()
            kind = str(item.get("type", "")).strip()
            priority = str(item.get("priority", "")).strip()

            if not title or not summary:
                skipped.append(f"Meldung {index}: Titel oder Kurztext fehlt")
                continue
            if not source_url or not base.valid_url(source_url):
                skipped.append(f"Meldung {index}: gültiger Direktlink fehlt")
                continue
            if source_url in known_urls:
                skipped.append(f"Meldung {index}: Originalquelle bereits vorhanden")
                continue
            try:
                date.fromisoformat(publication_date)
            except ValueError:
                skipped.append(f"Meldung {index}: Veröffentlichungsdatum ungültig")
                continue

            prefix = prefix_for_content(
                boundary_label,
                kind,
                title,
                summary,
            )
            article_id = next_article_id(prefix, reserved_ids)
            reserved_ids.add(article_id)
            known_urls.add(source_url)

            keywords = item.get("keywords", [])
            if isinstance(keywords, str):
                keywords = [
                    value.strip() for value in keywords.split(",") if value.strip()
                ]
            elif isinstance(keywords, list):
                keywords = [
                    str(value).strip() for value in keywords if str(value).strip()
                ]
            else:
                keywords = []

            for extra in (
                kind,
                f"Priorität {priority}" if priority else "",
                boundary_label,
            ):
                if extra and extra not in keywords:
                    keywords.append(extra)

            data = {
                "id": article_id,
                "status": "entwurf",
                "title": title,
                "subtitle": "",
                "summary": summary,
                "planetaryBoundary": prefix,
                "keywords": keywords,
                "imageId": f"{article_id}_01",
                "sourceId": "",
                "sourceTitle": source_title,
                "sourceUrl": source_url,
                "publicationDate": publication_date,
                "author": "",
                "editor": "",
                "created": today,
                "lastModified": today,
                "language": "de",
                "article": [],
                "facts": [],
                "links": [],
                "license": "",
                "notes": (
                    "Importiert über Recherche-Assistent 3.1; "
                    f"Meldungsart: {kind}; Priorität: {priority}; "
                    f"inhaltliche Zuordnung: {boundary_label}"
                ),
            }

            target = base.ENTWUERFE / f"{article_id}_{base.slug(title)}.json"
            remove_article_files({article_id}, keep=target)
            base.write_json(target, data)
            imported += 1

        self.refresh_all()

        if dialog is not None and imported:
            dialog.destroy()

        details = [
            f"{imported} Meldung(en) wurden als Entwürfe importiert.",
            "Artikel- und Bild-IDs wurden automatisch vergeben.",
        ]
        if skipped:
            details.append("")
            details.append(f"{len(skipped)} Meldung(en) wurden übersprungen:")
            details.extend(f"• {reason}" for reason in skipped[:12])

        base.messagebox.showinfo("Rechercheimport abgeschlossen", "\n".join(details))
        self.status_var.set(
            f"Rechercheimport: {imported} Entwurf/Entwürfe angelegt, "
            f"{len(skipped)} übersprungen."
        )


if __name__ == "__main__":
    NewsStudio31().mainloop()
