#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.16.1 – startkorrigierte mehrzeilige Beitragsfelder.

Wichtig:
Diese Version baut bewusst direkt auf News Studio 5.14 auf und umgeht die
fehlerhafte Feldersetzung aus Version 5.15.

Benötigt im selben Ordner:
- news_studio_5_14.py
- news_studio_5_13.py
- die korrigierte news_studio_5_12.py (Version 5.12.1)
- alle bisherigen Basisdateien

Korrektur gegenüber 5.16:
- interne Feldzustände werden vor dem Aufruf der Basisklasse angelegt
- geerbte Startaufrufe von refresh_all/new_article sind dadurch sicher
- Startfehler werden in news_studio_5_16_startfehler.txt protokolliert

Neu:
- Titel: zweizeiliges, automatisch umbrechendes Textfeld
- Kurzfassung: sechszeiliges, automatisch umbrechendes Textfeld
- zuverlässige Übernahme aus der aktuell geladenen Artikeldatei
- Synchronisierung mit den bisherigen Eingabefeldern und StringVars
- bestehende Import-, Speicher- und Exportlogik bleibt erhalten
"""

import importlib.util
import sys
import traceback
from pathlib import Path
from tkinter import messagebox
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_14.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_14.py wurde nicht gefunden.\n"
        "Lege News Studio 5.16 in denselben Ordner wie Version 5.14."
    )

def _write_start_error(exc: BaseException) -> Path:
    log_path = SCRIPT_DIR / "news_studio_5_16_startfehler.txt"
    details = (
        "ZUSTAND News Studio 5.16.1 konnte nicht gestartet werden.\n\n"
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
        "news_studio_5_14_base", BASE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("News Studio 5.14 konnte nicht geladen werden.")

    base516 = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = base516
    spec.loader.exec_module(base516)
except BaseException as exc:
    if isinstance(exc, KeyboardInterrupt):
        raise
    log_path = _write_start_error(exc)
    try:
        messagebox.showerror(
            "News Studio 5.16.1 – Startfehler",
            "Die Versionskette konnte nicht geladen werden.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            f"Fehlerbericht:\n{log_path}",
        )
    except Exception:
        pass
    raise SystemExit(1) from exc

tk = base516.tk
ttk = base516.ttk
read_json_object = base516.read_json_object


def _normalized_label(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


class NewsStudio516(base516.NewsStudio514):
    def __init__(self):
        # WICHTIG: Die Basisklasse ruft während ihres Aufbaus bereits Methoden
        # wie refresh_all() oder new_article() auf. Wegen dynamischer Bindung
        # landen diese Aufrufe schon in den Überschreibungen dieser Klasse.
        # Deshalb müssen die dort verwendeten Zustände vor super().__init__()
        # existieren.
        self._large_article_fields: dict[str, dict[str, Any]] = {}
        self._large_fields_installing = False

        super().__init__()
        self.title("ZUSTAND News Studio 5.16.1")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.14", "ZUSTAND News Studio 5.16.1"
        )

        # Erst nach dem vollständigen Aufbau der geerbten Maske ersetzen.
        self.after_idle(self._install_large_article_fields)

        self.status_var.set(
            "News Studio 5.16 bereit │ Titel und Kurzfassung werden vergrößert"
        )

    # ---------- Widgetsuche ----------
    def _walk_widgets(self, widget):
        yield widget
        for child in widget.winfo_children():
            yield from self._walk_widgets(child)

    def _find_widget_for_variable(self, variable):
        variable_name = str(variable)

        for widget in self._walk_widgets(self):
            try:
                widget_class = widget.winfo_class()
            except Exception:
                continue

            if widget_class not in {
                "TEntry",
                "Entry",
                "TCombobox",
                "Combobox",
            }:
                continue

            try:
                if str(widget.cget("textvariable")) == variable_name:
                    return widget
            except Exception:
                continue

        return None

    def _find_input_next_to_label(self, label_text: str):
        wanted = _normalized_label(label_text)

        for label in self._walk_widgets(self):
            try:
                if label.winfo_class() not in {"TLabel", "Label"}:
                    continue
                if _normalized_label(label.cget("text")) != wanted:
                    continue
            except Exception:
                continue

            parent = label.master
            try:
                manager = label.winfo_manager()
            except Exception:
                manager = ""

            if manager == "grid":
                try:
                    label_info = label.grid_info()
                    label_row = int(label_info.get("row", 0))
                    label_column = int(label_info.get("column", 0))
                except Exception:
                    continue

                candidates = []
                for child in parent.winfo_children():
                    try:
                        if child.winfo_manager() != "grid":
                            continue
                        info = child.grid_info()
                        if int(info.get("row", -1)) != label_row:
                            continue
                        column = int(info.get("column", -1))
                        if column <= label_column:
                            continue
                        if child.winfo_class() not in {
                            "TEntry",
                            "Entry",
                            "TCombobox",
                            "Combobox",
                        }:
                            continue
                        candidates.append((column, child))
                    except Exception:
                        continue

                if candidates:
                    candidates.sort(key=lambda item: item[0])
                    return candidates[0][1]

            elif manager == "pack":
                try:
                    children = list(parent.pack_slaves())
                    index = children.index(label)
                except Exception:
                    continue

                for child in children[index + 1:]:
                    try:
                        if child.winfo_class() in {
                            "TEntry",
                            "Entry",
                            "TCombobox",
                            "Combobox",
                        }:
                            return child
                    except Exception:
                        continue

        return None

    # ---------- Geometrie ----------
    def _place_replacement(self, original, replacement) -> bool:
        try:
            manager = original.winfo_manager()
        except Exception:
            manager = ""

        if manager == "grid":
            try:
                info = dict(original.grid_info())
                info.pop("in", None)
                original.grid_remove()
                replacement.grid(**info)
                return True
            except Exception:
                return False

        if manager == "pack":
            try:
                parent = original.master
                packed = list(parent.pack_slaves())
                next_widget = None
                if original in packed:
                    index = packed.index(original)
                    if index + 1 < len(packed):
                        next_widget = packed[index + 1]

                info = dict(original.pack_info())
                info.pop("in", None)
                original.pack_forget()
                if next_widget is not None:
                    info["before"] = next_widget
                replacement.pack(**info)
                return True
            except Exception:
                return False

        if manager == "place":
            try:
                info = dict(original.place_info())
                info.pop("in", None)
                original.place_forget()
                replacement.place(**info)
                return True
            except Exception:
                return False

        return False

    # ---------- Installation ----------
    def _install_large_article_fields(self) -> None:
        if self._large_fields_installing or self._large_article_fields:
            return

        self._large_fields_installing = True
        try:
            title_ok = self._install_large_field(
                field_key="title",
                label_text="Titel",
                height=2,
            )
            summary_ok = self._install_large_field(
                field_key="summary",
                label_text="Kurzfassung",
                height=6,
            )
        finally:
            self._large_fields_installing = False

        self.after_idle(self._refresh_large_fields)

        if title_ok and summary_ok:
            self.status_var.set(
                "Titel zweizeilig und Kurzfassung sechszeilig eingerichtet."
            )
        elif title_ok:
            self.status_var.set(
                "Titel wurde vergrößert; Kurzfassung konnte nicht gefunden werden."
            )
        elif summary_ok:
            self.status_var.set(
                "Kurzfassung wurde vergrößert; Titel konnte nicht gefunden werden."
            )
        else:
            self.status_var.set(
                "Titel und Kurzfassung konnten nicht eindeutig gefunden werden."
            )

    def _install_large_field(
        self,
        field_key: str,
        label_text: str,
        height: int,
    ) -> bool:
        variable = getattr(self, "article_vars", {}).get(field_key)

        original = None
        if variable is not None:
            original = self._find_widget_for_variable(variable)

        if original is None:
            original = self._find_input_next_to_label(label_text)

        if original is None:
            return False

        text_widget = tk.Text(
            original.master,
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
            pady=5,
            spacing1=1,
            spacing3=1,
            font=("Segoe UI", 10),
            takefocus=True,
        )

        if not self._place_replacement(original, text_widget):
            text_widget.destroy()
            return False

        state = {
            "field": field_key,
            "variable": variable,
            "original": original,
            "widget": text_widget,
            "syncing": False,
            "trace_id": None,
        }
        self._large_article_fields[field_key] = state

        text_widget.bind(
            "<<Modified>>",
            lambda _event, key=field_key: self._text_changed(key),
            add="+",
        )
        text_widget.bind(
            "<FocusOut>",
            lambda _event, key=field_key: self._flush_large_field(key),
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
            # Visuell mehrzeilig, inhaltlich weiterhin ein Titel ohne Absatzwechsel.
            text_widget.bind(
                "<Return>",
                lambda _event, widget=text_widget: self._focus_next(widget),
            )

        if variable is not None:
            try:
                trace_id = variable.trace_add(
                    "write",
                    lambda *_args, key=field_key: self._variable_changed(key),
                )
                state["trace_id"] = trace_id
            except Exception:
                pass

        return True

    # ---------- Datenquellen ----------
    def _current_article_data(self) -> dict[str, Any] | None:
        path = getattr(self, "current_article_path", None)
        if not path:
            return None
        try:
            return read_json_object(Path(path))
        except Exception:
            return None

    def _original_value(self, state: dict[str, Any]) -> str:
        original = state["original"]
        try:
            return str(original.get() or "")
        except Exception:
            return ""

    def _authoritative_value(self, field_key: str) -> str:
        state = self._large_article_fields[field_key]

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

        return self._original_value(state)

    # ---------- Synchronisierung ----------
    def _clean_value(self, field_key: str, value: str) -> str:
        value = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
        if field_key in {"title", "summary"}:
            # Beide Felder bleiben im Datensatz kompakte Textwerte.
            return " ".join(value.split())
        return value.strip()

    def _set_text_widget(self, state: dict[str, Any], value: str) -> None:
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

    def _set_backing_sources(
        self,
        state: dict[str, Any],
        value: str,
    ) -> None:
        state["syncing"] = True
        try:
            variable = state.get("variable")
            if variable is not None:
                try:
                    if str(variable.get() or "") != value:
                        variable.set(value)
                except Exception:
                    pass

            original = state["original"]
            try:
                current = str(original.get() or "")
            except Exception:
                current = None

            if current is not None and current != value:
                try:
                    original.delete(0, "end")
                    original.insert(0, value)
                except Exception:
                    pass
        finally:
            state["syncing"] = False

    def _refresh_large_field(self, field_key: str) -> None:
        state = self._large_article_fields.get(field_key)
        if not state or state["syncing"]:
            return

        value = self._authoritative_value(field_key)
        self._set_text_widget(state, value)
        self._set_backing_sources(state, value)

    def _refresh_large_fields(self) -> None:
        for field_key in ("title", "summary"):
            if field_key in self._large_article_fields:
                self._refresh_large_field(field_key)

    def _text_changed(self, field_key: str) -> None:
        state = self._large_article_fields.get(field_key)
        if not state or state["syncing"]:
            return

        widget = state["widget"]
        try:
            if not widget.edit_modified():
                return
        except Exception:
            pass

        # Während des Tippens nicht unnötig normalisieren; nur Datenquelle spiegeln.
        value = widget.get("1.0", "end-1c")
        self._set_backing_sources(state, value)

        try:
            widget.edit_modified(False)
        except Exception:
            pass

    def _variable_changed(self, field_key: str) -> None:
        state = self._large_article_fields.get(field_key)
        if not state or state["syncing"]:
            return

        variable = state.get("variable")
        if variable is None:
            return

        try:
            value = str(variable.get() or "")
        except Exception:
            return

        self._set_text_widget(state, value)

    def _flush_large_field(self, field_key: str) -> None:
        state = self._large_article_fields.get(field_key)
        if not state:
            return

        raw_value = state["widget"].get("1.0", "end-1c")
        value = self._clean_value(field_key, raw_value)
        self._set_text_widget(state, value)
        self._set_backing_sources(state, value)

    def _flush_large_fields(self) -> None:
        for field_key in tuple(self._large_article_fields):
            self._flush_large_field(field_key)

    # ---------- Tastatur ----------
    def _select_all(self, widget):
        widget.tag_add("sel", "1.0", "end-1c")
        widget.mark_set("insert", "1.0")
        widget.see("insert")
        return "break"

    def _focus_next(self, widget):
        next_widget = widget.tk_focusNext()
        if next_widget is not None:
            next_widget.focus_set()
        return "break"

    def _focus_previous(self, widget):
        previous_widget = widget.tk_focusPrev()
        if previous_widget is not None:
            previous_widget.focus_set()
        return "break"

    # ---------- Lebenszyklus ----------
    def load_selected_article(self, _event=None):
        result = super().load_selected_article(_event)
        if getattr(self, "_large_article_fields", None):
            self.after_idle(self._refresh_large_fields)
        return result

    def new_article(self):
        result = super().new_article()
        if getattr(self, "_large_article_fields", None):
            self.after_idle(self._refresh_large_fields)
        return result

    def refresh_all(self):
        result = super().refresh_all()
        if getattr(self, "_large_article_fields", None):
            self.after_idle(self._refresh_large_fields)
        return result

    def article_payload(self, forced_status=None):
        if getattr(self, "_large_article_fields", None):
            self._flush_large_fields()
        return super().article_payload(forced_status)


def main() -> None:
    try:
        app = NewsStudio516()
        app.mainloop()
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        log_path = _write_start_error(exc)
        try:
            messagebox.showerror(
                "News Studio 5.16.1 – Startfehler",
                "Das Studio wurde beim Start wegen eines Fehlers beendet.\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                f"Fehlerbericht:\n{log_path}",
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
