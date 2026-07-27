#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.19.1 – Windows-Startkorrektur.

Diese Version baut direkt auf News Studio 5.14 auf.

Der entscheidende Unterschied zu 5.15–5.18:
Die sichtbaren Widgets werden nicht mehr nachträglich gesucht oder ersetzt.
Stattdessen wird die ursprüngliche FieldRow-Klasse in der geladenen
Versionskette vor dem Aufbau des Fensters angepasst.

Dadurch entstehen von Anfang an:
- Titel: mehrzeiliges Textfeld, 2 sichtbare Zeilen
- Kurzfassung: mehrzeiliges Textfeld, 10 sichtbare Zeilen
"""

import importlib.util
import sys
import traceback
import types
from pathlib import Path
from tkinter import messagebox

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_14.py"


def _write_start_error(exc: BaseException) -> Path:
    path = SCRIPT_DIR / "news_studio_5_19_1_startfehler.txt"
    content = (
        "ZUSTAND News Studio 5.19.1 konnte nicht gestartet werden.\n\n"
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
        "Lege News Studio 5.19 in denselben Ordner wie Version 5.14."
    )

try:
    spec = importlib.util.spec_from_file_location(
        "news_studio_5_14_base", BASE_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("News Studio 5.14 konnte nicht geladen werden.")

    base519 = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = base519
    spec.loader.exec_module(base519)
except BaseException as exc:
    if isinstance(exc, KeyboardInterrupt):
        raise
    log_path = _write_start_error(exc)
    try:
        messagebox.showerror(
            "News Studio 5.19.1 – Startfehler",
            "Die Versionskette konnte nicht geladen werden.\n\n"
            f"{type(exc).__name__}: {exc}\n\n"
            f"Fehlerbericht:\n{log_path}",
        )
    except Exception:
        pass
    raise SystemExit(1) from exc

tk = base519.tk
ttk = base519.ttk


class BoundText(tk.Text):
    """Mehrzeiliges Textfeld mit bidirektionaler StringVar-Anbindung."""

    def __init__(
        self,
        parent,
        *,
        variable=None,
        height: int,
        compact_on_focus_out: bool = True,
        **kwargs,
    ):
        super().__init__(
            parent,
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
            **kwargs,
        )
        self._variable = variable
        self._syncing = False
        self._compact_on_focus_out = compact_on_focus_out

        if variable is not None:
            self.insert("1.0", str(variable.get() or ""))
            variable.trace_add("write", self._variable_changed)

        self.edit_modified(False)
        self.bind("<<Modified>>", self._text_changed, add="+")
        self.bind("<FocusOut>", self._focus_out, add="+")
        self.bind("<Control-a>", self._select_all, add="+")
        self.bind("<Control-A>", self._select_all, add="+")
        self.bind("<Tab>", self._focus_next, add="+")
        self.bind("<Shift-Tab>", self._focus_previous, add="+")

        # ISO_Left_Tab existiert nur auf X11/Linux. Unter Windows löst bereits
        # das Registrieren dieses Ereignisses einen TclError aus.
        try:
            if str(self.tk.call("tk", "windowingsystem")) == "x11":
                self.bind("<ISO_Left_Tab>", self._focus_previous, add="+")
        except tk.TclError:
            pass

    def _select_all(self, _event=None):
        self.tag_add("sel", "1.0", "end-1c")
        self.mark_set("insert", "1.0")
        self.see("insert")
        return "break"

    def _focus_next(self, _event=None):
        target = self.tk_focusNext()
        if target is not None:
            target.focus_set()
        return "break"

    def _focus_previous(self, _event=None):
        target = self.tk_focusPrev()
        if target is not None:
            target.focus_set()
        return "break"

    def _variable_changed(self, *_args):
        if self._syncing or self._variable is None:
            return
        desired = str(self._variable.get() or "")
        current = self.get("1.0", "end-1c")
        if current == desired:
            return

        self._syncing = True
        try:
            self.delete("1.0", "end")
            self.insert("1.0", desired)
            self.edit_modified(False)
        finally:
            self._syncing = False

    def _text_changed(self, _event=None):
        if self._syncing:
            return
        try:
            if not self.edit_modified():
                return
        except Exception:
            pass

        if self._variable is not None:
            value = self.get("1.0", "end-1c")
            self._syncing = True
            try:
                if str(self._variable.get() or "") != value:
                    self._variable.set(value)
            finally:
                self._syncing = False

        try:
            self.edit_modified(False)
        except Exception:
            pass

    def _focus_out(self, _event=None):
        if not self._compact_on_focus_out:
            return
        raw = self.get("1.0", "end-1c")
        compact = " ".join(raw.replace("\r", "\n").split())
        if raw == compact:
            return

        self._syncing = True
        try:
            self.delete("1.0", "end")
            self.insert("1.0", compact)
            if self._variable is not None:
                self._variable.set(compact)
            self.edit_modified(False)
        finally:
            self._syncing = False


class AdaptiveFieldRow(ttk.Frame):
    """Originale FieldRow mit gezielten mehrzeiligen Ausnahmen."""

    def __init__(self, parent, label, variable=None, width=60):
        super().__init__(parent)
        ttk.Label(self, text=label, width=20).pack(
            side="left",
            anchor="n",
        )

        normalized = " ".join(str(label or "").strip().casefold().split())

        if normalized == "titel":
            self.entry = BoundText(
                self,
                variable=variable,
                height=2,
            )
        elif normalized == "kurzfassung":
            self.entry = BoundText(
                self,
                variable=variable,
                height=10,
            )
        else:
            self.entry = ttk.Entry(
                self,
                textvariable=variable,
                width=width,
            )

        self.entry.pack(side="left", fill="x", expand=True)
        self.pack(fill="x", pady=3)

        # Kompatibilität mit älteren Funktionen, die summary_text erwarten.
        try:
            root = self.winfo_toplevel()
            if normalized == "kurzfassung":
                root.summary_text = self.entry
            elif normalized == "titel":
                root.title_text = self.entry
        except Exception:
            pass


def _iter_news_modules(root_module):
    """Durchläuft die verschachtelte Versionskette ohne Endlosschleifen."""
    seen: set[int] = set()
    stack = [root_module]

    while stack:
        module = stack.pop()
        if not isinstance(module, types.ModuleType):
            continue
        identity = id(module)
        if identity in seen:
            continue
        seen.add(identity)
        yield module

        for value in vars(module).values():
            if not isinstance(value, types.ModuleType):
                continue
            name = str(getattr(value, "__name__", ""))
            if (
                name.startswith("news_studio")
                or name.endswith("_base")
                or "news_studio" in name
            ):
                stack.append(value)


def _patch_fieldrow_chain() -> list[str]:
    """Ersetzt FieldRow vor der Erzeugung der GUI in allen Basismodulen."""
    patched: list[str] = []

    for module in _iter_news_modules(base519):
        existing = getattr(module, "FieldRow", None)
        if not isinstance(existing, type):
            continue
        setattr(module, "FieldRow", AdaptiveFieldRow)
        patched.append(str(getattr(module, "__name__", "unbekannt")))

    if not patched:
        raise RuntimeError(
            "In der geladenen Versionskette wurde keine FieldRow-Klasse gefunden."
        )

    return patched


PATCHED_FIELDROW_MODULES = _patch_fieldrow_chain()


class NewsStudio519(base519.NewsStudio514):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.19.1")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.14",
            "ZUSTAND News Studio 5.19.1",
        )
        self.status_var.set(
            "News Studio 5.19.1 bereit │ Titel 2-zeilig, Kurzfassung 10-zeilig"
        )


def main() -> None:
    try:
        app = NewsStudio519()
        app.mainloop()
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        log_path = _write_start_error(exc)
        try:
            messagebox.showerror(
                "News Studio 5.19.1 – Startfehler",
                "Das Studio wurde wegen eines Fehlers beendet.\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                f"Fehlerbericht:\n{log_path}",
            )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
