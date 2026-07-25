#!/usr/bin/env python3
from __future__ import annotations

"""
ZUSTAND News Studio 5.3 – Kontaktaufnahme und Interview-Assistent

Erweitert News Studio 5.2.1 um:
- personalisierte erste Interviewanfrage
- freundliche Erinnerung
- Telefonleitfaden
- Intervieweinladung nach Vorgespräch
- editierbare Vorschau, Kopieren und Öffnen im Standard-Mailprogramm

Installation:
Diese Datei neben news_studio_5_2_1.py, news_studio_5_1.py und die bisherigen
Studio-Dateien in den Z-PANEL-Projektordner legen und künftig diese Datei starten.
"""

import importlib.util
import sys
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BASE_CANDIDATES = (
    SCRIPT_DIR / "news_studio_5_2_1.py",
    SCRIPT_DIR / "news_studio_5_2_1(1).py",
    SCRIPT_DIR / "news_studio_5_2.py",
)
BASE_SCRIPT = next((path for path in BASE_CANDIDATES if path.exists()), None)

if BASE_SCRIPT is None:
    raise SystemExit(
        "news_studio_5_2_1.py wurde nicht gefunden.\n"
        "Lege News Studio 5.3 in denselben Ordner wie Version 5.2.1."
    )

spec = importlib.util.spec_from_file_location("news_studio_5_2_1_base", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise SystemExit("News Studio 5.2.1 konnte nicht geladen werden.")

base52 = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = base52
spec.loader.exec_module(base52)

tk = base52.tk
ttk = base52.ttk
messagebox = base52.messagebox
clean_text = base52.clean_text
write_contact_db = base52.write_contact_db


def greeting_for(contact: dict[str, Any]) -> str:
    """Erzeugt eine vorsichtige Anrede, ohne Geschlecht oder Titel zu erraten."""
    name = clean_text(contact.get("name"))
    if not name:
        return "Guten Tag,"
    return f"Guten Tag {name},"


def linked_articles(db: dict[str, Any], contact_id: str) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for source_key, link in db.get("articleLinks", {}).items():
        if not isinstance(link, dict):
            continue
        ids = link.get("contactIds", [])
        if not isinstance(ids, list) or contact_id not in ids:
            continue
        result.append({
            "key": source_key,
            "title": clean_text(link.get("title")) or "Meldung ohne Titel",
            "sourceUrl": clean_text(link.get("sourceUrl")),
        })
    result.sort(key=lambda item: item["title"].lower())
    return result


class NewsStudio53(base52.NewsStudio52):
    def __init__(self):
        super().__init__()
        self.title("ZUSTAND News Studio 5.3")
        self._replace_widget_text("ZUSTAND News Studio 5.2.1", "ZUSTAND News Studio 5.3")
        self._replace_widget_text("ZUSTAND News Studio 5.2", "ZUSTAND News Studio 5.3")
        self._build_outreach_tab()
        self.status_var.set(
            "News Studio 5.3 bereit │ Kontaktaufnahme und Interview-Assistent aktiv"
        )

    def _build_outreach_tab(self) -> None:
        self.outreach_tab = ttk.Frame(self.tabs)
        self.tabs.add(self.outreach_tab, text="Kontaktaufnahme")

        outer = ttk.Frame(self.outreach_tab, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="Kontaktaufnahme vorbereiten",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Wähle einen recherchierten Kontakt und eine verknüpfte Meldung. "
                "Der Entwurf bleibt lokal und wird nicht automatisch versendet."
            ),
            wraplength=1000,
            justify="left",
        ).pack(anchor="w", pady=(2, 12))

        select_box = ttk.LabelFrame(outer, text="Auswahl", padding=10)
        select_box.pack(fill="x")

        row1 = ttk.Frame(select_box)
        row1.pack(fill="x", pady=3)
        ttk.Label(row1, text="Kontakt", width=18).pack(side="left")
        self.outreach_contact_var = tk.StringVar()
        self.outreach_contact_combo = ttk.Combobox(
            row1, textvariable=self.outreach_contact_var, state="readonly"
        )
        self.outreach_contact_combo.pack(side="left", fill="x", expand=True)
        self.outreach_contact_combo.bind(
            "<<ComboboxSelected>>", self._on_outreach_contact_selected
        )
        ttk.Button(
            row1, text="Liste aktualisieren", command=self.refresh_outreach_contacts
        ).pack(side="left", padx=(6, 0))

        row2 = ttk.Frame(select_box)
        row2.pack(fill="x", pady=3)
        ttk.Label(row2, text="Meldung/Studie", width=18).pack(side="left")
        self.outreach_article_var = tk.StringVar()
        self.outreach_article_combo = ttk.Combobox(
            row2, textvariable=self.outreach_article_var, state="readonly"
        )
        self.outreach_article_combo.pack(side="left", fill="x", expand=True)
        self.outreach_article_combo.bind(
            "<<ComboboxSelected>>", lambda _event: self.generate_outreach_text()
        )

        row3 = ttk.Frame(select_box)
        row3.pack(fill="x", pady=3)
        ttk.Label(row3, text="Textart", width=18).pack(side="left")
        self.outreach_kind_var = tk.StringVar(value="Erste E-Mail")
        self.outreach_kind_combo = ttk.Combobox(
            row3,
            textvariable=self.outreach_kind_var,
            values=(
                "Erste E-Mail",
                "Freundliche Erinnerung",
                "Intervieweinladung",
                "Telefonleitfaden",
            ),
            state="readonly",
        )
        self.outreach_kind_combo.pack(side="left", fill="x", expand=True)
        self.outreach_kind_combo.bind(
            "<<ComboboxSelected>>", lambda _event: self.generate_outreach_text()
        )

        details = ttk.LabelFrame(outer, text="Persönliche Anknüpfung", padding=10)
        details.pack(fill="x", pady=(10, 0))

        ttk.Label(
            details,
            text=(
                "Optional: Ein konkreter Satz zur Veröffentlichung. "
                "Beispiel: „Besonders aufschlussreich finde ich Ihre Einordnung, dass …“"
            ),
            wraplength=1000,
            justify="left",
        ).pack(anchor="w")
        self.outreach_hook_var = tk.StringVar()
        ttk.Entry(details, textvariable=self.outreach_hook_var).pack(
            fill="x", pady=(6, 0)
        )
        self.outreach_hook_var.trace_add(
            "write", lambda *_args: self.generate_outreach_text()
        )

        subject_row = ttk.Frame(outer)
        subject_row.pack(fill="x", pady=(12, 4))
        ttk.Label(subject_row, text="Betreff", width=12).pack(side="left")
        self.outreach_subject_var = tk.StringVar()
        ttk.Entry(subject_row, textvariable=self.outreach_subject_var).pack(
            side="left", fill="x", expand=True
        )

        editor_frame = ttk.Frame(outer)
        editor_frame.pack(fill="both", expand=True)
        scroll = ttk.Scrollbar(editor_frame, orient="vertical")
        self.outreach_text = tk.Text(
            editor_frame,
            wrap="word",
            undo=True,
            yscrollcommand=scroll.set,
            font=("Segoe UI", 10),
        )
        scroll.configure(command=self.outreach_text.yview)
        scroll.pack(side="right", fill="y")
        self.outreach_text.pack(side="left", fill="both", expand=True)

        actions = ttk.Frame(outer)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(
            actions, text="Entwurf neu erzeugen", command=self.generate_outreach_text
        ).pack(side="left")
        ttk.Button(
            actions, text="Text kopieren", command=self.copy_outreach_text
        ).pack(side="left", padx=5)
        ttk.Button(
            actions, text="Betreff + Text kopieren", command=self.copy_full_outreach
        ).pack(side="left")
        ttk.Button(
            actions, text="Im Mailprogramm öffnen", command=self.open_mail_client
        ).pack(side="right")

        self.outreach_contact_ids: list[str] = []
        self.outreach_articles: list[dict[str, str]] = []
        self.refresh_outreach_contacts()

    def refresh_outreach_contacts(self) -> None:
        contacts = self.contact_db.get("contacts", {})
        rows: list[tuple[int, str, str]] = []
        for contact_id, contact in contacts.items():
            if not isinstance(contact, dict):
                continue
            name = clean_text(contact.get("name")) or clean_text(contact.get("institution"))
            institution = clean_text(contact.get("institution"))
            email = clean_text(contact.get("email"))
            label = name
            if institution and institution.lower() not in name.lower():
                label += f" — {institution}"
            if not email:
                label += " (keine E-Mail)"
            rows.append((0 if contact.get("preferred") else 1, label.lower(), contact_id))

        rows.sort()
        self.outreach_contact_ids = [item[2] for item in rows]
        labels = []
        for _, __, contact_id in rows:
            contact = contacts[contact_id]
            name = clean_text(contact.get("name")) or clean_text(contact.get("institution"))
            institution = clean_text(contact.get("institution"))
            email = clean_text(contact.get("email"))
            label = name
            if institution and institution.lower() not in name.lower():
                label += f" — {institution}"
            if not email:
                label += " (keine E-Mail)"
            labels.append(label)

        self.outreach_contact_combo["values"] = labels
        if labels:
            current = self.outreach_contact_combo.current()
            self.outreach_contact_combo.current(current if current >= 0 else 0)
            self._on_outreach_contact_selected()
        else:
            self.outreach_contact_var.set("")
            self.outreach_article_combo["values"] = ()
            self.outreach_article_var.set("")
            self.outreach_subject_var.set("")
            self._set_outreach_text(
                "Noch keine Kontakte vorhanden. Importiere zunächst eine Recherche-Datei "
                "mit Kontaktdaten oder lege im Reiter „Kontakte“ eine Person an."
            )

    def _selected_contact(self) -> tuple[str, dict[str, Any]] | tuple[None, None]:
        index = self.outreach_contact_combo.current()
        if index < 0 or index >= len(self.outreach_contact_ids):
            return None, None
        contact_id = self.outreach_contact_ids[index]
        contact = self.contact_db.get("contacts", {}).get(contact_id)
        if not isinstance(contact, dict):
            return None, None
        return contact_id, contact

    def _on_outreach_contact_selected(self, _event=None) -> None:
        contact_id, _contact = self._selected_contact()
        if not contact_id:
            return
        self.outreach_articles = linked_articles(self.contact_db, contact_id)
        labels = [article["title"] for article in self.outreach_articles]
        self.outreach_article_combo["values"] = labels
        if labels:
            self.outreach_article_combo.current(0)
        else:
            self.outreach_article_var.set("")
        self.generate_outreach_text()

    def _selected_article(self) -> dict[str, str]:
        index = self.outreach_article_combo.current()
        if 0 <= index < len(self.outreach_articles):
            return self.outreach_articles[index]
        return {"title": "", "sourceUrl": "", "key": ""}

    def _set_outreach_text(self, value: str) -> None:
        self.outreach_text.delete("1.0", "end")
        self.outreach_text.insert("1.0", value)

    def generate_outreach_text(self) -> None:
        _contact_id, contact = self._selected_contact()
        if not contact:
            return

        article = self._selected_article()
        title = article.get("title") or "[Titel der Veröffentlichung]"
        greeting = greeting_for(contact)
        hook = clean_text(self.outreach_hook_var.get())
        hook_paragraph = f"\n\n{hook}" if hook else ""
        kind = self.outreach_kind_var.get()

        if kind == "Freundliche Erinnerung":
            subject = f"Freundliche Nachfrage zu meiner Interviewanfrage"
            body = f"""{greeting}

vor einigen Tagen hatte ich Sie wegen eines kurzen Gesprächs zu Ihrer Veröffentlichung „{title}“ angeschrieben.

Da Ihre Arbeit sehr gut zu unserem Bildungs- und Öffentlichkeitsprojekt ZUSTAND – Die Vermessung unserer Zukunft passt, möchte ich freundlich nachfragen, ob grundsätzlich Interesse an einem etwa 20- bis 30-minütigen Telefon- oder Online-Interview besteht.{hook_paragraph}

Falls es derzeit zeitlich nicht passt, genügt selbstverständlich eine kurze Rückmeldung.

Mit freundlichen Grüßen

Detlef Hau
Technische Hochschule Lübeck
Projekt ZUSTAND – Die Vermessung unserer Zukunft"""

        elif kind == "Intervieweinladung":
            subject = f"Abstimmung unseres Gesprächs zu „{title}“"
            body = f"""{greeting}

vielen Dank für Ihre Bereitschaft zu einem Gespräch über Ihre Veröffentlichung „{title}“.

Vorgesehen ist ein etwa 20- bis 30-minütiges Telefon- oder Online-Interview. Im Mittelpunkt stehen die wichtigsten Ergebnisse, ihre gesellschaftliche Bedeutung und die Frage, was daraus für Öffentlichkeit, Bildung und weitere Forschung folgt.{hook_paragraph}

Vorab sende ich Ihnen gern den kurzen Beitrag für unseren ZUSTAND-Infoscreen sowie die geplanten Themenblöcke. Das Gespräch soll nur nach vorheriger Abstimmung veröffentlicht werden.

Welche Termine würden Ihnen in den kommenden Wochen gut passen?

Mit freundlichen Grüßen

Detlef Hau
Technische Hochschule Lübeck
Projekt ZUSTAND – Die Vermessung unserer Zukunft"""

        elif kind == "Telefonleitfaden":
            subject = f"Telefonleitfaden: {title}"
            body = f"""KONTAKT
{clean_text(contact.get("name"))}
{clean_text(contact.get("role"))}
{clean_text(contact.get("institution"))}
{clean_text(contact.get("phone"))}

BEGRÜSSUNG
Guten Tag, mein Name ist Detlef Hau von der Technischen Hochschule Lübeck. Passt es gerade für eine sehr kurze Frage?

ANLASS
Ich beschäftige mich im Bildungs- und Öffentlichkeitsprojekt ZUSTAND – Die Vermessung unserer Zukunft mit aktuellen wissenschaftlichen Erkenntnissen zu Umwelt, Gesellschaft und Zukunftsfähigkeit.

WARUM DIESE PERSON?
Bei unserer Recherche bin ich auf die Veröffentlichung „{title}“ gestoßen.
{hook or "Die Ergebnisse erscheinen besonders geeignet, um sie einer breiteren Öffentlichkeit verständlich zu vermitteln."}

ANFRAGE
Hätten Sie grundsätzlich Interesse an einem etwa 20- bis 30-minütigen Telefon- oder Online-Interview?

RAHMEN
Das Gespräch ist für den Offenen Kanal Lübeck und unsere Bildungsarbeit vorgesehen. Vorher erhalten Sie den kurzen Infoscreen-Beitrag und die geplanten Themen. Eine Veröffentlichung erfolgt nur transparent und abgestimmt.

ABSCHLUSS
Darf ich Ihnen die Informationen und einige Terminvorschläge per E-Mail zusenden?

NOTIZEN NACH DEM TELEFONAT
• Interesse:
• Bevorzugtes Format:
• Mögliche Termine:
• Bedingungen/Wünsche:
• Nächster Schritt:"""

        else:
            subject = f"Anfrage zu einem kurzen Gespräch über Ihre aktuelle Veröffentlichung"
            body = f"""{greeting}

ich bin Lehrbeauftragter an der Technischen Hochschule Lübeck und beschäftige mich im Bildungs- und Öffentlichkeitsprojekt ZUSTAND – Die Vermessung unserer Zukunft mit aktuellen wissenschaftlichen Erkenntnissen zu Umwelt, Gesellschaft und Zukunftsfähigkeit.

Bei der Recherche für unseren öffentlichen Infoscreen bin ich auf Ihre Veröffentlichung „{title}“ aufmerksam geworden. Die Ergebnisse erscheinen mir besonders relevant und verständlich für eine breite Öffentlichkeit.{hook_paragraph}

Deshalb möchte ich Sie fragen, ob Sie Interesse an einem etwa 20- bis 30-minütigen Telefon- oder Online-Interview hätten. Ziel ist es, Ihre Forschung allgemeinverständlich vorzustellen und die wichtigsten Erkenntnisse direkt von Ihnen erläutern zu lassen. Das Gespräch soll unter anderem über den Offenen Kanal Lübeck sowie in unserer Bildungsarbeit verwendet werden.

Vor dem Gespräch würde ich Ihnen selbstverständlich den kurzen Beitrag für unseren Infoscreen und die vorgesehenen Themen zusenden. Eine Veröffentlichung erfolgt nur transparent und nach vorheriger Abstimmung.

Ich würde mich sehr freuen, wenn Sie Zeit für ein Gespräch finden.

Mit freundlichen Grüßen

Detlef Hau
Technische Hochschule Lübeck
Projekt ZUSTAND – Die Vermessung unserer Zukunft"""

        self.outreach_subject_var.set(subject)
        self._set_outreach_text(body)

    def copy_outreach_text(self) -> None:
        text = self.outreach_text.get("1.0", "end").strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self.status_var.set("E-Mail-Text in die Zwischenablage kopiert")

    def copy_full_outreach(self) -> None:
        subject = self.outreach_subject_var.get().strip()
        text = self.outreach_text.get("1.0", "end").strip()
        full = f"Betreff: {subject}\n\n{text}".strip()
        self.clipboard_clear()
        self.clipboard_append(full)
        self.update()
        self.status_var.set("Betreff und Text in die Zwischenablage kopiert")

    def open_mail_client(self) -> None:
        _contact_id, contact = self._selected_contact()
        if not contact:
            return
        email = clean_text(contact.get("email"))
        if not email:
            messagebox.showwarning(
                "Keine E-Mail-Adresse",
                "Für diesen Kontakt ist noch keine E-Mail-Adresse gespeichert.",
                parent=self,
            )
            return

        subject = self.outreach_subject_var.get().strip()
        body = self.outreach_text.get("1.0", "end").strip()
        mailto = (
            f"mailto:{urllib.parse.quote(email, safe='@,+')}"
            f"?subject={urllib.parse.quote(subject)}"
            f"&body={urllib.parse.quote(body)}"
        )
        try:
            webbrowser.open(mailto)
            self.status_var.set(f"Mailprogramm für {email} geöffnet")
        except Exception as exc:
            messagebox.showerror(
                "Mailprogramm konnte nicht geöffnet werden", str(exc), parent=self
            )


if __name__ == "__main__":
    app = NewsStudio53()
    app.mainloop()
