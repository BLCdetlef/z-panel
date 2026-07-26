#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.12.1 – korrigierte Löschkaskade für Grundlagenbeiträge.

Benötigt im selben Ordner:
- news_studio_5_11.py
- news_studio_5_10.py
- news_studio_5_9.py
- news_studio_5_8.py
- news_studio_5_7.py
- news_studio_5_6.py
- news_studio_5_5_2.py und die bisherige Projektstruktur

Korrekturen gegenüber der fehlerhaften 5.12:
- Startfehler beim Zugriff auf messagebox behoben
- Verknüpfungen werden erst nach bestätigter Löschung verändert
- Startfehler werden in news_studio_5_12_startfehler.txt protokolliert

Neu gegenüber 5.11:
- eigener Löschbutton mit Löschkaskade für Grundlagenbeiträge
- beim Löschen einer Grundlage werden in allen betroffenen News
  die Felder explainerId und sequenceRole entfernt
- automatische Bereinigung verwaister explainerId-Verweise beim
  Aktualisieren und beim Erzeugen von news.json
"""

import importlib.util
import sys
import traceback
from pathlib import Path
from tkinter import messagebox
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_11.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_11.py wurde nicht gefunden.\n"
        "Lege News Studio 5.12 in denselben Ordner wie Version 5.11."
    )

def _write_start_error(exc: BaseException) -> Path:
    log_path = SCRIPT_DIR / "news_studio_5_12_startfehler.txt"
    details = (
        "ZUSTAND News Studio 5.12.1 konnte nicht gestartet werden.\n\n"
        f"Fehlertyp: {type(exc).__name__}\n"
        f"Fehler: {exc}\n\n"
        "Technische Details:\n"
        + traceback.format_exc()
    )
    try:
        log_path.write_text(details, encoding="utf-8")
    except OSError:
        pass
    return log_path


try:
    spec = importlib.util.spec_from_file_location(
        "news_studio_5_11_base", BASE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("News Studio 5.11 konnte nicht geladen werden.")

    base512 = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = base512
    spec.loader.exec_module(base512)
except BaseException as exc:
    if isinstance(exc, KeyboardInterrupt):
        raise
    log_path = _write_start_error(exc)
    try:
        messagebox.showerror(
            "News Studio 5.12.1 – Startfehler",
            "Das Studio konnte nicht gestartet werden.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            f"Ein Fehlerbericht wurde gespeichert unter:\n{log_path}",
        )
    except Exception:
        pass
    raise SystemExit(1) from exc

tk = base512.tk
ttk = base512.ttk

read_json_object = base512.read_json_object
write_json_atomic = base512.write_json_atomic
normalize_content_type = base512.normalize_content_type
OUTPUT = base512.OUTPUT
DRAFTS_DIR = base512.DRAFTS_DIR
ARTICLES_DIR = base512.ARTICLES_DIR


def article_id(article: dict[str, Any], fallback: str = "") -> str:
    return str(article.get("id") or fallback or "").strip()


def article_title(article: dict[str, Any]) -> str:
    return str(article.get("title") or "Ohne Titel").strip()


def article_dirs() -> list[Path]:
    return [DRAFTS_DIR, ARTICLES_DIR]


def article_files() -> list[Path]:
    files: list[Path] = []
    for folder in article_dirs():
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.json")):
            if (
                path.name.lower() == "index.json"
                or path.name.lower().endswith("_vorlage.json")
            ):
                continue
            files.append(path)
    return files


def existing_explainer_ids() -> set[str]:
    ids: set[str] = set()
    for path in article_files():
        article = read_json_object(path)
        if not isinstance(article, dict):
            continue
        if normalize_content_type(article.get("contentType"), article) == "explainer":
            identifier = article_id(article, path.stem)
            if identifier:
                ids.add(identifier)
    return ids


def linked_news_for_explainer(explainer_id: str) -> list[dict[str, str]]:
    """Liest betroffene News, ohne Dateien zu verändern."""
    explainer_id = str(explainer_id or "").strip()
    if not explainer_id:
        return []

    linked: list[dict[str, str]] = []
    for path in article_files():
        article = read_json_object(path)
        if not isinstance(article, dict):
            continue
        if normalize_content_type(article.get("contentType"), article) == "explainer":
            continue
        if str(article.get("explainerId") or "").strip() != explainer_id:
            continue
        linked.append(
            {
                "id": article_id(article, path.stem),
                "title": article_title(article),
                "path": str(path),
            }
        )
    linked.sort(key=lambda item: item["title"].casefold())
    return linked


def remove_explainer_links(explainer_id: str) -> dict[str, Any]:
    """Entfernt explainerId-Verweise auf eine gelöschte Grundlage."""
    explainer_id = str(explainer_id or "").strip()
    if not explainer_id:
        return {"changed": 0, "titles": []}

    changed = 0
    titles: list[str] = []

    for path in article_files():
        article = read_json_object(path)
        if not isinstance(article, dict):
            continue
        if normalize_content_type(article.get("contentType"), article) == "explainer":
            continue

        if str(article.get("explainerId") or "").strip() != explainer_id:
            continue

        article.pop("explainerId", None)
        if article.get("sequenceRole") == "context-news":
            article.pop("sequenceRole", None)

        write_json_atomic(path, article)
        changed += 1
        titles.append(article_title(article))

    return {"changed": changed, "titles": titles}


def cleanup_dangling_explainer_links() -> dict[str, Any]:
    """Bereinigt verwaiste explainerId-Verweise in News-Beiträgen."""
    valid = existing_explainer_ids()
    changed = 0
    details: list[str] = []

    for path in article_files():
        article = read_json_object(path)
        if not isinstance(article, dict):
            continue
        if normalize_content_type(article.get("contentType"), article) == "explainer":
            continue

        linked = str(article.get("explainerId") or "").strip()
        if not linked or linked in valid:
            continue

        article.pop("explainerId", None)
        if article.get("sequenceRole") == "context-news":
            article.pop("sequenceRole", None)
        write_json_atomic(path, article)
        changed += 1
        details.append(f'{article_id(article, path.stem)} → {linked}')

    return {"changed": changed, "details": details}


class NewsStudio512(base512.NewsStudio511):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.12.1")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.11", "ZUSTAND News Studio 5.12.1"
        )
        self._replace_widget_text(
            "News Studio 5.11 bereit │ reduzierte Grundlagenbilder und News→Grundlage-Folgen",
            "News Studio 5.12.1 bereit │ korrigierte Löschkaskade für Grundlagen",
        )

        self._add_delete_cascade_box()
        self._auto_cleanup_after_start()
        self.status_var.set(
            "News Studio 5.12.1 bereit │ Grundlagen löschen jetzt sicher mit Kaskade"
        )

    # ---------- UI ----------
    def _article_form_parent(self):
        notes = getattr(self, "article_notes", None)
        if notes is not None:
            return notes.master
        return getattr(self, "article_text").master

    def _add_delete_cascade_box(self) -> None:
        box = ttk.LabelFrame(
            self._article_form_parent(),
            text="Löschen und Verknüpfungen",
            padding=10,
        )
        box.pack(fill="x", pady=(10, 4))

        ttk.Label(
            box,
            text=(
                "Beim Löschen eines Grundlagenbeitrags entfernt das Studio "
                "automatisch alle explainerId-Verknüpfungen in den betroffenen News."
            ),
            wraplength=800,
            justify="left",
        ).pack(anchor="w", pady=(0, 6))

        row = ttk.Frame(box)
        row.pack(fill="x")
        ttk.Button(
            row,
            text="Aktuellen Beitrag löschen (mit Grundlagen-Kaskade)",
            command=self.delete_current_article_with_cascade,
        ).pack(side="left")

    # ---------- Hilfsfunktionen ----------
    def _current_article_path(self) -> Path | None:
        path = getattr(self, "current_article_path", None)
        if not path:
            return None
        return Path(path)

    def _current_article(self) -> dict[str, Any] | None:
        path = self._current_article_path()
        if path is None or not path.exists():
            return None
        article = read_json_object(path)
        return article if isinstance(article, dict) else None

    def _auto_cleanup_after_start(self) -> None:
        try:
            result = cleanup_dangling_explainer_links()
        except Exception:
            return
        if result["changed"] > 0:
            self.refresh_all()
            self.status_var.set(
                f'{result["changed"]} verwaiste Grundlagen-Verknüpfungen bereinigt'
            )

    # ---------- Kaskadierende Löschung ----------
    def delete_current_article_with_cascade(self) -> None:
        path = self._current_article_path()
        article = self._current_article()

        if path is None or article is None or not path.exists():
            messagebox.showwarning(
                "Kein Beitrag ausgewählt",
                "Es ist kein gespeicherter Beitrag ausgewählt, der gelöscht werden kann.",
                parent=self,
            )
            return

        content_type = normalize_content_type(article.get("contentType"), article)
        identifier = article_id(article, path.stem)
        title = article_title(article)

        if content_type == "explainer":
            linked_preview = linked_news_for_explainer(identifier)
            question = (
                f'Soll der Grundlagenbeitrag\n\n'
                f'"{title}"\n\n'
                f'wirklich gelöscht werden?'
            )
            if linked_preview:
                question += (
                    f'\n\nNach der Bestätigung werden außerdem '
                    f'{len(linked_preview)} verknüpfte News-Beiträge '
                    f'von dieser Grundlage gelöst.'
                )

            confirmed = messagebox.askyesno(
                "Grundlagenbeitrag löschen",
                question,
                parent=self,
            )
            if not confirmed:
                self.status_var.set("Löschen abgebrochen – keine Daten verändert")
                return

            # Zuerst die bestätigte Grundlage löschen. Verwaiste Links werden
            # anschließend entfernt; bei einem Bereinigungsfehler greift zusätzlich
            # die automatische Sicherheitsbereinigung beim nächsten Aktualisieren.
            try:
                path.unlink()
            except OSError as exc:
                messagebox.showerror(
                    "Löschen fehlgeschlagen",
                    f'Der Beitrag konnte nicht gelöscht werden:\n{exc}',
                    parent=self,
                )
                return

            try:
                linked = remove_explainer_links(identifier)
            except Exception as exc:
                linked = {
                    "changed": 0,
                    "titles": [item["title"] for item in linked_preview],
                }
                cleanup_dangling_explainer_links()
                messagebox.showwarning(
                    "Grundlage gelöscht – Bereinigung geprüft",
                    "Die Grundlage wurde gelöscht. Bei der unmittelbaren "
                    "Bereinigung trat ein Fehler auf; die Sicherheitsbereinigung "
                    f"wurde ausgeführt.\n\n{type(exc).__name__}: {exc}",
                    parent=self,
                )

            self.new_article()
            self.refresh_all()
            linked_titles = "; ".join(linked["titles"][:4])
            if len(linked["titles"]) > 4:
                linked_titles += " …"

            message = f'Grundlage "{title}" wurde gelöscht.'
            removed_count = linked.get("changed", 0)
            if removed_count > 0:
                message += (
                    f'\n\nVerknüpfungen aus {removed_count} News wurden entfernt.'
                )
                if linked_titles:
                    message += f'\nBetroffen: {linked_titles}'
            elif linked_preview:
                message += (
                    "\n\nDie verknüpften News wurden durch die "
                    "Sicherheitsbereinigung geprüft."
                )
            messagebox.showinfo("Grundlage gelöscht", message, parent=self)
            self.status_var.set(
                f'Grundlage gelöscht │ {removed_count} News-Verknüpfungen entfernt'
            )
            return

        # Normale News oder andere Beitragstypen: keine Kaskade nötig.
        confirmed = messagebox.askyesno(
            "Beitrag löschen",
            f'Soll der Beitrag\n\n"{title}"\n\nwirklich gelöscht werden?',
            parent=self,
        )
        if not confirmed:
            return

        try:
            path.unlink()
        except OSError as exc:
            messagebox.showerror(
                "Löschen fehlgeschlagen",
                f'Der Beitrag konnte nicht gelöscht werden:\n{exc}',
            )
            return

        self.new_article()
        self.refresh_all()
        messagebox.showinfo("Beitrag gelöscht", f'"{title}" wurde gelöscht.', parent=self)
        self.status_var.set("Beitrag gelöscht")

    # ---------- Zusätzliche Sicherheitsbereinigung ----------
    def refresh_all(self):
        result = super().refresh_all()
        try:
            cleanup_dangling_explainer_links()
        except Exception:
            return result
        return result

    def run_generator(self):
        try:
            cleanup = cleanup_dangling_explainer_links()
        except Exception:
            cleanup = {"changed": 0, "details": []}

        super().run_generator()

        if cleanup.get("changed", 0) > 0 and hasattr(self, "generator_log"):
            try:
                self.generator_log.configure(state="normal")
                self.generator_log.insert(
                    "end",
                    "\n\nLÖSCHKASKADE UND BEREINIGUNG 5.12\n"
                    f'✓ {cleanup["changed"]} verwaiste Grundlagen-Verknüpfungen bereinigt\n',
                )
                if cleanup["details"]:
                    self.generator_log.insert(
                        "end",
                        "Betroffen:\n- " + "\n- ".join(cleanup["details"][:10]) + "\n",
                    )
                self.generator_log.configure(state="disabled")
                self.generator_log.see("end")
            except Exception:
                pass


def main() -> None:
    try:
        app = NewsStudio512()
        app.mainloop()
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        log_path = _write_start_error(exc)
        try:
            messagebox.showerror(
                "News Studio 5.12.1 – Startfehler",
                "Das Studio wurde wegen eines Fehlers beendet.\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                f"Fehlerbericht:\n{log_path}",
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
