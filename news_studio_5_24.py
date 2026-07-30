#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.24.1 – Sie-/Du-Umschalter, startkorrigiert.

Baut auf der eigenständigen News-Studio-Version 5.23 auf.

Korrektur gegenüber 5.24:
- übernimmt den tatsächlichen Startweg von 5.23
- entpackt zuerst die in 5.23 eingebettete Programmkette
- erzeugt anschließend die Anwendungsklasse über create_app_class(runtime)
- sucht nicht mehr fälschlich nach einer fertigen Tk-Klasse im Modul

Neue Funktion:
- Umschalter „Ansprache: Sie | Du“ im Reiter „Kontaktaufnahme“
- Betreff und Text werden beim Umschalten neu erzeugt
- unterstützt Erste E-Mail, Erinnerung, Intervieweinladung,
  Telefonleitfaden und Dankeschön
"""

import importlib.util
import os
import re
import sys
import tempfile
import traceback
import types
from pathlib import Path
from tkinter import messagebox
from typing import Any

VERSION = "5.24.1"
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_CANDIDATES = (
    SCRIPT_DIR / "news_studio_5_23.py",
    SCRIPT_DIR / "news_studio_5_23(1).py",
    SCRIPT_DIR / "news_studio_5_23_1.py",
)
ERROR_LOG = SCRIPT_DIR / "news_studio_5_24_startfehler.txt"


def clean_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def first_name_for(contact: dict[str, Any]) -> str:
    explicit = clean_text(
        contact.get("firstName")
        or contact.get("firstname")
        or contact.get("givenName")
    )
    if explicit:
        return explicit.split()[0]

    name = clean_text(contact.get("name"))
    if not name:
        return ""

    if "," in name:
        after_comma = clean_text(name.split(",", 1)[1])
        if after_comma:
            return after_comma.split()[0].strip(" ,.;:")

    tokens = [token.strip(" ,.;:()") for token in name.split()]
    title_tokens = {
        "prof", "prof.", "professor", "professorin",
        "dr", "dr.", "dr.-ing.", "dr.-ing", "dr.-rer.-nat.",
        "dr.-med.", "dr.-phil.", "dr.-jur.", "dipl.-ing.",
        "jun.-prof.", "apl.-prof.", "priv.-doz.", "pd",
        "ing.", "habil.", "mult.", "h.c.", "e.h."
    }
    while tokens and tokens[0].casefold() in title_tokens:
        tokens.pop(0)

    return tokens[0] if tokens else ""


def greeting_for(contact: dict[str, Any], mode: str) -> str:
    if mode == "Du":
        first_name = first_name_for(contact)
        return f"Hallo {first_name}," if first_name else "Hallo,"

    name = clean_text(contact.get("name"))
    return f"Guten Tag {name}," if name else "Guten Tag,"


def build_outreach_copy(
    *,
    kind: str,
    title: str,
    contact: dict[str, Any],
    hook: str,
    address_mode: str,
) -> tuple[str, str]:
    title = clean_text(title) or "[Titel der Veröffentlichung]"
    hook = clean_text(hook)
    hook_paragraph = f"\n\n{hook}" if hook else ""
    du = address_mode == "Du"
    greeting = greeting_for(contact, address_mode)

    if du:
        studio = (
            "Die Studios des Offenen Kanals Lübeck sind montags bis freitags "
            "von 12:00 bis 19:00 Uhr geöffnet. Innerhalb dieses Zeitrahmens "
            "richten wir uns gern nach deinen Möglichkeiten."
        )
        sequence = (
            "Geplant sind eine kurze Vorstellung deiner Person und Arbeit, die "
            "verständliche Einordnung der Veröffentlichung und anschließend meine "
            "Fragen. Bei einer späteren Live-Sendung könnte das Telefon zusätzlich "
            "für Fragen von Hörerinnen und Hörern geöffnet werden; dies würden wir "
            "vorher ausdrücklich mit dir abstimmen."
        )
        precheck = (
            "Vor dem Gespräch erhältst du den vorbereiteten Infoscreen-Beitrag und "
            "die vorgesehenen Fragen zur Durchsicht. Hinweise oder Korrekturen "
            "berücksichtigen wir selbstverständlich vor der Aufzeichnung."
        )
        signature = (
            "Herzliche Grüße\n\n"
            "Detlef Hau\n"
            "Technische Hochschule Lübeck\n"
            "Projekt ZUSTAND – Die Vermessung unserer Zukunft"
        )
    else:
        studio = (
            "Die Studios des Offenen Kanals Lübeck sind montags bis freitags "
            "von 12:00 bis 19:00 Uhr geöffnet. Innerhalb dieses Zeitrahmens "
            "richten wir uns gern nach Ihren Möglichkeiten."
        )
        sequence = (
            "Geplant sind eine kurze Vorstellung Ihrer Person und Arbeit, die "
            "verständliche Einordnung der Veröffentlichung und anschließend meine "
            "Fragen. Bei einer späteren Live-Sendung könnte das Telefon zusätzlich "
            "für Fragen von Hörerinnen und Hörern geöffnet werden; dies würden wir "
            "vorher ausdrücklich mit Ihnen abstimmen."
        )
        precheck = (
            "Vor dem Gespräch erhalten Sie den vorbereiteten Infoscreen-Beitrag und "
            "die vorgesehenen Fragen zur Durchsicht. Hinweise oder Korrekturen "
            "berücksichtigen wir selbstverständlich vor der Aufzeichnung."
        )
        signature = (
            "Mit freundlichen Grüßen\n\n"
            "Detlef Hau\n"
            "Technische Hochschule Lübeck\n"
            "Projekt ZUSTAND – Die Vermessung unserer Zukunft"
        )

    if kind == "Dankeschön":
        subject = f"Vielen Dank für das Gespräch zu „{title}“"
        if du:
            body = f"""{greeting}

