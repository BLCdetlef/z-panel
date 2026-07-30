#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.24.4 – Sie-/Du-Umschalter, startkorrigiert.

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
- vollständige Signatur mit Telefon, Mobilnummer und E-Mail
- kurzes Telefonat als Vorschlag für Terminabstimmung und Rückfragen
- optionaler Hinweis auf eine Beispielfolge
- KI-Recherche nur als freiwilliges Angebot
- Zustimmungsstatus: Offen, Zugestimmt, Abgelehnt oder Gespräch gewünscht
- gesonderte Dokumentation der mündlichen Bestätigung
- alle KI-Angaben bleiben in der privaten lokalen Kontaktdatenbank
- vertikaler Scrollbalken für den gesamten Reiter „Kontaktaufnahme“
- Mausrad scrollt die Seite; das Nachrichtentextfeld behält seine eigene Scrollfunktion
"""

import importlib.util
import json
import os
import re
import webbrowser
import sys
import tempfile
import traceback
import types
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox
from typing import Any

VERSION = "5.24.4"
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_CANDIDATES = (
    SCRIPT_DIR / "news_studio_5_23.py",
    SCRIPT_DIR / "news_studio_5_23(1).py",
    SCRIPT_DIR / "news_studio_5_23_1.py",
)
ERROR_LOG = SCRIPT_DIR / "news_studio_5_24_4_startfehler.txt"

SENDER_NAME = "Detlef Hau"
SENDER_INSTITUTION = "Technische Hochschule Lübeck"
SENDER_PROJECT = "Projekt ZUSTAND – Die Vermessung unserer Zukunft"
SENDER_PHONE = "+49 451 300-5660"
SENDER_MOBILE = "+49 173 6144597"
SENDER_EMAIL = "detlef.hau@th-luebeck.de"

AI_CONSENT_VALUES = (
    "Offen",
    "Zugestimmt",
    "Abgelehnt",
    "Gespräch gewünscht",
)
AI_SETTINGS_KEY = "aiInterviewSettings"
AI_DEFAULTS_KEY = "aiInterviewDefaults"


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
            f"{SENDER_NAME}\n"
            f"{SENDER_INSTITUTION}\n"
            f"{SENDER_PROJECT}\n\n"
            f"Tel.: {SENDER_PHONE}\n"
            f"Mobil: {SENDER_MOBILE}\n"
            f"E-Mail: {SENDER_EMAIL}"
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
            f"{SENDER_NAME}\n"
            f"{SENDER_INSTITUTION}\n"
            f"{SENDER_PROJECT}\n\n"
            f"Tel.: {SENDER_PHONE}\n"
            f"Mobil: {SENDER_MOBILE}\n"
            f"E-Mail: {SENDER_EMAIL}"
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

Wenn grundsätzlich Interesse besteht, schlage ich zwecks Abstimmung und möglicher Rückfragen ein kurzes Telefonat vor. Du kannst mir gern einen passenden Zeitpunkt nennen. Meine Kontaktdaten findest du unterhalb.

Falls es derzeit zeitlich nicht passt, genügt selbstverständlich eine kurze Rückmeldung.

{signature}"""
        else:
            body = f"""{greeting}

vor einigen Tagen hatte ich Sie wegen eines kurzen Gesprächs zu Ihrer Veröffentlichung „{title}“ angeschrieben.

Da Ihre Arbeit sehr gut zu unserem Bildungs- und Öffentlichkeitsprojekt ZUSTAND – Die Vermessung unserer Zukunft passt, möchte ich freundlich nachfragen, ob grundsätzlich Interesse an einem etwa 20- bis 30-minütigen Telefon- oder Online-Interview besteht.{hook_paragraph}

{studio}

Wenn grundsätzlich Interesse besteht, schlage ich zwecks Abstimmung und möglicher Rückfragen ein kurzes Telefonat vor. Sie können mir gern einen passenden Zeitpunkt nennen. Meine Kontaktdaten finden Sie unterhalb.

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

Für die konkrete Terminabstimmung und mögliche Rückfragen schlage ich ein kurzes Telefonat vor. Du kannst mir gern einen passenden Zeitpunkt nennen. Meine Kontaktdaten findest du unterhalb.

{signature}"""
        else:
            body = f"""{greeting}

vielen Dank für Ihre Bereitschaft zu einem Gespräch über Ihre Veröffentlichung „{title}“.

Vorgesehen ist ein etwa 20- bis 30-minütiges Telefon- oder Online-Interview.{hook_paragraph}

{sequence}

{studio}

{precheck}

Für die konkrete Terminabstimmung und mögliche Rückfragen schlage ich ein kurzes Telefonat vor. Sie können mir gern einen passenden Zeitpunkt nennen. Meine Kontaktdaten finden Sie unterhalb.

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

Ich würde mich sehr freuen, wenn du Zeit für ein Gespräch findest, und schlage zwecks Abstimmung und möglicher Rückfragen ein kurzes Telefonat vor. Du kannst mir gern einen passenden Zeitpunkt nennen. Meine Kontaktdaten findest du unterhalb.

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

Ich würde mich sehr freuen, wenn Sie Zeit für ein Gespräch finden, und schlage zwecks Abstimmung und möglicher Rückfragen ein kurzes Telefonat vor. Sie können mir gern einen passenden Zeitpunkt nennen. Meine Kontaktdaten finden Sie unterhalb.

{signature}"""

    return subject, body



