#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.18 – mehrzeilige FieldRow-Felder.

Diese Version baut direkt auf News Studio 5.14 auf.

Die tatsächliche Beitragsmaske verwendet FieldRow-Frames:
- Label und Entry liegen als direkte Kinder in einem gepackten Frame.
- 5.18 ersetzt gezielt den Entry innerhalb genau dieser FieldRow.
- Es wird nicht mehr nach Grid-Zeilen oder räumlich ähnlichen Widgets gesucht.

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
    path = SCRIPT_DIR / "news_studio_5_18_startfehler.txt"
    content = (
        "ZUSTAND News Studio 5.18 konnte nicht gestartet werden.\n\n"
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
        "Lege News Studio 5.18 in denselben Ordner wie Version 5.14."
    )

try:
    spec = importlib.util.spec_from_file_location(
        "news_studio_5_14_base", BASE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("News Studio 5.14 konnte nicht geladen werden.")

    base518 = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = base518
    spec.loader.exec_module(base518)
except BaseException as exc:
    if isinstance(exc, KeyboardInterrupt):
        raise
    log_path = _write_start_error(exc)
    try:
        messagebox.showerror(
            "News Studio 5.18 – Startfehler",
            "Die Versionskette konnte nicht geladen werden.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            f"Fehlerbericht:\n{log_path}",
        )
    except Exception:
        pass
    raise SystemExit(1) from exc

tk = base518.tk
ttk = base518.ttk


def _normalized(value: object) -> str:
    return " ".join(str(value or "").strip().casefold().split())


class NewsStudio518(base518.NewsStudio514):
    def __init__(self):
        # Die Basisklasse ruft bereits während ihres Aufbaus überschreibbare
        # Methoden auf. Zustände deshalb vor super().__init__ anlegen.
        self._multiline_rows: dict[str, dict[str, Any]] = {}
        self._multiline_installing = False

        super().__init__()
        self.title("ZUSTAND News Studio 5.18")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.14", "ZUSTAND News Studio 5.18"
        )

        self.after_idle(self._install_multiline_rows)
        self.status_var.set(
            "News Studio 5.18 bereit │ große Titel- und Kurzfassungsfelder werden eingerichtet"
        )

    # ------------------------------------------------------------------
    # Tatsächliche FieldRow suchen
    # ------------------------------------------------------------------
    def _walk(self, widget):
        yield widget
        for child in widget.winfo_children():
            yield from self._walk(child)

    def _find_field_row(self, label_text: str):
        """Findet den gepackten FieldRow-Frame anhand seines direkten Labels."""
        wanted = _normalized(label_text)
        root = getattr(self, "article_tab", self)

        matches = []
        for widget in self._walk(root):
            try:
                if widget.winfo_class() not in {"TFrame", "Frame"}:
                    continue
            except Exception:
                continue

            direct_children = widget.winfo_children()
            labels = []
            entries = []

            for child in direct_children:
                try:
                    klass = child.winfo_class()
                    if klass in {"TLabel", "Label"}:
                        labels.append(child)
                    elif klass in {"TEntry", "Entry"}:
                        entries.append(child)
                except Exception:
                    continue

            if not entries:
                continue

            matching_labels = []
            for label in labels:
                try:
                    if _normalized(label.cget("text")) == wanted:
                        matching_labels.append(label)
                except Exception:
                    continue

            if not matching_labels:
                continue

            # FieldRow selbst ist gepackt und enthält Label + Entry direkt.
            score = 0
            try:
                if widget.winfo_manager() == "pack":
                    score += 10
                if entries[0].winfo_manager() == "pack":
                    score += 10
                if widget.winfo_viewable():
                    score += 5
                score += widget.winfo_rootx() / 100000
            except Exception:
                pass

            matches.append((score, widget, matching_labels[0], entries[0]))

        if not matches:
            return None

        matches.sort(key=lambda item: item[0], reverse=True)
        _score, row, label, entry = matches[0]
        return row, label, entry

    # ------------------------------------------------------------------
    # Installation
    # ------------------------------------------------------------------
    def _install_multiline_rows(self) -> None:
        if self._multiline_installing or self._multiline_rows:
            return

        self._multiline_installing = True
        try:
            title_ok = self._replace_field_entry(
                field_key="title",
                label_text="Titel",
                height=2,
            )
            summary_ok = self._replace_field_entry(
                field_key="summary",
                label_text="Kurzfassung",
                height=10,
            )
        finally:
            self._multiline_installing = False

        self.after_idle(self._sync_all_from_variables)

        if title_ok and summary_ok:
            self.status_var.set(
                "Titel zweizeilig und Kurzfassung zehnzeilig eingerichtet."
            )
        elif title_ok:
            self.status_var.set(
                "Titel wurde vergrößert; die FieldRow der Kurzfassung wurde nicht gefunden."
            )
        elif summary_ok:
            self.status_var.set(
                "Kurzfassung wurde vergrößert; die FieldRow des Titels wurde nicht gefunden."
            )
        else:
            self.status_var.set(
                "Die FieldRows für Titel und Kurzfassung wurden nicht gefunden."
            )
            self._write_fieldrow_diagnostics()

    def _replace_field_entry(
        self,
        field_key: str,
        label_text: str,
        height: int,
    ) -> bool:
        found = self._find_field_row(label_text)
        if found is None:
            return False

        row, label, original_entry = found
        variable = getattr(self, "article_vars", {}).get(field_key)
        if variable is None:
            return False

        # Den originalen Entry nur ausblenden. Er bleibt als Kompatibilitäts-
        # schnittstelle erhalten und wird weiterhin über dieselbe StringVar gespeist.
        try:
            original_entry.pack_forget()
        except Exception:
            return False

        text_widget = tk.Text(
            row,
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
        text_widget.pack(side="left", fill="x", expand=True)

        # Das Label soll bei hohen Textfeldern oben stehen.
        try:
            label.pack_configure(anchor="n")
        except Exception:
            pass

        state = {
            "field": field_key,
            "row": row,
            "label": label,
            "original": original_entry,
            "widget": text_widget,
            "variable": variable,
            "syncing": False,
        }
        self._multiline_rows[field_key] = state

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
            # Titel bleibt ein kompakter Datensatz ohne Absatzwechsel.
            text_widget.bind(
                "<Return>",
                lambda _event, widget=text_widget: self._focus_next(widget),
            )

        variable.trace_add(
            "write",
            lambda *_args, key=field_key: self._variable_changed(key),
        )

        try:
            row.update_idletasks()
            self.update_idletasks()
        except Exception:
            pass

        return True

    # ------------------------------------------------------------------
    # Synchronisierung
    # ------------------------------------------------------------------
    def _set_text(self, state: dict[str, Any], value: str) -> None:
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

    def _sync_from_variable(self, field_key: str) -> None:
        state = self._multiline_rows.get(field_key)
        if not state or state["syncing"]:
            return

        try:
            value = str(state["variable"].get() or "")
        except Exception:
            value = ""

        self._set_text(state, value)

    def _sync_all_from_variables(self) -> None:
        for field_key in ("title", "summary"):
            if field_key in self._multiline_rows:
                self._sync_from_variable(field_key)

    def _variable_changed(self, field_key: str) -> None:
        self._sync_from_variable(field_key)

    def _text_changed(self, field_key: str) -> None:
        state = self._multiline_rows.get(field_key)
        if not state or state["syncing"]:
            return

        widget = state["widget"]
        try:
            if not widget.edit_modified():
                return
        except Exception:
            pass

        value = widget.get("1.0", "end-1c")
        state["syncing"] = True
        try:
            if str(state["variable"].get() or "") != value:
                state["variable"].set(value)
            widget.edit_modified(False)
        finally:
            state["syncing"] = False

    def _flush_field(self, field_key: str) -> None:
        state = self._multiline_rows.get(field_key)
        if not state:
            return

        raw = state["widget"].get("1.0", "end-1c")
        compact = " ".join(raw.replace("\r", "\n").split())

        state["syncing"] = True
        try:
            if str(state["variable"].get() or "") != compact:
                state["variable"].set(compact)
            self._set_text(state, compact)
        finally:
            state["syncing"] = False

    def _flush_all(self) -> None:
        for field_key in tuple(self._multiline_rows):
            self._flush_field(field_key)

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
    def _write_fieldrow_diagnostics(self) -> None:
        path = SCRIPT_DIR / "news_studio_5_18_fieldrows.txt"
        lines = [
            "ZUSTAND News Studio 5.18 – FieldRow-Diagnose",
            "",
        ]
        root = getattr(self, "article_tab", self)

        for widget in self._walk(root):
            try:
                if widget.winfo_class() not in {"TFrame", "Frame"}:
                    continue
                children = widget.winfo_children()
                child_data = []
                for child in children:
                    klass = child.winfo_class()
                    text = ""
                    if klass in {"TLabel", "Label"}:
                        text = str(child.cget("text") or "")
                    child_data.append(f"{klass}:{text!r}")
                if child_data:
                    lines.append(
                        f"manager={widget.winfo_manager()} "
                        f"children={', '.join(child_data)}"
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
        if getattr(self, "_multiline_rows", None):
            self.after_idle(self._sync_all_from_variables)
        return result

    def new_article(self):
        result = super().new_article()
        if getattr(self, "_multiline_rows", None):
            self.after_idle(self._sync_all_from_variables)
        return result

    def refresh_all(self):
        result = super().refresh_all()
        if getattr(self, "_multiline_rows", None):
            self.after_idle(self._sync_all_from_variables)
        return result

    def article_payload(self, forced_status=None):
        if getattr(self, "_multiline_rows", None):
            self._flush_all()
        return super().article_payload(forced_status)


def main() -> None:
    try:
        app = NewsStudio518()
        app.mainloop()
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        log_path = _write_start_error(exc)
        try:
            messagebox.showerror(
                "News Studio 5.18 – Startfehler",
                "Das Studio wurde wegen eines Fehlers beendet.\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                f"Fehlerbericht:\n{log_path}",
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