herzlichen Dank, dass du dir die Zeit für unser Gespräch über deine Veröffentlichung „{title}“ genommen hast. Deine Erläuterungen helfen sehr dabei, die Forschung verständlich und zugleich differenziert zu vermitteln.

Sobald der Beitrag beziehungsweise die Aufzeichnung veröffentlicht ist, sende ich dir den Link.

Über Hinweise oder Korrekturen freue ich mich auch im Nachgang.

{signature}"""
        else:
            body = f"""{greeting}

herzlichen Dank, dass Sie sich die Zeit für unser Gespräch über Ihre Veröffentlichung „{title}“ genommen haben. Ihre Erläuterungen helfen sehr dabei, die Forschung verständlich und zugleich differenziert zu vermitteln.

Sobald der Beitrag beziehungsweise die Aufzeichnung veröffentlicht ist, sende ich Ihnen den Link.

Über Hinweise oder Korrekturen freue ich mich auch im Nachgang.

{signature}"""

    elif kind == "Freundliche Erinnerung":
        subject = "Freundliche Nachfrage zu meiner Interviewanfrage"
        if du:
            body = f"""{greeting}

vor einigen Tagen hatte ich dir wegen eines kurzen Gesprächs zu deiner Veröffentlichung „{title}“ geschrieben.

Da deine Arbeit sehr gut zu unserem Bildungs- und Öffentlichkeitsprojekt ZUSTAND – Die Vermessung unserer Zukunft passt, möchte ich freundlich nachfragen, ob grundsätzlich Interesse an einem etwa 20- bis 30-minütigen Telefon- oder Online-Interview besteht.{hook_paragraph}

{studio}

Falls es derzeit zeitlich nicht passt, genügt selbstverständlich eine kurze Rückmeldung.

{signature}"""
        else:
            body = f"""{greeting}

vor einigen Tagen hatte ich Sie wegen eines kurzen Gesprächs zu Ihrer Veröffentlichung „{title}“ angeschrieben.

Da Ihre Arbeit sehr gut zu unserem Bildungs- und Öffentlichkeitsprojekt ZUSTAND – Die Vermessung unserer Zukunft passt, möchte ich freundlich nachfragen, ob grundsätzlich Interesse an einem etwa 20- bis 30-minütigen Telefon- oder Online-Interview besteht.{hook_paragraph}

{studio}

Falls es derzeit zeitlich nicht passt, genügt selbstverständlich eine kurze Rückmeldung.

{signature}"""

    elif kind == "Intervieweinladung":
        subject = f"Abstimmung unseres Gesprächs zu „{title}“"
        if du:
            body = f"""{greeting}

vielen Dank für deine Bereitschaft zu einem Gespräch über deine Veröffentlichung „{title}“.

Vorgesehen ist ein etwa 20- bis 30-minütiges Telefon- oder Online-Interview.{hook_paragraph}

{sequence}

{studio}

{precheck}

Welche Termine würden dir gut passen?

{signature}"""
        else:
            body = f"""{greeting}