def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _sample_episode_paragraph(url: str, address_mode: str) -> str:
    url = clean_text(url)
    if not url:
        return ""
    if address_mode == "Du":
        return (
            "Falls du das Format vorab kennenlernen möchtest, kannst du hier "
            "eine bereits veröffentlichte Folge anhören:\n"
            f"{url}"
        )
    return (
        "Falls Sie das Format vorab kennenlernen möchten, können Sie hier "
        "eine bereits veröffentlichte Folge anhören:\n"
        f"{url}"
    )


def _ai_open_consent_block(address_mode: str, sample_url: str) -> str:
    sample = _sample_episode_paragraph(sample_url, address_mode)
    if address_mode == "Du":
        core = """Bei Interesse würden wir während des Gesprächs gelegentlich auch eine KI als zusätzliche Rechercheunterstützung hinzuziehen – selbstverständlich nur mit deiner vorherigen ausdrücklichen Zustimmung.¹

Deine Wahl:
☐ Ja, ich stimme der beschriebenen punktuellen Einbindung zu.
☐ Nein, ich möchte das Gespräch ohne KI-Unterstützung führen.
☐ Ich möchte dies zunächst telefonisch besprechen.

¹ KI-Recherche im Gespräch: Die KI wird ausschließlich punktuell und nach ausdrücklicher Ankündigung einbezogen, beispielsweise bei der Frage, ob zu einem angesprochenen Aspekt bereits weitere Forschungsergebnisse oder Primärquellen vorliegen. Sie soll das Gespräch ergänzen, nicht deine fachliche Einordnung bewerten oder ersetzen. Genannte Quellen und Aussagen werden vor einer Veröffentlichung nochmals überprüft. Ohne deine ausdrückliche Zustimmung findet das Interview ohne KI-Unterstützung statt."""
    else:
        core = """Bei Interesse würden wir während des Gesprächs gelegentlich auch eine KI als zusätzliche Rechercheunterstützung hinzuziehen – selbstverständlich nur mit Ihrer vorherigen ausdrücklichen Zustimmung.¹

Ihre Wahl:
☐ Ja, ich stimme der beschriebenen punktuellen Einbindung zu.
☐ Nein, ich möchte das Gespräch ohne KI-Unterstützung führen.
☐ Ich möchte dies zunächst telefonisch besprechen.

¹ KI-Recherche im Gespräch: Die KI wird ausschließlich punktuell und nach ausdrücklicher Ankündigung einbezogen, beispielsweise bei der Frage, ob zu einem angesprochenen Aspekt bereits weitere Forschungsergebnisse oder Primärquellen vorliegen. Sie soll das Gespräch ergänzen, nicht Ihre fachliche Einordnung bewerten oder ersetzen. Genannte Quellen und Aussagen werden vor einer Veröffentlichung nochmals überprüft. Ohne Ihre ausdrückliche Zustimmung findet das Interview ohne KI-Unterstützung statt."""
    return "\n\n".join(part for part in (sample, core) if part)


