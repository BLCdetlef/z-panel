#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.20 – Titeltextfilter in der Beitragsliste.

Baut direkt auf der funktionierenden Windows-Fassung 5.19.1 auf.

Neu:
- Suchfeld „Titel filtern“ oberhalb der Beitragsliste
- Filterung während der Eingabe
- Groß-/Kleinschreibung wird ignoriert
- mehrere Suchwörter müssen alle im Titel vorkommen
- Trefferanzeige
- Schaltfläche „Zurücksetzen“
- keine Änderung an Artikeldateien oder news.json
"""

import importlib.util
import sys
import traceback
from pathlib import Path
from tkinter import messagebox
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_19.py"


def _write_start_error(exc: BaseException) -> Path:
    path = SCRIPT_DIR / "news_studio_5_20_startfehler.txt"
    content = (
        "ZUSTAND News Studio 5.20 konnte nicht gestartet werden.\n\n"
        f"Fehlertyp: {type(exc).__name__}\n"
        f"Fehler: {exc}\n\n"
        "Technische Details:\n"
        + traceback.format_exc()
    )
    try:
        path.write_text(content, encoding="utf-8")
    except OSError:
        pass
    return path


if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_19.py wurde nicht gefunden.\n"
        "Lege News Studio 5.20 in denselben Ordner wie die funktionierende Version 5.19.1."
    )

try:
    spec = importlib.util.spec_from_file_location(
        "news_studio_5_19_base", BASE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("News Studio 5.19.1 konnte nicht geladen werden.")

    base520 = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = base520
    spec.loader.exec_module(base520)
except BaseException as exc:
    if isinstance(exc, KeyboardInterrupt):
        raise
    log_path = _write_start_error(exc)
    try:
        messagebox.showerror(
            "News Studio 5.20 – Startfehler",
            "Die Versionskette konnte nicht geladen werden.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            f"Fehlerbericht:\n{log_path}",
        )
    except Exception:
        pass
    raise SystemExit(1) from exc

tk = base520.tk
ttk = base520.ttk


def _normalize(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


class NewsStudio520(base520.NewsStudio519):
    def __init__(self):
        # Die Basisklasse kann refresh_all() bereits während ihres Aufbaus aufrufen.
        self._title_filter_ready = False
        self._title_filter_tree = None
        self._title_filter_column = None
        self._title_filter_order: list[str] = []
        self._title_filter_updating = False

        super().__init__()
        self.title("ZUSTAND News Studio 5.20")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.19.1",
            "ZUSTAND News Studio 5.20",
        )

        self.title_filter_var = tk.StringVar(value="")
        self.title_filter_count_var = tk.StringVar(value="")
        self.after_idle(self._install_title_filter)

        self.status_var.set(
            "News Studio 5.20 bereit │ Titeltextfilter wird eingerichtet"
        )

    # ------------------------------------------------------------------
    # Treeview und Titelspalte erkennen
    # ------------------------------------------------------------------
    def _walk_widgets(self, widget):
        yield widget
        for child in widget.winfo_children():
            yield from self._walk_widgets(child)

    def _find_article_tree(self):
        # Bekannte Attributnamen zuerst.
        for name in (
            "article_tree",
            "articles_tree",
            "article_list",
            "articles_list",
            "tree_articles",
        ):
            candidate = getattr(self, name, None)
            try:
                if candidate is not None and candidate.winfo_class() == "Treeview":
                    if self._find_title_column(candidate) is not None:
                        return candidate
            except Exception:
                pass

        # Danach alle Treeviews prüfen und den mit Überschrift „Titel“ verwenden.
        for widget in self._walk_widgets(self):
            try:
                if widget.winfo_class() != "Treeview":
                    continue
            except Exception:
                continue
            if self._find_title_column(widget) is not None:
                return widget

        return None

    def _find_title_column(self, tree):
        # Explizite Daten-Spalten.
        try:
            columns = list(tree.cget("columns"))
        except Exception:
            columns = []

        for column in columns:
            try:
                heading = str(tree.heading(column, "text") or "")
            except Exception:
                heading = ""
            if _normalize(heading) == "titel":
                return column

        # Optional die Baumspalte #0.
        try:
            if _normalize(tree.heading("#0", "text")) == "titel":
                return "#0"
        except Exception:
            pass

        return None

    # ------------------------------------------------------------------
    # Filterleiste einbauen
    # ------------------------------------------------------------------
    def _install_title_filter(self) -> None:
        if self._title_filter_ready:
            return

        tree = self._find_article_tree()
        if tree is None:
            self.status_var.set(
                "Titeltextfilter konnte die Beitragsliste nicht erkennen."
            )
            return

        title_column = self._find_title_column(tree)
        if title_column is None:
            self.status_var.set(
                "Titeltextfilter konnte die Titelspalte nicht erkennen."
            )
            return

        parent = tree.master
        bar = ttk.Frame(parent)

        if not self._place_filter_bar(parent, tree, bar):
            self.status_var.set(
                "Titeltextfilter konnte nicht oberhalb der Liste platziert werden."
            )
            return

        ttk.Label(bar, text="Titel filtern:").pack(side="left")

        entry = ttk.Entry(
            bar,
            textvariable=self.title_filter_var,
            width=34,
        )
        entry.pack(side="left", fill="x", expand=True, padx=(8, 6))

        ttk.Button(
            bar,
            text="Zurücksetzen",
            command=self._clear_title_filter,
        ).pack(side="left", padx=(0, 8))

        ttk.Label(
            bar,
            textvariable=self.title_filter_count_var,
            width=16,
            anchor="e",
        ).pack(side="right")

        self._title_filter_tree = tree
        self._title_filter_column = title_column
        self._title_filter_ready = True

        self.title_filter_var.trace_add(
            "write",
            lambda *_args: self._apply_title_filter(),
        )
        entry.bind("<Escape>", lambda _event: self._clear_title_filter())
        entry.bind("<Control-a>", self._select_filter_text)
        entry.bind("<Control-A>", self._select_filter_text)

        self._snapshot_tree_order()
        self._apply_title_filter()
        self.status_var.set(
            "News Studio 5.20 bereit │ Titeltextfilter aktiv"
        )

    def _place_filter_bar(self, parent, tree, bar) -> bool:
        try:
            manager = tree.winfo_manager()
        except Exception:
            manager = ""

        # Reale Beitragsliste verwendet voraussichtlich pack().
        if manager == "pack":
            try:
                packed = list(parent.pack_slaves())
                first = packed[0] if packed else tree
                bar.pack(
                    side="top",
                    fill="x",
                    pady=(0, 7),
                    before=first,
                )
                return True
            except Exception:
                return False

        # Sicherheitsfallback für grid(): alle vorhandenen Zeilen um eins verschieben.
        if manager == "grid":
            try:
                slaves = list(parent.grid_slaves())
                grid_data = []
                for child in slaves:
                    info = dict(child.grid_info())
                    info.pop("in", None)
                    grid_data.append((child, info))

                # Von unten nach oben verschieben, damit nichts kollidiert.
                grid_data.sort(
                    key=lambda item: int(item[1].get("row", 0)),
                    reverse=True,
                )
                for child, info in grid_data:
                    info["row"] = int(info.get("row", 0)) + 1
                    child.grid_configure(**info)

                max_column = 0
                for _child, info in grid_data:
                    column = int(info.get("column", 0))
                    span = int(info.get("columnspan", 1))
                    max_column = max(max_column, column + span - 1)

                bar.grid(
                    row=0,
                    column=0,
                    columnspan=max_column + 1,
                    sticky="ew",
                    pady=(0, 7),
                )
                parent.grid_columnconfigure(max_column, weight=1)
                return True
            except Exception:
                return False

        return False

    def _select_filter_text(self, _event=None):
        # Das fokussierte Entry ist das Suchfeld.
        try:
            widget = self.focus_get()
            widget.selection_range(0, "end")
            widget.icursor("end")
        except Exception:
            pass
        return "break"

    def _clear_title_filter(self) -> None:
        self.title_filter_var.set("")

    # ------------------------------------------------------------------
    # Filterlogik
    # ------------------------------------------------------------------
    def _tree_title(self, item_id: str) -> str:
        tree = self._title_filter_tree
        column = self._title_filter_column
        if tree is None or column is None:
            return ""

        try:
            if column == "#0":
                return str(tree.item(item_id, "text") or "")
            return str(tree.set(item_id, column) or "")
        except Exception:
            return ""

    def _all_root_items(self) -> list[str]:
        """Gibt sichtbare und derzeit abgehängte Root-Items in Originalreihenfolge zurück."""
        tree = self._title_filter_tree
        if tree is None:
            return []

        existing: list[str] = []
        for item_id in self._title_filter_order:
            try:
                if tree.exists(item_id):
                    existing.append(item_id)
            except Exception:
                pass

        # Neue Items ergänzen, die seit dem letzten Snapshot hinzugekommen sind.
        try:
            visible = list(tree.get_children(""))
        except Exception:
            visible = []

        for item_id in visible:
            if item_id not in existing:
                existing.append(item_id)

        return existing

    def _restore_all_tree_items(self) -> None:
        tree = self._title_filter_tree
        if tree is None:
            return

        for index, item_id in enumerate(self._all_root_items()):
            try:
                tree.reattach(item_id, "", index)
            except Exception:
                pass

    def _snapshot_tree_order(self) -> None:
        tree = self._title_filter_tree
        if tree is None:
            return

        # Vor dem Snapshot alle bereits gefilterten Items wieder einhängen.
        self._restore_all_tree_items()
        try:
            self._title_filter_order = list(tree.get_children(""))
        except Exception:
            self._title_filter_order = []

    def _apply_title_filter(self) -> None:
        if (
            not self._title_filter_ready
            or self._title_filter_updating
            or self._title_filter_tree is None
        ):
            return

        self._title_filter_updating = True
        try:
            tree = self._title_filter_tree
            terms = [
                part
                for part in _normalize(self.title_filter_var.get()).split()
                if part
            ]

            all_items = self._all_root_items()
            matching: list[str] = []

            for item_id in all_items:
                title = _normalize(self._tree_title(item_id))
                is_match = all(term in title for term in terms)

                if is_match:
                    matching.append(item_id)
                else:
                    try:
                        tree.detach(item_id)
                    except Exception:
                        pass

            # Treffer wieder in ihrer ursprünglichen Reihenfolge einhängen.
            for index, item_id in enumerate(matching):
                try:
                    tree.reattach(item_id, "", index)
                except Exception:
                    pass

            total = len(all_items)
            shown = len(matching)
            if terms:
                self.title_filter_count_var.set(f"{shown} von {total}")
            else:
                self.title_filter_count_var.set(f"{total} Beiträge")
        finally:
            self._title_filter_updating = False

    # ------------------------------------------------------------------
    # Aktualisieren ohne Konflikte mit abgehängten Treeview-Einträgen
    # ------------------------------------------------------------------
    def refresh_all(self):
        # Manche Basismethoden löschen nur sichtbare Treeview-Einträge.
        # Deshalb vor der Aktualisierung alle gefilterten Einträge wieder anhängen.
        if getattr(self, "_title_filter_ready", False):
            self._restore_all_tree_items()

        result = super().refresh_all()

        if getattr(self, "_title_filter_ready", False):
            self.after_idle(self._after_article_refresh)
        return result

    def _after_article_refresh(self) -> None:
        self._snapshot_tree_order()
        self._apply_title_filter()


def main() -> None:
    try:
        app = NewsStudio520()
        app.mainloop()
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        log_path = _write_start_error(exc)
        try:
            messagebox.showerror(
                "News Studio 5.20 – Startfehler",
                "Das Studio wurde wegen eines Fehlers beendet.\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                f"Fehlerbericht:\n{log_path}",
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
