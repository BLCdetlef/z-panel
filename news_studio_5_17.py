#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.17 – stabile große Felder für Titel und Kurzfassung.

Diese Version baut bewusst direkt auf News Studio 5.14 auf. Sie ersetzt nicht
mehr ein vermutetes internes Eingabewidget, sondern jeweils die komplette
sichtbare Formularzeile „Titel“ bzw. „Kurzfassung“.

Benötigt im selben Ordner:
- news_studio_5_14.py
- news_studio_5_13.py
- die korrigierte news_studio_5_12.py
- alle bisherigen Basisdateien

Feldgrößen:
- Titel: 2 sichtbare Zeilen
- Kurzfassung: 10 sichtbare Zeilen
"""

import importlib.util
import sys
import traceback
from pathlib import Path
from tkinter import messagebox
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_14.py"


def _write_start_error(exc: BaseException) -> Path:
    path = SCRIPT_DIR / "news_studio_5_17_startfehler.txt"
    content = (
        "ZUSTAND News Studio 5.17 konnte nicht gestartet werden.\n\n"
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
        "news_studio_5_14.py wurde nicht gefunden.\n"
        "Lege News Studio 5.17 in denselben Ordner wie Version 5.14."
    )

try:
    spec = importlib.util.spec_from_file_location(
        "news_studio_5_14_base", BASE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("News Studio 5.14 konnte nicht geladen werden.")

    base517 = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = base517
    spec.loader.exec_module(base517)
except BaseException as exc:
    if isinstance(exc, KeyboardInterrupt):
        raise
    log_path = _write_start_error(exc)
    try:
        messagebox.showerror(
            "News Studio 5.17 – Startfehler",
            "Die Versionskette konnte nicht geladen werden.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            f"Fehlerbericht:\n{log_path}",
        )
    except Exception:
        pass
    raise SystemExit(1) from exc

tk = base517.tk
ttk = base517.ttk
read_json_object = base517.read_json_object


def _normal(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


class NewsStudio517(base517.NewsStudio514):
    def __init__(self):
        # Die Basisklasse ruft während __init__ bereits überschreibbare Methoden
        # auf. Alle dort verwendeten Zustände müssen deshalb vorher existieren.
        self._large_fields: dict[str, dict[str, Any]] = {}
        self._large_fields_installed = False
        self._large_fields_installing = False

        super().__init__()
        self.title("ZUSTAND News Studio 5.17")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.14", "ZUSTAND News Studio 5.17"
        )

        self.after_idle(self._install_large_rows)
        self.status_var.set(
            "News Studio 5.17 bereit │ große Textfelder werden eingerichtet"
        )

    # ------------------------------------------------------------------
    # Widgetsuche
    # ------------------------------------------------------------------
    def _walk(self, widget):
        yield widget
        for child in widget.winfo_children():
            yield from self._walk(child)

    def _article_root(self):
        finder = getattr(self, "_article_form_parent", None)
        if callable(finder):
            try:
                root = finder()
                if root is not None:
                    return root
            except Exception:
                pass
        return self

    def _visible(self, widget) -> bool:
        try:
            return bool(widget.winfo_viewable()) and bool(widget.winfo_manager())
        except Exception:
            return False

    def _find_visible_grid_label(self, text: str):
        wanted = _normal(text)
        root = self._article_root()

        try:
            self.update_idletasks()
        except Exception:
            pass

        matches = []
        for widget in self._walk(root):
            try:
                if widget.winfo_class() not in {"TLabel", "Label"}:
                    continue
                if _normal(widget.cget("text")) != wanted:
                    continue
                if widget.winfo_manager() != "grid":
                    continue
                if not self._visible(widget):
                    continue
                matches.append(widget)
            except Exception:
                continue

        # Bei mehreren Treffern den am weitesten rechts liegenden verwenden:
        # Das ist die Bearbeitungsmaske und nicht etwa eine Überschrift links.
        matches.sort(
            key=lambda widget: widget.winfo_rootx()
            if self._visible(widget)
            else -1,
            reverse=True,
        )
        return matches[0] if matches else None

    def _row_widgets(self, label):
        parent = label.master
        info = label.grid_info()
        row = int(info.get("row", 0))

        result = []
        for child in parent.winfo_children():
            try:
                if child.winfo_manager() != "grid":
                    continue
                child_info = child.grid_info()
                if int(child_info.get("row", -1)) == row:
                    result.append(child)
            except Exception:
                continue

        return parent, row, result

    def _backing_inputs(self, widgets):
        accepted = {
            "TEntry",
            "Entry",
            "TCombobox",
            "Combobox",
        }
        result = []
        for widget in widgets:
            try:
                if widget.winfo_class() in accepted:
                    result.append(widget)
            except Exception:
                continue
        return result

    # ------------------------------------------------------------------
    # Installation der kompletten Formularzeilen
    # ------------------------------------------------------------------
    def _install_large_rows(self) -> None:
        if self._large_fields_installed or self._large_fields_installing:
            return

        self._large_fields_installing = True
        try:
            title_ok = self._replace_form_row(
                field_key="title",
                label_text="Titel",
                height=2,
            )
            summary_ok = self._replace_form_row(
                field_key="summary",
                label_text="Kurzfassung",
                height=10,
            )
            self._large_fields_installed = title_ok or summary_ok
        finally:
            self._large_fields_installing = False

        self.after_idle(self._refresh_large_fields)

        if title_ok and summary_ok:
            self.status_var.set(
                "Titel zweizeilig und Kurzfassung zehnzeilig eingerichtet."
            )
        elif title_ok:
            self.status_var.set(
                "Titel wurde vergrößert; Kurzfassung konnte nicht ersetzt werden."
            )
        elif summary_ok:
            self.status_var.set(
                "Kurzfassung wurde vergrößert; Titel konnte nicht ersetzt werden."
            )
        else:
            self.status_var.set(
                "Die sichtbaren Zeilen Titel/Kurzfassung wurden nicht gefunden."
            )
            self._write_ui_diagnostics()

    def _replace_form_row(
        self,
        field_key: str,
        label_text: str,
        height: int,
    ) -> bool:
        label = self._find_visible_grid_label(label_text)
        if label is None:
            return False

        try:
            parent, row, row_widgets = self._row_widgets(label)
        except Exception:
            return False

        if not row_widgets:
            return False

        columns = []
        for widget in row_widgets:
            try:
                info = widget.grid_info()
                column = int(info.get("column", 0))
                span = int(info.get("columnspan", 1))
                columns.extend(range(column, column + max(span, 1)))
            except Exception:
                continue

        if not columns:
            return False

        first_column = min(columns)
        last_column = max(columns)
        columnspan = last_column - first_column + 1
        backing_widgets = self._backing_inputs(row_widgets)

        for widget in row_widgets:
            try:
                widget.grid_remove()
            except Exception:
                pass

        replacement = ttk.Frame(parent)
        replacement.grid(
            row=row,
            column=first_column,
            columnspan=columnspan,
            sticky="nsew",
            pady=(3, 4),
        )
        replacement.columnconfigure(1, weight=1)

        ttk.Label(
            replacement,
            text=label_text,
            width=18,
            anchor="nw",
        ).grid(row=0, column=0, sticky="nw", padx=(0, 8), pady=(5, 0))

        text_widget = tk.Text(
            replacement,
            height=height,
            width=1,
            wrap="word",
            undo=True,
            maxundo=100,
            autoseparators=True,
            relief="solid",
            borderwidth=1,
            highlightthickness=0,
            padx=7,
            pady=6,
            spacing1=1,
            spacing3=1,
            font=("Segoe UI", 10),
            takefocus=True,
        )
        text_widget.grid(row=0, column=1, sticky="nsew")

        try:
            parent.grid_columnconfigure(last_column, weight=1)
            parent.update_idletasks()
            self.update_idletasks()
        except Exception:
            pass

        variable = getattr(self, "article_vars", {}).get(field_key)
        state = {
            "field": field_key,
            "widget": text_widget,
            "variable": variable,
            "backing": backing_widgets,
            "replacement": replacement,
            "syncing": False,
        }
        self._large_fields[field_key] = state

        text_widget.bind(
            "<<Modified>>",
            lambda _event, key=field_key: self._text_changed(key),
            add="+",
        )
        text_widget.bind(
            "<FocusOut>",
            lambda _event, key=field_key: self._flush_field(key),
            add="+",
        )
        text_widget.bind(
            "<Control-a>",
            lambda _event, widget=text_widget: self._select_all(widget),
        )
        text_widget.bind(
            "<Control-A>",
            lambda _event, widget=text_widget: self._select_all(widget),
        )
        text_widget.bind(
            "<Tab>",
            lambda _event, widget=text_widget: self._focus_next(widget),
        )
        text_widget.bind(
            "<Shift-Tab>",
            lambda _event, widget=text_widget: self._focus_previous(widget),
        )
        text_widget.bind(
            "<ISO_Left_Tab>",
            lambda _event, widget=text_widget: self._focus_previous(widget),
        )

        if field_key == "title":
            text_widget.bind(
                "<Return>",
                lambda _event, widget=text_widget: self._focus_next(widget),
            )

        if variable is not None:
            try:
                variable.trace_add(
                    "write",
                    lambda *_args, key=field_key: self._variable_changed(key),
                )
            except Exception:
                pass

        return True

    # ------------------------------------------------------------------
    # Daten und Synchronisierung
    # ------------------------------------------------------------------
    def _current_article_data(self):
        path = getattr(self, "current_article_path", None)
        if not path:
            return None
        try:
            return read_json_object(Path(path))
        except Exception:
            return None

    def _backing_value(self, state) -> str:
        for widget in state["backing"]:
            try:
                value = str(widget.get() or "")
                if value:
                    return value
            except Exception:
                continue
        return ""

    def _authoritative_value(self, field_key: str) -> str:
        state = self._large_fields[field_key]

        article = self._current_article_data()
        if isinstance(article, dict) and field_key in article:
            return str(article.get(field_key) or "")

        variable = state.get("variable")
        if variable is not None:
            try:
                value = str(variable.get() or "")
                if value:
                    return value
            except Exception:
                pass

        return self._backing_value(state)

    def _set_large_text(self, state, value: str) -> None:
        widget = state["widget"]
        current = widget.get("1.0", "end-1c")
        if current == value:
            return

        state["syncing"] = True
        try:
            widget.delete("1.0", "end")
            widget.insert("1.0", value)
            widget.edit_modified(False)
        finally:
            state["syncing"] = False

    def _set_backing(self, state, value: str) -> None:
        state["syncing"] = True
        try:
            variable = state.get("variable")
            if variable is not None:
                try:
                    if str(variable.get() or "") != value:
                        variable.set(value)
                except Exception:
                    pass

            for widget in state["backing"]:
                try:
                    current = str(widget.get() or "")
                except Exception:
                    continue
                if current == value:
                    continue
                try:
                    widget.delete(0, "end")
                    widget.insert(0, value)
                except Exception:
                    pass
        finally:
            state["syncing"] = False

    def _refresh_field(self, field_key: str) -> None:
        state = self._large_fields.get(field_key)
        if not state or state["syncing"]:
            return
        value = self._authoritative_value(field_key)
        self._set_large_text(state, value)
        self._set_backing(state, value)

    def _refresh_large_fields(self) -> None:
        for key in ("title", "summary"):
            if key in self._large_fields:
                self._refresh_field(key)

    def _text_changed(self, field_key: str) -> None:
        state = self._large_fields.get(field_key)
        if not state or state["syncing"]:
            return

        widget = state["widget"]
        try:
            if not widget.edit_modified():
                return
        except Exception:
            pass

        value = widget.get("1.0", "end-1c")
        self._set_backing(state, value)

        try:
            widget.edit_modified(False)
        except Exception:
            pass

    def _variable_changed(self, field_key: str) -> None:
        state = self._large_fields.get(field_key)
        if not state or state["syncing"]:
            return

        variable = state.get("variable")
        if variable is None:
            return
        try:
            value = str(variable.get() or "")
        except Exception:
            return
        self._set_large_text(state, value)

    def _flush_field(self, field_key: str) -> None:
        state = self._large_fields.get(field_key)
        if not state:
            return

        raw = state["widget"].get("1.0", "end-1c")
        compact = " ".join(raw.replace("\r", "\n").split())
        self._set_large_text(state, compact)
        self._set_backing(state, compact)

    def _flush_large_fields(self) -> None:
        for key in tuple(self._large_fields):
            self._flush_field(key)

    # ------------------------------------------------------------------
    # Tastatur
    # ------------------------------------------------------------------
    def _select_all(self, widget):
        widget.tag_add("sel", "1.0", "end-1c")
        widget.mark_set("insert", "1.0")
        widget.see("insert")
        return "break"

    def _focus_next(self, widget):
        target = widget.tk_focusNext()
        if target is not None:
            target.focus_set()
        return "break"

    def _focus_previous(self, widget):
        target = widget.tk_focusPrev()
        if target is not None:
            target.focus_set()
        return "break"

    # ------------------------------------------------------------------
    # Diagnose
    # ------------------------------------------------------------------
    def _write_ui_diagnostics(self) -> None:
        path = SCRIPT_DIR / "news_studio_5_17_feldsuche.txt"
        lines = [
            "ZUSTAND News Studio 5.17 – Formularzeilen-Diagnose",
            "",
        ]

        root = self._article_root()
        for widget in self._walk(root):
            try:
                klass = widget.winfo_class()
                text = ""
                if klass in {"TLabel", "Label", "TButton", "Button"}:
                    text = str(widget.cget("text") or "")
                lines.append(
                    f"{klass:12} visible={self._visible(widget)!s:5} "
                    f"manager={widget.winfo_manager():5} text={text!r}"
                )
            except Exception:
                continue

        try:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Lebenszyklus
    # ------------------------------------------------------------------
    def load_selected_article(self, _event=None):
        result = super().load_selected_article(_event)
        if getattr(self, "_large_fields", None):
            self.after_idle(self._refresh_large_fields)
        return result

    def new_article(self):
        result = super().new_article()
        if getattr(self, "_large_fields", None):
            self.after_idle(self._refresh_large_fields)
        return result

    def refresh_all(self):
        result = super().refresh_all()
        if getattr(self, "_large_fields", None):
            self.after_idle(self._refresh_large_fields)
        return result

    def article_payload(self, forced_status=None):
        if getattr(self, "_large_fields", None):
            self._flush_large_fields()
        return super().article_payload(forced_status)


def main() -> None:
    try:
        app = NewsStudio517()
        app.mainloop()
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        log_path = _write_start_error(exc)
        try:
            messagebox.showerror(
                "News Studio 5.17 – Startfehler",
                "Das Studio wurde beim Start wegen eines Fehlers beendet.\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                f"Fehlerbericht:\n{log_path}",
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
