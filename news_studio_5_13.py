#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.13 – ein gemeinsamer sicherer Löschen-Button.

Benötigt im selben Ordner:
- die korrigierte news_studio_5_12.py (Version 5.12.1)
- news_studio_5_11.py und die bisherigen Basisdateien

Neu:
- alter und neuer Löschen-Button werden zu einem Button zusammengeführt
- der verbleibende Button verwendet immer die sichere Löschlogik
- bei Grundlagen: News-Verknüpfungen werden nach Bestätigung entfernt
- bei News: nur der ausgewählte Beitrag wird gelöscht
- verwaiste explainerId-Verknüpfungen werden beim Start bereinigt
"""

import importlib.util
import sys
from pathlib import Path
from tkinter import messagebox
from typing import Any, Iterator

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_SCRIPT = SCRIPT_DIR / "news_studio_5_12.py"

if not BASE_SCRIPT.exists():
    raise SystemExit(
        "Die korrigierte news_studio_5_12.py wurde nicht gefunden.\n"
        "Lege News Studio 5.13 in denselben Ordner wie Version 5.12.1."
    )

spec = importlib.util.spec_from_file_location("news_studio_5_12_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("News Studio 5.12.1 konnte nicht geladen werden.")

base513 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base513
spec.loader.exec_module(base513)

tk = base513.tk
ttk = base513.ttk

cleanup_dangling_explainer_links = base513.cleanup_dangling_explainer_links


def _walk_widgets(widget) -> Iterator[Any]:
    yield widget
    for child in widget.winfo_children():
        yield from _walk_widgets(child)


def _normalized_button_text(widget) -> str:
    try:
        return " ".join(str(widget.cget("text") or "").strip().lower().split())
    except Exception:
        return ""


def _forget_widget(widget) -> None:
    """Entfernt ein Widget unabhängig vom verwendeten Geometriemanager."""
    try:
        manager = widget.winfo_manager()
    except Exception:
        manager = ""

    try:
        if manager == "pack":
            widget.pack_forget()
        elif manager == "grid":
            widget.grid_remove()
        elif manager == "place":
            widget.place_forget()
        else:
            widget.destroy()
    except Exception:
        try:
            widget.destroy()
        except Exception:
            pass


class NewsStudio513(base513.NewsStudio512):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.13")
        self._replace_widget_text(
            "ZUSTAND News Studio 5.12.1", "ZUSTAND News Studio 5.13"
        )

        unified = self._unify_delete_buttons()
        cleanup = self._cleanup_after_accidental_deletion()

        if cleanup["changed"] > 0:
            self.status_var.set(
                f'News Studio 5.13 bereit │ {cleanup["changed"]} verwaiste '
                "Grundlagen-Verknüpfungen bereinigt"
            )
        elif unified:
            self.status_var.set(
                "News Studio 5.13 bereit │ ein sicherer Löschen-Button"
            )
        else:
            self.status_var.set(
                "News Studio 5.13 bereit │ sichere Löschlogik aktiv"
            )

    # ---------- Button-Zusammenführung ----------
    def _article_tab_root(self):
        """Ermittelt den gesamten Reiter, in dem das Beitragsformular liegt."""
        widget = self._article_form_parent()
        last = widget

        while widget is not None:
            try:
                parent = widget.master
            except Exception:
                break
            if parent is None:
                break
            try:
                if parent.winfo_class() == "TNotebook":
                    return widget
            except Exception:
                pass
            last = widget
            widget = parent

        return last

    def _is_article_delete_button(self, widget) -> bool:
        try:
            if widget.winfo_class() not in {"TButton", "Button"}:
                return False
        except Exception:
            return False

        text = _normalized_button_text(widget)
        if "lösch" not in text and "delete" not in text:
            return False

        # Keine Löschknöpfe für Unterobjekte wie Bilder, Quellen oder Kontakte umbinden.
        exclusions = (
            "bild",
            "quelle",
            "kontakt",
            "anhang",
            "datei",
            "label",
            "notiz",
        )
        if any(word in text for word in exclusions):
            return False

        return (
            text in {"löschen", "delete"}
            or "beitrag" in text
            or "artikel" in text
            or "entwurf" in text
            or "aktuellen" in text
            or "grundlagen-kaskade" in text
            or "kaskade" in text
        )

    def _find_cascade_frame(self):
        root = self._article_tab_root()
        for widget in _walk_widgets(root):
            try:
                if (
                    widget.winfo_class() == "TLabelframe"
                    and str(widget.cget("text") or "").strip()
                    == "Löschen und Verknüpfungen"
                ):
                    return widget
            except Exception:
                continue
        return None

    def _unify_delete_buttons(self) -> bool:
        """Lässt im Beitragsreiter genau einen sicheren Löschen-Button übrig."""
        root = self._article_tab_root()
        buttons = [
            widget
            for widget in _walk_widgets(root)
            if self._is_article_delete_button(widget)
        ]

        # Den früheren Standardbutton bevorzugen, nicht den zusätzlich angelegten
        # Kaskadenbutton im separaten Hinweisfeld.
        standard_buttons = [
            button
            for button in buttons
            if "kaskade" not in _normalized_button_text(button)
        ]
        primary = standard_buttons[0] if standard_buttons else (buttons[0] if buttons else None)

        if primary is None:
            # Sicherheitsfallback: Der 5.12-Hinweisblock bleibt sichtbar und dessen
            # vorhandener Button wird weiter benutzt.
            return False

        try:
            primary.configure(
                text="Beitrag löschen",
                command=self.delete_current_article_with_cascade,
            )
        except Exception:
            return False

        # Weitere Artikel-Löschen-Buttons ausblenden.
        for button in buttons:
            if button is primary:
                continue
            _forget_widget(button)

        # Das zusätzliche Kaskaden-Hinweisfeld entfernen, weil der normale Button
        # nun dieselbe sichere Logik verwendet.
        cascade_frame = self._find_cascade_frame()
        if cascade_frame is not None:
            try:
                if primary not in list(_walk_widgets(cascade_frame)):
                    _forget_widget(cascade_frame)
            except Exception:
                _forget_widget(cascade_frame)

        return True

    # ---------- Bereinigung versehentlich gelöschter Grundlagen ----------
    def _cleanup_after_accidental_deletion(self) -> dict[str, Any]:
        try:
            result = cleanup_dangling_explainer_links()
        except Exception as exc:
            messagebox.showwarning(
                "Verknüpfungen konnten nicht geprüft werden",
                "Das Studio wurde gestartet, aber alte Grundlagen-Verknüpfungen "
                f"konnten nicht automatisch geprüft werden.\n\n"
                f"{type(exc).__name__}: {exc}",
                parent=self,
            )
            return {"changed": 0, "details": []}

        if result.get("changed", 0) > 0:
            details = result.get("details", [])
            preview = "\n".join(f"• {item}" for item in details[:8])
            if len(details) > 8:
                preview += "\n• …"

            messagebox.showinfo(
                "Alte Verknüpfungen bereinigt",
                f'{result["changed"]} News-Verknüpfungen zeigten auf bereits '
                "gelöschte Grundlagen und wurden entfernt.\n\n"
                f"{preview}\n\n"
                "Bitte news.json anschließend neu erzeugen.",
                parent=self,
            )
            try:
                super().refresh_all()
            except Exception:
                pass

        return result


def main() -> None:
    app = NewsStudio513()
    app.mainloop()


if __name__ == "__main__":
    main()