def _ai_status_email_block(
    *,
    address_mode: str,
    sample_url: str,
    consent_status: str,
    oral_confirmed: bool,
) -> str:
    consent_status = consent_status if consent_status in AI_CONSENT_VALUES else "Offen"
    sample = _sample_episode_paragraph(sample_url, address_mode)

    if consent_status == "Offen":
        return _ai_open_consent_block(address_mode, sample_url)

    if consent_status == "Zugestimmt":
        if address_mode == "Du":
            core = (
                "Vielen Dank für deine ausdrückliche Zustimmung zur beschriebenen "
                "punktuellen KI-Recherche. Die KI wird nur bei spontan entstehenden "
                "Sachfragen und nach Ankündigung hinzugezogen. Sie soll möglichst "
                "wissenschaftliche Veröffentlichungen und Primärquellen nennen; "
                "deine fachliche Einordnung bleibt maßgeblich. Genannte Quellen und "
                "Aussagen werden vor einer Veröffentlichung nochmals überprüft. "
                "Zu Beginn der Aufnahme bestätigen wir die Zustimmung noch einmal kurz."
            )
        else:
            core = (
                "Vielen Dank für Ihre ausdrückliche Zustimmung zur beschriebenen "
                "punktuellen KI-Recherche. Die KI wird nur bei spontan entstehenden "
                "Sachfragen und nach Ankündigung hinzugezogen. Sie soll möglichst "
                "wissenschaftliche Veröffentlichungen und Primärquellen nennen; "
                "Ihre fachliche Einordnung bleibt maßgeblich. Genannte Quellen und "
                "Aussagen werden vor einer Veröffentlichung nochmals überprüft. "
                "Zu Beginn der Aufnahme bestätigen wir die Zustimmung noch einmal kurz."
            )
        return "\n\n".join(part for part in (sample, core) if part)

    if consent_status == "Abgelehnt":
        return (
            "Wie vereinbart, findet das Gespräch ohne KI-Unterstützung statt."
            if address_mode == "Du"
            else "Wie vereinbart, findet das Gespräch ohne KI-Unterstützung statt."
        )

    if address_mode == "Du":
        core = (
            "Die mögliche KI-Recherche besprechen wir zunächst telefonisch. "
            "Bis zu deiner ausdrücklichen Zustimmung findet das Interview ohne "
            "KI-Unterstützung statt."
        )
    else:
        core = (
            "Die mögliche KI-Recherche besprechen wir zunächst telefonisch. "
            "Bis zu Ihrer ausdrücklichen Zustimmung findet das Interview ohne "
            "KI-Unterstützung statt."
        )
    return "\n\n".join(part for part in (sample, core) if part)


def _ai_phone_guide_block(
    *,
    address_mode: str,
    sample_url: str,
    consent_status: str,
    oral_confirmed: bool,
) -> str:
    consent_status = consent_status if consent_status in AI_CONSENT_VALUES else "Offen"
    sample_line = f"\nBeispielfolge: {clean_text(sample_url)}" if clean_text(sample_url) else ""
    confirmed = "Ja" if oral_confirmed else "Nein"

    if consent_status == "Zugestimmt":
        return f"""KI-RECHERCHE
Status: Zugestimmt
Mündlich bestätigt: {confirmed}{sample_line}

Die interviewte Person hat der punktuellen KI-Recherche ausdrücklich zugestimmt. Die KI nur nach Ankündigung und nur bei spontan entstehenden Sachfragen hinzuziehen. Genannte Veröffentlichungen und Aussagen später nochmals an den Quellen prüfen.

BESTÄTIGUNG ZU BEGINN DER AUFNAHME
„Wir hatten vereinbart, dass wir bei Bedarf eine KI zur Suche nach weiterführenden Forschungsergebnissen hinzuziehen dürfen. Ist das für Sie weiterhin in Ordnung?“

WICHTIG
Bei einem Nein oder einer Einschränkung bleibt die KI aus beziehungsweise wird nur im ausdrücklich vereinbarten Umfang eingesetzt."""

    if consent_status == "Abgelehnt":
        return f"""KI-RECHERCHE
Status: Abgelehnt
Mündlich bestätigt: {confirmed}{sample_line}

Keine KI in das Interview einbeziehen. Die Ablehnung ist vollständig zu respektieren."""

    if consent_status == "Gespräch gewünscht":
        return f"""KI-RECHERCHE
Status: Gespräch gewünscht
Mündlich bestätigt: {confirmed}{sample_line}

Kurz erläutern: Die KI würde nur punktuell und nach Ankündigung nach weiteren wissenschaftlichen Veröffentlichungen oder Primärquellen suchen. Sie ersetzt nicht die fachliche Einordnung und alle wichtigen Angaben werden später geprüft.

ZUSTIMMUNGSFRAGE
„Hätten Sie Interesse an dieser punktuellen Rechercheunterstützung? Ohne Ihre ausdrückliche Zustimmung bleibt die KI vollständig außen vor.“

Ergebnis anschließend im Feld „Zustimmung“ dokumentieren."""

    return f"""KI-RECHERCHE
Status: Offen
Mündlich bestätigt: {confirmed}{sample_line}

OPTIONAL ERLÄUTERN
Die KI würde nur punktuell und nach ausdrücklicher Ankündigung einbezogen, beispielsweise bei der Frage, ob es zu einem angesprochenen Aspekt weitere Forschungsergebnisse oder Primärquellen gibt. Sie ergänzt das Gespräch, ersetzt aber nicht die fachliche Einordnung. Alle wichtigen Angaben werden vor der Veröffentlichung nochmals geprüft.

ZUSTIMMUNGSFRAGE
„Hätten Sie Interesse an dieser punktuellen Rechercheunterstützung? Ohne Ihre ausdrückliche Zustimmung bleibt die KI vollständig außen vor.“

MÖGLICHE ANTWORTEN
• Zugestimmt
• Abgelehnt
• Zunächst telefonisch weiter klären

Ergebnis im Feld „Zustimmung“ dokumentieren."""