vielen Dank für Ihre Bereitschaft zu einem Gespräch über Ihre Veröffentlichung „{title}“.

Vorgesehen ist ein etwa 20- bis 30-minütiges Telefon- oder Online-Interview.{hook_paragraph}

{sequence}

{studio}

{precheck}

Welche Termine würden Ihnen gut passen?

{signature}"""

    elif kind == "Telefonleitfaden":
        subject = f"Telefonleitfaden: {title}"
        name = clean_text(contact.get("name"))
        role = clean_text(contact.get("role"))
        institution = clean_text(contact.get("institution"))
        phone = clean_text(contact.get("phone"))
        reason = hook or (
            "Die Ergebnisse erscheinen besonders geeignet, um sie einer breiteren "
            "Öffentlichkeit verständlich zu vermitteln."
        )

        if du:
            request = (
                "Hättest du grundsätzlich Interesse an einem etwa 20- bis "
                "30-minütigen Telefon- oder Online-Interview?"
            )
            ending = (
                "Darf ich dir die Informationen und einige Terminvorschläge "
                "per E-Mail zusenden?"
            )
        else:
            request = (
                "Hätten Sie grundsätzlich Interesse an einem etwa 20- bis "
                "30-minütigen Telefon- oder Online-Interview?"
            )
            ending = (
                "Darf ich Ihnen die Informationen und einige Terminvorschläge "
                "per E-Mail zusenden?"
            )

        body = f"""KONTAKT
{name}
{role}
{institution}
{phone}

BEGRÜSSUNG
{greeting.rstrip(",")} – mein Name ist Detlef Hau von der Technischen Hochschule Lübeck. Passt es gerade für eine kurze Frage?

ANLASS
Ich beschäftige mich im Bildungs- und Öffentlichkeitsprojekt ZUSTAND – Die Vermessung unserer Zukunft mit aktuellen wissenschaftlichen Erkenntnissen zu Umwelt, Gesellschaft und Zukunftsfähigkeit.

WARUM DIESE PERSON?
Bei unserer Recherche bin ich auf die Veröffentlichung „{title}“ gestoßen.
{reason}

ANFRAGE
{request}

ABLAUF
{sequence}

ZEITRAHMEN
{studio}

TRANSPARENZ
{precheck}

ABSCHLUSS
{ending}

NOTIZEN
• Interesse:
• Bevorzugtes Format:
• Mögliche Termine:
• Hörerfragen möglich?
• Bedingungen/Wünsche:
• Nächster Schritt:"""

    else:
        if du:
            subject = "Anfrage zu einem kurzen Gespräch über deine aktuelle Veröffentlichung"
            body = f"""{greeting}

ich bin Lehrbeauftragter an der Technischen Hochschule Lübeck und beschäftige mich im Bildungs- und Öffentlichkeitsprojekt ZUSTAND – Die Vermessung unserer Zukunft mit aktuellen wissenschaftlichen Erkenntnissen zu Umwelt, Gesellschaft und Zukunftsfähigkeit.

Bei der Recherche für unseren öffentlichen Infoscreen bin ich auf deine Veröffentlichung „{title}“ aufmerksam geworden. Die Ergebnisse erscheinen mir besonders relevant und verständlich für eine breite Öffentlichkeit.{hook_paragraph}

Deshalb möchte ich dich fragen, ob du Interesse an einem etwa 20- bis 30-minütigen Telefon- oder Online-Interview hättest. Ziel ist es, deine Forschung allgemeinverständlich vorzustellen und die wichtigsten Erkenntnisse direkt von dir erläutern zu lassen. Das Gespräch soll unter anderem über den Offenen Kanal Lübeck sowie in unserer Bildungsarbeit verwendet werden.

{sequence}

{studio}

{precheck}

Ich würde mich sehr freuen, wenn du Zeit für ein Gespräch findest.

{signature}"""
        else:
            subject = "Anfrage zu einem kurzen Gespräch über Ihre aktuelle Veröffentlichung"
            body = f"""{greeting}

ich bin Lehrbeauftragter an der Technischen Hochschule Lübeck und beschäftige mich im Bildungs- und Öffentlichkeitsprojekt ZUSTAND – Die Vermessung unserer Zukunft mit aktuellen wissenschaftlichen Erkenntnissen zu Umwelt, Gesellschaft und Zukunftsfähigkeit.

Bei der Recherche für unseren öffentlichen Infoscreen bin ich auf Ihre Veröffentlichung „{title}“ aufmerksam geworden. Die Ergebnisse erscheinen mir besonders relevant und verständlich für eine breite Öffentlichkeit.{hook_paragraph}

