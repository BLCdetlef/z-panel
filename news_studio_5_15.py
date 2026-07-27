#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.15 – größere Textfelder für Titel und Kurzfassung.

Benötigt im selben Ordner:
- news_studio_5_14.py
- news_studio_5_13.py
- die korrigierte news_studio_5_12.py (Version 5.12.1)
- alle bisherigen Basisdateien

Neu:
- Titel als mehrzeiliges Textfeld mit ca. drei sichtbaren Zeilen
- Kurzfassung als mehrzeiliges Textfeld mit ca. acht sichtbaren Zeilen
- automatischer Zeilenumbruch
- Laden, Speichern, Import und Export verwenden weiterhin die bisherigen
  StringVar-Datenfelder und bleiben dadurch kompatibel
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_14.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "news_studio_5_14.py wurde nicht gefunden.\n"
        "Lege News Studio 5.15 in denselben Ordner wie Version 5.14."
    )

spec = importlib.util.spec_from_file_location("news_studio_5_14_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("News Studio 5.14 konnte nicht geladen werden.")

base515 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base515
spec.loader.exec_module(base515)

tk = base515.tk
ttk = base515.ttk


class NewsStudio515(base515.NewsStudio514):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.15")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.14", "ZUSTAND News Studio 5.15"
        )

        self._multiline_fields: dict[str, dict[str, Any]] = {}
        self.after_idle(self._install_multiline_article_fields)

        self.status_var.set(
            "News Studio 5.15 bereit │ Titel und Kurzfassung mehrzeilig bearbeitbar"
        )

    # ---------- Widget-Suche ----------
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
                textvariable = str(widget.cget("textvariable"))
            except Exception:
                continue

            if textvariable == variable_name:
                return widget

        return None

    # ---------- Geometrie ----------
    def _replace_in_geometry(self, original, replacement) -> bool:
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
                children = list(parent.pack_slaves())
                next_widget = None
                if original in children:
                    index = children.index(original)
                    if index + 1 < len(children):
                        next_widget = children[index + 1]

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

    # ---------- Mehrzeilige Felder ----------
    def _install_multiline_article_fields(self) -> None:
        configurations = (
            ("title", 3, "Titel"),
            ("summary", 8, "Kurzfassung"),
        )

        installed = 0
        for field_key, height, accessible_name in configurations:
            if self._install_multiline_field(
                field_key=field_key,
                height=height,
                accessible_name=accessible_name,
            ):
                installed += 1

        if installed == 2:
            self.status_var.set(
                "Titel und Kurzfassung wurden als große Textfelder eingerichtet."
            )
        elif installed == 1:
            self.status_var.set(
                "Ein Textfeld wurde vergrößert; das zweite Feld konnte nicht "
                "eindeutig gefunden werden."
            )
        else:
            self.status_var.set(
                "Titel und Kurzfassung konnten in dieser lokalen Maske nicht "
                "automatisch gefunden werden."
            )

    def _install_multiline_field(
        self,
        field_key: str,
        height: int,
        accessible_name: str,
    ) -> bool:
        if field_key in self._multiline_fields:
            return True

        variable = getattr(self, "article_vars", {}).get(field_key)
        if variable is None:
            return False

        original = self._find_widget_for_variable(variable)
        if original is None:
            return False

        parent = original.master

        text_widget = tk.Text(
            parent,
            height=height,
            width=1,
            wrap="word",
            undo=True,
            maxundo=100,
            autoseparators=True,
            relief="solid",
            borderwidth=1,
            padx=7,
            pady=6,
            spacing1=1,
            spacing3=1,
            font=("Segoe UI", 10),
        )
        text_widget.insert("1.0", str(variable.get() or ""))
        text_widget.edit_modified(False)

        if not self._replace_in_geometry(original, text_widget):
            text_widget.destroy()
            return False

        state = {
            "variable": variable,
            "original": original,
            "widget": text_widget,
            "updating": False,
            "name": accessible_name,
        }
        self._multiline_fields[field_key] = state

        def text_to_variable(_event=None, key=field_key):
            item = self._multiline_fields.get(key)
            if not item or item["updating"]:
                return
            widget = item["widget"]
            try:
                modified = widget.edit_modified()
            except Exception:
                modified = True
            if not modified and _event is None:
                return

            value = widget.get("1.0", "end-1c")
            if str(item["variable"].get() or "") != value:
                item["variable"].set(value)
            try:
                widget.edit_modified(False)
            except Exception:
                pass

        def variable_to_text(*_args, key=field_key):
            item = self._multiline_fields.get(key)
            if not item or item["updating"]:
                return

            widget = item["widget"]
            desired = str(item["variable"].get() or "")
            current = widget.get("1.0", "end-1c")
            if current == desired:
                return

            item["updating"] = True
            try:
                insert_index = widget.index("insert")
                yview = widget.yview()
                widget.delete("1.0", "end")
                widget.insert("1.0", desired)

                try:
                    widget.mark_set("insert", insert_index)
                except Exception:
                    widget.mark_set("insert", "end-1c")

                if yview:
                    widget.yview_moveto(yview[0])
                widget.edit_modified(False)
            finally:
                item["updating"] = False

        text_widget.bind("<<Modified>>", text_to_variable, add="+")
        text_widget.bind(
            "<Control-a>",
            lambda _event, widget=text_widget: self._select_all_text(widget),
        )
        text_widget.bind(
            "<Control-A>",
            lambda _event, widget=text_widget: self._select_all_text(widget),
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

        variable.trace_add("write", variable_to_text)
        return True

    def _select_all_text(self, widget):
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

    def _flush_multiline_fields(self) -> None:
        for item in self._multiline_fields.values():
            widget = item["widget"]
            value = widget.get("1.0", "end-1c")
            if str(item["variable"].get() or "") != value:
                item["variable"].set(value)
            try:
                widget.edit_modified(False)
            except Exception:
                pass

    # ---------- Speichern ----------
    def article_payload(self, forced_status=None):
        self._flush_multiline_fields()
        return super().article_payload(forced_status)


def main() -> None:
    app = NewsStudio515()
    app.mainloop()


if __name__ == "__main__":
    main()