def add_ai_research_to_copy(
    body: str,
    *,
    kind: str,
    address_mode: str,
    offer_ai: bool,
    sample_url: str,
    consent_status: str,
    oral_confirmed: bool,
) -> str:
    """Ergänzt den bestehenden Text, ohne die bewährten Vorlagen umzubauen."""
    if not offer_ai or kind == "Dankeschön":
        return body

    if kind == "Telefonleitfaden":
        block = _ai_phone_guide_block(
            address_mode=address_mode,
            sample_url=sample_url,
            consent_status=consent_status,
            oral_confirmed=oral_confirmed,
        )
        marker = "\n\nNOTIZEN"
        if marker in body:
            return body.replace(marker, f"\n\n{block}{marker}", 1)
        return f"{body.rstrip()}\n\n{block}"

    block = _ai_status_email_block(
        address_mode=address_mode,
        sample_url=sample_url,
        consent_status=consent_status,
        oral_confirmed=oral_confirmed,
    )
    if not block:
        return body

    for marker in ("\n\nMit freundlichen Grüßen", "\n\nHerzliche Grüße"):
        if marker in body:
            return body.replace(marker, f"\n\n{block}{marker}", 1)
    return f"{body.rstrip()}\n\n{block}"


def make_frame_vertically_scrollable(
    tk_module,
    ttk_module,
    *,
    tab,
    content,
) -> dict[str, Any]:
    """Legt einen vorhandenen Tab-Inhalt in eine vertikal scrollbare Ansicht.

    Der vorhandene Frame muss nicht neu aufgebaut werden. Tk erlaubt, dass ein
    Canvas ein Fenster einbettet, das ein Kind eines gemeinsamen Vorfahren ist.
    Dadurch bleiben alle bestehenden Widgets, Variablen und Ereignisbindungen
    vollständig erhalten.
    """
    if getattr(content, "_zustand_scroll_wrapped", False):
        return getattr(content, "_zustand_scroll_handles", {})

    manager = content.winfo_manager()
    if manager == "pack":
        content.pack_forget()
    elif manager == "grid":
        content.grid_remove()
    elif manager == "place":
        content.place_forget()

    viewport = ttk_module.Frame(tab)
    viewport.pack(fill="both", expand=True)

    style = ttk_module.Style(tab)
    background = style.lookup("TFrame", "background") or "#f0f0f0"

    canvas = tk_module.Canvas(
        viewport,
        highlightthickness=0,
        borderwidth=0,
        background=background,
    )
    scrollbar = ttk_module.Scrollbar(
        viewport,
        orient="vertical",
        command=canvas.yview,
    )
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    window_id = canvas.create_window(
        (0, 0),
        window=content,
        anchor="nw",
    )

    def update_scrollregion(_event=None):
        try:
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)
        except Exception:
            pass

    def fit_content_width(event):
        try:
            canvas.itemconfigure(window_id, width=max(int(event.width), 1))
            update_scrollregion()
        except Exception:
            pass

    content.bind("<Configure>", update_scrollregion, add="+")
    canvas.bind("<Configure>", fit_content_width, add="+")

    # Scrollbare Unterelemente behalten ihr eigenes Verhalten.
    own_scroll_classes = {
        "Text",
        "Listbox",
        "Treeview",
        "TCombobox",
        "Scrollbar",
        "TScrollbar",
    }

    def scroll_windows(event):
        try:
            delta = int(event.delta)
        except Exception:
            delta = 0
        if delta == 0:
            return None
        direction = -1 if delta > 0 else 1
        canvas.yview_scroll(direction * 3, "units")
        return "break"

    def scroll_linux_up(_event):
        canvas.yview_scroll(-3, "units")
        return "break"

    def scroll_linux_down(_event):
        canvas.yview_scroll(3, "units")
        return "break"

    def bind_mousewheel_tree(widget):
        try:
            widget_class = widget.winfo_class()
        except Exception:
            widget_class = ""

        if widget_class not in own_scroll_classes:
            try:
                widget.bind("<MouseWheel>", scroll_windows, add="+")
                widget.bind("<Button-4>", scroll_linux_up, add="+")
                widget.bind("<Button-5>", scroll_linux_down, add="+")
            except Exception:
                pass

        try:
            children = widget.winfo_children()
        except Exception:
            children = []
        for child in children:
            bind_mousewheel_tree(child)

    bind_mousewheel_tree(content)
    bind_mousewheel_tree(canvas)

    content._zustand_scroll_wrapped = True
    handles = {
        "viewport": viewport,
        "canvas": canvas,
        "scrollbar": scrollbar,
        "content": content,
        "window_id": window_id,
        "update_scrollregion": update_scrollregion,
    }
    content._zustand_scroll_handles = handles

    tab.after_idle(update_scrollregion)
    tab.after_idle(lambda: canvas.yview_moveto(0.0))
    return handles