Deshalb möchte ich Sie fragen, ob Sie Interesse an einem etwa 20- bis 30-minütigen Telefon- oder Online-Interview hätten. Ziel ist es, Ihre Forschung allgemeinverständlich vorzustellen und die wichtigsten Erkenntnisse direkt von Ihnen erläutern zu lassen. Das Gespräch soll unter anderem über den Offenen Kanal Lübeck sowie in unserer Bildungsarbeit verwendet werden.

{sequence}

{studio}

{precheck}

Ich würde mich sehr freuen, wenn Sie Zeit für ein Gespräch finden.

{signature}"""

    return subject, body


def load_base_module() -> types.ModuleType:
    base_path = next((path for path in BASE_CANDIDATES if path.exists()), None)
    if base_path is None:
        choices = "\n".join(f"• {path.name}" for path in BASE_CANDIDATES)
        raise FileNotFoundError(
            "News Studio 5.23 wurde nicht gefunden. Lege diese Datei in denselben "
            f"Ordner wie eine der folgenden Dateien:\n{choices}"
        )

    spec = importlib.util.spec_from_file_location(
        "news_studio_5_23_base_for_524", base_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("News Studio 5.23 konnte nicht geladen werden.")

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def create_app_class(base_class: type, runtime: types.ModuleType) -> type:
    tk = runtime.tk
    ttk = runtime.ttk

    class NewsStudio524(base_class):
        def __init__(self):
            self._outreach_address_mode_fallback = "Sie"
            super().__init__()
            self.after_idle(self._install_address_switch)
            try:
                self.title("ZUSTAND News Studio 5.24.1")
            except Exception:
                pass
            try:
                self.status_var.set(
                    "News Studio 5.24.1 bereit │ Kontakttexte in Sie- oder Du-Form"
                )
            except Exception:
                pass

        def _address_mode(self) -> str:
            variable = getattr(self, "outreach_address_var", None)
            if variable is not None:
                try:
                    value = variable.get()
                    if value in {"Sie", "Du"}:
                        return value
                except Exception:
                    pass
            return getattr(self, "_outreach_address_mode_fallback", "Sie")

        def _install_address_switch(self) -> None:
            if hasattr(self, "outreach_address_var"):
                return

            kind_combo = getattr(self, "outreach_kind_combo", None)
            if kind_combo is None:
                raise RuntimeError(
                    "Das Feld „Textart“ im Reiter Kontaktaufnahme wurde nicht gefunden."
                )

            self.outreach_address_var = tk.StringVar(master=self, value="Sie")

            kind_row = kind_combo.master
            select_box = kind_row.master
            row = ttk.Frame(select_box)
            row.pack(fill="x", pady=3)

            ttk.Label(row, text="Ansprache", width=18).pack(side="left")
            ttk.Radiobutton(
                row,
                text="Sie",
                value="Sie",
                variable=self.outreach_address_var,
                command=self.generate_outreach_text,
            ).pack(side="left")
            ttk.Radiobutton(
                row,
                text="Du",
                value="Du",
                variable=self.outreach_address_var,
                command=self.generate_outreach_text,
            ).pack(side="left", padx=(10, 0))
            ttk.Label(
                row,
                text="Betreff und Text werden beim Umschalten neu erzeugt.",
            ).pack(side="left", padx=(14, 0))

            self.generate_outreach_text()

        def generate_outreach_text(self) -> None:
            try:
                _contact_id, contact = self._selected_contact()
            except Exception:
                return
            if not isinstance(contact, dict) or not contact:
                return

            try:
                article = self._selected_article()
            except Exception:
                article = {}
            if not isinstance(article, dict):
                article = {}

            title = article.get("title") or "[Titel der Veröffentlichung]"

            try:
                hook = self.outreach_hook_var.get()
            except Exception:
                hook = ""

            try:
                kind = self.outreach_kind_var.get()
            except Exception:
                kind = "Erste E-Mail"

            subject, body = build_outreach_copy(
                kind=kind,
                title=title,
                contact=contact,
                hook=hook,
                address_mode=self._address_mode(),
            )

            try:
                self.outreach_subject_var.set(subject)
            except Exception:
                pass

            setter = getattr(self, "_set_outreach_text", None)
            if callable(setter):
                try:
                    setter(body)
                    return
                except Exception:
                    pass

            widget = getattr(self, "outreach_text", None)
            if widget is not None:
                try:
                    widget.delete("1.0", "end")
                    widget.insert("1.0", body)
                except Exception:
                    pass

    NewsStudio524.__name__ = "NewsStudio524"
    NewsStudio524.__qualname__ = "NewsStudio524"
    return NewsStudio524


def write_error(exc: BaseException) -> None:
    details = (
        "ZUSTAND News Studio 5.24.1 konnte nicht gestartet werden.\n\n"
        f"Fehlertyp: {type(exc).__name__}\n"
        f"Fehler: {exc}\n\n"
        "Technische Details:\n"
        + traceback.format_exc()
    )
    try:
        ERROR_LOG.write_text(details, encoding="utf-8")
    except OSError:
        pass


def text_self_test() -> None:
    contact = {
        "name": "Prof. Dr.-Ing. Stefanie Weidner",
        "role": "Korrespondenzautorin",
        "institution": "Werner Sobek AG",
        "phone": "+49 000 000",
    }
    kinds = (
        "Erste E-Mail",
        "Freundliche Erinnerung",
        "Intervieweinladung",
        "Telefonleitfaden",
        "Dankeschön",
    )
    for kind in kinds:
        sie_subject, sie_body = build_outreach_copy(
            kind=kind,
            title="Ressourcenminimierung im urbanen Kontext",
            contact=contact,
            hook="Besonders interessant finde ich die Verbindung von Gebäuden und Straßen.",
            address_mode="Sie",
        )
        du_subject, du_body = build_outreach_copy(
            kind=kind,
            title="Ressourcenminimierung im urbanen Kontext",
            contact=contact,
            hook="Besonders interessant finde ich die Verbindung von Gebäuden und Straßen.",
            address_mode="Du",
        )
        assert sie_subject and sie_body
        assert du_subject and du_body
        assert "Guten Tag Prof. Dr.-Ing. Stefanie Weidner" in sie_body
        assert "Hallo Stefanie" in du_body
    print("Text-Selbsttest erfolgreich: Sie/Du für fünf Textarten.")


def integration_self_test() -> None:
    """Prüft auf dem Zielrechner zusätzlich die echte eingebettete 5.23-Kette."""
    text_self_test()
    base_module = load_base_module()
    project_root = base_module.find_project_root()
    os.environ["ZUSTAND_PROJECT_ROOT"] = str(project_root)

    with tempfile.TemporaryDirectory(prefix="zustand_studio_524_test_") as temporary:
        runtime_dir = Path(temporary)
        base_module.extract_runtime(runtime_dir)
        runtime = base_module.load_runtime_module(runtime_dir)
        base_class = base_module.create_app_class(runtime)

        required = (
            "generate_outreach_text",
            "_selected_contact",
            "_selected_article",
        )
        missing = [name for name in required if not hasattr(base_class, name)]
        if missing:
            raise RuntimeError(
                "In der geladenen 5.23 fehlen benötigte Funktionen: "
                + ", ".join(missing)
            )
        create_app_class(base_class, runtime)

    print("Integrationstest erfolgreich: eingebettete 5.23-Kette wurde geladen.")


def main() -> int:
    if "--text-self-test" in sys.argv:
        text_self_test()
        return 0

    if "--self-test" in sys.argv:
        integration_self_test()
        return 0

    try:
        base_module = load_base_module()
        project_root = base_module.find_project_root()
        os.environ["ZUSTAND_PROJECT_ROOT"] = str(project_root)

        # Wichtig: Der temporäre Ordner muss bis zum Schließen des Fensters
        # bestehen bleiben, genau wie bei der eigenständigen Version 5.23.
        with tempfile.TemporaryDirectory(prefix="zustand_studio_524_") as temporary:
            runtime_dir = Path(temporary)
            base_module.extract_runtime(runtime_dir)
            runtime = base_module.load_runtime_module(runtime_dir)

            base_class = base_module.create_app_class(runtime)
            app_class = create_app_class(base_class, runtime)
            app = app_class()
            app.mainloop()
        return 0

    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        write_error(exc)
        try:
            messagebox.showerror(
                "News Studio 5.24.1 – Startfehler",
                f"{type(exc).__name__}: {exc}\n\n"
                f"Fehlerbericht:\n{ERROR_LOG}",
            )
        except Exception:
            pass
        print(f"News Studio 5.24.1 – Startfehler: {exc}", file=sys.stderr)
        print(f"Fehlerbericht: {ERROR_LOG}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