def scroll_layout_self_test() -> None:
    """Kleiner GUI-Test der echten Scroll-Hilfsfunktion."""
    import tkinter as test_tk
    from tkinter import ttk as test_ttk

    root = test_tk.Tk()
    root.geometry("520x280")
    tab = test_ttk.Frame(root)
    tab.pack(fill="both", expand=True)

    content = test_ttk.Frame(tab, padding=12)
    content.pack(fill="both", expand=True)
    for index in range(35):
        test_ttk.Label(content, text=f"Testzeile {index + 1}").pack(anchor="w")

    handles = make_frame_vertically_scrollable(
        test_tk,
        test_ttk,
        tab=tab,
        content=content,
    )
    root.update_idletasks()

    canvas = handles["canvas"]
    bbox = canvas.bbox("all")
    if not bbox:
        root.destroy()
        raise RuntimeError("Die Scrollregion wurde nicht erzeugt.")

    content_height = bbox[3] - bbox[1]
    canvas_height = max(canvas.winfo_height(), 1)
    if content_height <= canvas_height:
        root.destroy()
        raise RuntimeError("Der Testinhalt ist nicht höher als das Sichtfenster.")

    canvas.yview_moveto(1.0)
    root.update_idletasks()
    top, bottom = canvas.yview()
    root.destroy()

    if top <= 0:
        raise RuntimeError("Der Canvas ließ sich nicht nach unten scrollen.")

    print("Scroll-Selbsttest erfolgreich: vertikaler Seiten-Scrollbalken funktioniert.")

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
            # Während des geerbten Fensteraufbaus gelten sichere Standardwerte.
            self._outreach_address_mode_fallback = "Sie"
            self._ai_settings_loading = False
            self._ai_save_after_id = None
            super().__init__()
            self.after_idle(self._install_outreach_extensions)
            try:
                self.title("ZUSTAND News Studio 5.24.4")
            except Exception:
                pass
            try:
                self.status_var.set(
                    "News Studio 5.24.4 bereit │ KI-Recherche nur nach ausdrücklicher Zustimmung"
                )
            except Exception:
                pass

        # ---------- Ansprache ----------
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

        # ---------- Auswahl und private Speicherung ----------
        def _ai_selection_key(self) -> str:
            try:
                contact_id, _contact = self._selected_contact()
            except Exception:
                return ""
            if not contact_id:
                return ""

            try:
                article = self._selected_article()
            except Exception:
                article = {}
            if not isinstance(article, dict):
                article = {}

            article_key = clean_text(
                article.get("key")
                or article.get("sourceUrl")
                or article.get("title")
            )
            if not article_key:
                return ""
            return f"{contact_id}::{article_key}"

        def _write_private_contact_db(self) -> bool:
            try:
                saver = getattr(self, "_save_db", None)
                if callable(saver):
                    saver()
                    return True

                writer = getattr(runtime, "write_contact_db", None)
                if callable(writer):
                    try:
                        writer(self.contact_db)
                    except TypeError:
                        writer(
                            self.contact_db,
                            getattr(self, "contact_db_path", None),
                        )
                    return True
            except Exception as exc:
                try:
                    self.status_var.set(
                        f"KI-Einstellungen konnten nicht gespeichert werden: {exc}"
                    )
                except Exception:
                    pass
                return False
            return False

        def _current_ai_values(self) -> dict[str, Any]:
            offer_var = getattr(self, "ai_offer_var", None)
            sample_var = getattr(self, "ai_sample_episode_var", None)
            consent_var = getattr(self, "ai_consent_var", None)
            oral_var = getattr(self, "ai_oral_confirmed_var", None)

            try:
                offer = bool(offer_var.get()) if offer_var is not None else True
            except Exception:
                offer = True
            try:
                sample = clean_text(sample_var.get()) if sample_var is not None else ""
            except Exception:
                sample = ""
            try:
                consent = consent_var.get() if consent_var is not None else "Offen"
            except Exception:
                consent = "Offen"
            if consent not in AI_CONSENT_VALUES:
                consent = "Offen"
            try:
                oral = bool(oral_var.get()) if oral_var is not None else False
            except Exception:
                oral = False

            return {
                "offer": offer,
                "sampleEpisodeUrl": sample,
                "consentStatus": consent,
                "oralConfirmed": oral,
            }

        def _save_ai_settings(self) -> None:
            self._ai_save_after_id = None
            if self._ai_settings_loading:
                return

            key = self._ai_selection_key()
            if not key:
                return

            values = self._current_ai_values()
            db = self.contact_db
            defaults = db.setdefault(AI_DEFAULTS_KEY, {})
            if isinstance(defaults, dict):
                defaults["sampleEpisodeUrl"] = values["sampleEpisodeUrl"]
                defaults.setdefault("offerByDefault", True)
                defaults["updatedAt"] = now_iso()

            records = db.setdefault(AI_SETTINGS_KEY, {})
            if not isinstance(records, dict):
                records = {}
                db[AI_SETTINGS_KEY] = records

            records[key] = {
                "offer": values["offer"],
                "consentStatus": values["consentStatus"],
                "oralConfirmed": values["oralConfirmed"],
                "updatedAt": now_iso(),
            }

            if self._write_private_contact_db():
                try:
                    self.status_var.set(
                        "KI-Angebot und Zustimmungsstatus privat gespeichert"
                    )
                except Exception:
                    pass

        def _schedule_ai_save(self) -> None:
            if self._ai_settings_loading:
                return
            previous = getattr(self, "_ai_save_after_id", None)
            if previous:
                try:
                    self.after_cancel(previous)
                except Exception:
                    pass
            try:
                self._ai_save_after_id = self.after(500, self._save_ai_settings)
            except Exception:
                self._save_ai_settings()

        def _load_ai_settings_for_selection(self) -> None:
            if not hasattr(self, "ai_offer_var"):
                return

            key = self._ai_selection_key()
            db = self.contact_db
            defaults = db.get(AI_DEFAULTS_KEY, {})
            if not isinstance(defaults, dict):
                defaults = {}
            records = db.get(AI_SETTINGS_KEY, {})
            if not isinstance(records, dict):
                records = {}
            stored = records.get(key, {}) if key else {}
            if not isinstance(stored, dict):
                stored = {}

            self._ai_settings_loading = True
            try:
                self.ai_offer_var.set(
                    bool(stored.get("offer", defaults.get("offerByDefault", True)))
                )
                self.ai_sample_episode_var.set(
                    clean_text(defaults.get("sampleEpisodeUrl"))
                )
                consent = stored.get("consentStatus", "Offen")
                if consent not in AI_CONSENT_VALUES:
                    consent = "Offen"
                self.ai_consent_var.set(consent)
                self.ai_oral_confirmed_var.set(
                    bool(stored.get("oralConfirmed", False))
                    if consent == "Zugestimmt"
                    else False
                )
            finally:
                self._ai_settings_loading = False

            self._update_ai_control_state()
            self.generate_outreach_text()

        def _on_ai_setting_changed(self, *_args) -> None:
            if self._ai_settings_loading:
                return

            try:
                consent = self.ai_consent_var.get()
            except Exception:
                consent = "Offen"

            if consent != "Zugestimmt":
                try:
                    if self.ai_oral_confirmed_var.get():
                        self._ai_settings_loading = True
                        self.ai_oral_confirmed_var.set(False)
                finally:
                    self._ai_settings_loading = False

            self._update_ai_control_state()
            self.generate_outreach_text()
            self._schedule_ai_save()

        def _update_ai_control_state(self) -> None:
            oral_widget = getattr(self, "ai_oral_confirmed_check", None)
            if oral_widget is not None:
                try:
                    enabled = (
                        bool(self.ai_offer_var.get())
                        and self.ai_consent_var.get() == "Zugestimmt"
                    )
                    oral_widget.configure(state="normal" if enabled else "disabled")
                except Exception:
                    pass

            consent_widget = getattr(self, "ai_consent_combo", None)
            sample_widget = getattr(self, "ai_sample_episode_entry", None)
            try:
                offer = bool(self.ai_offer_var.get())
            except Exception:
                offer = True
            for widget in (consent_widget, sample_widget):
                if widget is None:
                    continue
                try:
                    if widget is consent_widget:
                        widget.configure(state="readonly" if offer else "disabled")
                    else:
                        widget.configure(state="normal" if offer else "disabled")
                except Exception:
                    pass

        def _open_sample_episode(self) -> None:
            try:
                url = clean_text(self.ai_sample_episode_var.get())
            except Exception:
                url = ""
            if not url:
                messagebox.showinfo(
                    "Keine Beispielfolge",
                    "Trage zunächst den Link zu einer veröffentlichten Folge ein.",
                    parent=self,
                )
                return
            try:
                webbrowser.open(url)
            except Exception as exc:
                messagebox.showerror(
                    "Link konnte nicht geöffnet werden",
                    str(exc),
                    parent=self,
                )

        # ---------- Oberfläche ----------
        def _install_outreach_extensions(self) -> None:
            if hasattr(self, "outreach_address_var"):
                return

            kind_combo = getattr(self, "outreach_kind_combo", None)
            if kind_combo is None:
                raise RuntimeError(
                    "Das Feld „Textart“ im Reiter Kontaktaufnahme wurde nicht gefunden."
                )

            kind_row = kind_combo.master
            select_box = kind_row.master

            # Ansprache
            self.outreach_address_var = tk.StringVar(master=self, value="Sie")
            address_row = ttk.Frame(select_box)
            address_row.pack(fill="x", pady=3)
            ttk.Label(address_row, text="Ansprache", width=18).pack(side="left")
            ttk.Radiobutton(
                address_row,
                text="Sie",
                value="Sie",
                variable=self.outreach_address_var,
                command=self.generate_outreach_text,
            ).pack(side="left")
            ttk.Radiobutton(
                address_row,
                text="Du",
                value="Du",
                variable=self.outreach_address_var,
                command=self.generate_outreach_text,
            ).pack(side="left", padx=(10, 0))
            ttk.Label(
                address_row,
                text="Betreff und Text werden beim Umschalten neu erzeugt.",
            ).pack(side="left", padx=(14, 0))

            # KI-Recherche
            ai_box = ttk.LabelFrame(
                select_box,
                text="Optionale KI-Recherche im Interview",
                padding=8,
            )
            ai_box.pack(fill="x", pady=(8, 2))

            self.ai_offer_var = tk.BooleanVar(master=self, value=True)
            self.ai_sample_episode_var = tk.StringVar(master=self, value="")
            self.ai_consent_var = tk.StringVar(master=self, value="Offen")
            self.ai_oral_confirmed_var = tk.BooleanVar(master=self, value=False)

            row1 = ttk.Frame(ai_box)
            row1.pack(fill="x", pady=2)
            ttk.Checkbutton(
                row1,
                text="KI-Recherche als freiwillige Wahlmöglichkeit anbieten",
                variable=self.ai_offer_var,
            ).pack(side="left")
            ttk.Label(row1, text="Zustimmung", padding=(18, 0, 4, 0)).pack(
                side="left"
            )
            self.ai_consent_combo = ttk.Combobox(
                row1,
                textvariable=self.ai_consent_var,
                values=AI_CONSENT_VALUES,
                state="readonly",
                width=20,
            )
            self.ai_consent_combo.pack(side="left")
            self.ai_oral_confirmed_check = ttk.Checkbutton(
                row1,
                text="mündlich bestätigt",
                variable=self.ai_oral_confirmed_var,
            )
            self.ai_oral_confirmed_check.pack(side="left", padx=(14, 0))

            row2 = ttk.Frame(ai_box)
            row2.pack(fill="x", pady=2)
            ttk.Label(row2, text="Beispielfolge", width=18).pack(side="left")
            self.ai_sample_episode_entry = ttk.Entry(
                row2,
                textvariable=self.ai_sample_episode_var,
            )
            self.ai_sample_episode_entry.pack(
                side="left",
                fill="x",
                expand=True,
            )
            ttk.Button(
                row2,
                text="Öffnen",
                command=self._open_sample_episode,
            ).pack(side="left", padx=(6, 0))
            ttk.Button(
                row2,
                text="Speichern",
                command=self._save_ai_settings,
            ).pack(side="left", padx=(6, 0))

            ttk.Label(
                ai_box,
                text=(
                    "Ohne vorherige ausdrückliche Zustimmung bleibt die KI vollständig "
                    "außen vor. Die Beispielfolge wird als gemeinsamer Standard für "
                    "weitere Anfragen gespeichert."
                ),
                wraplength=1050,
                justify="left",
            ).pack(anchor="w", pady=(4, 0))

            for variable in (
                self.ai_offer_var,
                self.ai_sample_episode_var,
                self.ai_consent_var,
                self.ai_oral_confirmed_var,
            ):
                variable.trace_add("write", self._on_ai_setting_changed)

            article_combo = getattr(self, "outreach_article_combo", None)
            if article_combo is not None:
                article_combo.bind(
                    "<<ComboboxSelected>>",
                    self._on_ai_article_selected,
                    add="+",
                )

            self._load_ai_settings_for_selection()
            self.after_idle(self._install_outreach_scrollbar)

        def _install_outreach_scrollbar(self) -> None:
            if hasattr(self, "outreach_scroll_canvas"):
                return

            tab = getattr(self, "outreach_tab", None)
            kind_combo = getattr(self, "outreach_kind_combo", None)
            if tab is None or kind_combo is None:
                raise RuntimeError(
                    "Der Reiter „Kontaktaufnahme“ konnte nicht für das Scrollen vorbereitet werden."
                )

            # Vom Feld „Textart“ bis zum direkten Inhaltsframe des Tabs hochgehen.
            content = kind_combo
            while getattr(content, "master", None) is not tab:
                parent = getattr(content, "master", None)
                if parent is None or parent is content:
                    raise RuntimeError(
                        "Der Inhaltsrahmen des Reiters „Kontaktaufnahme“ wurde nicht gefunden."
                    )
                content = parent

            handles = make_frame_vertically_scrollable(
                tk,
                ttk,
                tab=tab,
                content=content,
            )
            self.outreach_scroll_viewport = handles["viewport"]
            self.outreach_scroll_canvas = handles["canvas"]
            self.outreach_scrollbar = handles["scrollbar"]
            self.outreach_scroll_content = handles["content"]

            try:
                self.status_var.set(
                    "News Studio 5.24.4 bereit │ Kontaktaufnahme vollständig scrollbar"
                )
            except Exception:
                pass

        def _on_ai_article_selected(self, _event=None) -> None:
            self._load_ai_settings_for_selection()

        def _on_outreach_contact_selected(self, _event=None) -> None:
            result = super()._on_outreach_contact_selected(_event)
            if hasattr(self, "ai_offer_var"):
                self.after_idle(self._load_ai_settings_for_selection)
            return result

        # ---------- Texterzeugung ----------
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

            ai_values = self._current_ai_values()
            body = add_ai_research_to_copy(
                body,
                kind=kind,
                address_mode=self._address_mode(),
                offer_ai=ai_values["offer"],
                sample_url=ai_values["sampleEpisodeUrl"],
                consent_status=ai_values["consentStatus"],
                oral_confirmed=ai_values["oralConfirmed"],
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
        "ZUSTAND News Studio 5.24.4 konnte nicht gestartet werden.\n\n"
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
    sample_url = "https://example.org/zustand-beispielfolge"

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

        sie_body = add_ai_research_to_copy(
            sie_body,
            kind=kind,
            address_mode="Sie",
            offer_ai=True,
            sample_url=sample_url,
            consent_status="Offen",
            oral_confirmed=False,
        )
        du_body = add_ai_research_to_copy(
            du_body,
            kind=kind,
            address_mode="Du",
            offer_ai=True,
            sample_url=sample_url,
            consent_status="Offen",
            oral_confirmed=False,
        )

        assert sie_subject and sie_body
        assert du_subject and du_body
        assert "Guten Tag Prof. Dr.-Ing. Stefanie Weidner" in sie_body
        assert "Hallo Stefanie" in du_body

        if kind != "Telefonleitfaden":
            for body in (sie_body, du_body):
                assert SENDER_PHONE in body
                assert SENDER_MOBILE in body
                assert SENDER_EMAIL in body

        if kind in {
            "Erste E-Mail",
            "Freundliche Erinnerung",
            "Intervieweinladung",
        }:
            assert sample_url in sie_body
            assert "nur mit Ihrer vorherigen ausdrücklichen Zustimmung" in sie_body
            assert "Ohne Ihre ausdrückliche Zustimmung" in sie_body
            assert "nur mit deiner vorherigen ausdrücklichen Zustimmung" in du_body

        if kind == "Telefonleitfaden":
            assert "KI-RECHERCHE" in sie_body
            assert "Ohne Ihre ausdrückliche Zustimmung" in sie_body

        if kind == "Dankeschön":
            assert "KI-Recherche im Gespräch" not in sie_body

    accepted = add_ai_research_to_copy(
        "Text\n\nMit freundlichen Grüßen\nDetlef",
        kind="Intervieweinladung",
        address_mode="Sie",
        offer_ai=True,
        sample_url=sample_url,
        consent_status="Zugestimmt",
        oral_confirmed=True,
    )
    assert "Vielen Dank für Ihre ausdrückliche Zustimmung" in accepted
    assert "Zu Beginn der Aufnahme bestätigen wir" in accepted

    declined = add_ai_research_to_copy(
        "Text\n\nMit freundlichen Grüßen\nDetlef",
        kind="Intervieweinladung",
        address_mode="Sie",
        offer_ai=True,
        sample_url=sample_url,
        consent_status="Abgelehnt",
        oral_confirmed=False,
    )
    assert "findet das Gespräch ohne KI-Unterstützung statt" in declined

    disabled = add_ai_research_to_copy(
        "Unverändert",
        kind="Erste E-Mail",
        address_mode="Sie",
        offer_ai=False,
        sample_url=sample_url,
        consent_status="Offen",
        oral_confirmed=False,
    )
    assert disabled == "Unverändert"

    print(
        "Text-Selbsttest erfolgreich: Sie/Du, Signatur, Beispielfolge, "
        "KI-Wahlmöglichkeit und Zustimmungsstatus geprüft."
    )

def integration_self_test() -> None:
    """Prüft auf dem Zielrechner zusätzlich die echte eingebettete 5.23-Kette."""
    text_self_test()
    base_module = load_base_module()
    project_root = base_module.find_project_root()
    os.environ["ZUSTAND_PROJECT_ROOT"] = str(project_root)

    with tempfile.TemporaryDirectory(prefix="zustand_studio_5244_test_") as temporary:
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

    if "--scroll-self-test" in sys.argv:
        scroll_layout_self_test()
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
        with tempfile.TemporaryDirectory(prefix="zustand_studio_5244_") as temporary:
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
                "News Studio 5.24.4 – Startfehler",
                f"{type(exc).__name__}: {exc}\n\n"
                f"Fehlerbericht:\n{ERROR_LOG}",
            )
        except Exception:
            pass
        print(f"News Studio 5.24.4 – Startfehler: {exc}", file=sys.stderr)
        print(f"Fehlerbericht: {ERROR_LOG}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
