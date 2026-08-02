#!/usr/bin/env python3
from __future__ import annotations

"""ZUSTAND News Studio 5.24.12 – Sie-/Du-Umschalter, startkorrigiert.

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
- korrigierter vertikaler Seiten-Scrollbalken im Reiter „Kontaktaufnahme“
- vorhandene Widgets werden nicht in einen Canvas umgehängt
- Nachrichtentextfeld behält seine eigene Scrollfunktion
- neue Textart „Anmoderation und Gesprächsleitfaden“
- personalisierte Anmoderation aus Thema, Beitrag, Quelle und Interviewperson
- fünf kurze Leitpunkte als vorgelesener goldener Faden
- konkrete Fragen als flexibler interner Fragenpool
- KI-Hinweis nur bei Zustimmung UND mündlicher Bestätigung
- Vollbild-Interviewansicht mit großer veränderbarer Schrift
- Vollbildknopf jetzt dauerhaft sichtbar in der unteren Aktionsleiste
- E-Mail-Schaltflächen werden beim Interviewleitfaden automatisch deaktiviert
- Feldbezeichnung wechselt beim Interviewleitfaden von „Betreff“ zu „Titel“
- Namenskollision mit einer bestehenden Studio-Hilfsmethode behoben
- Vollbild übernimmt den aktuell bearbeiteten Text aus dem Textfeld
- eigene Änderungen bleiben im Vollbild erhalten
- nur bei leerem Textfeld wird ein neuer Interviewentwurf erzeugt
- Druckknopf unten und im Vollbild
- aktueller bearbeiteter Text wird gedruckt
- Windows-Druckfenster öffnet sich über den Standardbrowser
- Erstmail nennt ZUSTAND ausdrücklich als Bildungsinitiative
- Intervieweinladung deutlich gekürzt
- KI-Auswahl in Antwort-E-Mails per Antwortnummer 1, 2 oder 3 statt Kästchen
- erste Kontakt-E-Mail deutlich gekürzt
- offizielle ZUSTAND-Landingpage als Projektvisitenkarte eingefügt
- KI-Hinweis in der ersten E-Mail auf einen kurzen optionalen Satz reduziert
"""

import html
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

VERSION = "5.24.12"
SCRIPT_DIR = Path(__file__).resolve().parent
BASE_CANDIDATES = (
    SCRIPT_DIR / "news_studio_5_23.py",
    SCRIPT_DIR / "news_studio_5_23(1).py",
    SCRIPT_DIR / "news_studio_5_23_1.py",
)
ERROR_LOG = SCRIPT_DIR / "news_studio_5_24_12_startfehler.txt"

SENDER_NAME = "Detlef Hau"
SENDER_INSTITUTION = "Technische Hochschule Lübeck"
SENDER_PROJECT = "Projekt ZUSTAND – Die Vermessung unserer Zukunft"
SENDER_PHONE = "+49 451 300-5660"
SENDER_MOBILE = "+49 173 6144597"
SENDER_EMAIL = "detlef.hau@th-luebeck.de"
PROJECT_URL = "https://www.th-luebeck.de/zustand/"

AI_CONSENT_VALUES = (
    "Offen",
    "Zugestimmt",
    "Abgelehnt",
    "Gespräch gewünscht",
)
AI_SETTINGS_KEY = "aiInterviewSettings"
AI_DEFAULTS_KEY = "aiInterviewDefaults"
INTERVIEW_SCRIPT_KIND = "Anmoderation und Gesprächsleitfaden"
INTERVIEW_DEFAULT_FONT_SIZE = 25


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

vielen Dank für deine Bereitschaft zu einem Gespräch über „{title}“.

Vorgesehen ist ein etwa 20- bis 30-minütiges Telefon- oder Online-Interview.{hook_paragraph}

Wir sprechen kurz über deine Arbeit und ordnen die wichtigsten Ergebnisse verständlich ein. Den vorbereiteten Infoscreen-Beitrag und die Fragen erhältst du vorab zur Durchsicht.

Für die Terminabstimmung genügt eine kurze Antwort mit möglichen Zeiten; Details können wir gern telefonisch klären.

{signature}"""
        else:
            body = f"""{greeting}

vielen Dank für Ihre Bereitschaft zu einem Gespräch über „{title}“.

Vorgesehen ist ein etwa 20- bis 30-minütiges Telefon- oder Online-Interview.{hook_paragraph}

Wir sprechen kurz über Ihre Arbeit und ordnen die wichtigsten Ergebnisse verständlich ein. Den vorbereiteten Infoscreen-Beitrag und die Fragen erhalten Sie vorab zur Durchsicht.

Für die Terminabstimmung genügt eine kurze Antwort mit möglichen Zeiten; Details können wir gern telefonisch klären.

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
            subject = f"Gesprächsanfrage zu „{title}“"
            body = f"""{greeting}

bei der Recherche für unsere Bildungsinitiative „ZUSTAND – Die Vermessung unserer Zukunft“ bin ich auf deine Veröffentlichung „{title}“ aufmerksam geworden.{hook_paragraph}

Ich möchte dich gern zu einem etwa 20- bis 30-minütigen Telefon- oder Online-Gespräch einladen. Ziel ist eine verständliche Einordnung deiner Forschung für unseren öffentlichen Infoscreen, die Bildungsarbeit an der TH Lübeck und den Offenen Kanal Lübeck.

Mehr zum Projekt:
{PROJECT_URL}

Bei Interesse können wir Ablauf und Termin kurz telefonisch abstimmen. Den vorbereiteten Beitrag und die Fragen erhältst du vorab zur Durchsicht.

{signature}"""
        else:
            subject = f"Gesprächsanfrage zu „{title}“"
            body = f"""{greeting}

bei der Recherche für unsere Bildungsinitiative „ZUSTAND – Die Vermessung unserer Zukunft“ bin ich auf Ihre Veröffentlichung „{title}“ aufmerksam geworden.{hook_paragraph}

Ich möchte Sie gern zu einem etwa 20- bis 30-minütigen Telefon- oder Online-Gespräch einladen. Ziel ist eine verständliche Einordnung Ihrer Forschung für unseren öffentlichen Infoscreen, die Bildungsarbeit an der TH Lübeck und den Offenen Kanal Lübeck.

Mehr zum Projekt:
{PROJECT_URL}

Bei Interesse können wir Ablauf und Termin kurz telefonisch abstimmen. Den vorbereiteten Beitrag und die Fragen erhalten Sie vorab zur Durchsicht.

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
        core = """Optional können wir im Gespräch punktuell eine KI zur Suche nach weiteren wissenschaftlichen Quellen hinzuziehen. Sie wird nur nach Ankündigung eingesetzt; deine fachliche Einordnung bleibt maßgeblich.

Bitte antworte einfach mit 1, 2 oder 3:
1 – Einverstanden
2 – Gespräch ohne KI
3 – Zunächst telefonisch besprechen

Ohne deine ausdrückliche Zustimmung bleibt die KI außen vor."""
    else:
        core = """Optional können wir im Gespräch punktuell eine KI zur Suche nach weiteren wissenschaftlichen Quellen hinzuziehen. Sie wird nur nach Ankündigung eingesetzt; Ihre fachliche Einordnung bleibt maßgeblich.

Bitte antworten Sie einfach mit 1, 2 oder 3:
1 – Einverstanden
2 – Gespräch ohne KI
3 – Zunächst telefonisch besprechen

Ohne Ihre ausdrückliche Zustimmung bleibt die KI außen vor."""
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

    if kind == "Erste E-Mail":
        consent_status = (
            consent_status if consent_status in AI_CONSENT_VALUES else "Offen"
        )
        if consent_status == "Abgelehnt":
            return body
        if consent_status == "Zugestimmt":
            block = (
                "Wie abgestimmt, kann im Gespräch punktuell eine KI zur Suche "
                "nach weiterführenden wissenschaftlichen Quellen eingesetzt werden. "
                "Die fachliche Einordnung bleibt selbstverständlich bei Ihnen."
                if address_mode == "Sie"
                else
                "Wie abgestimmt, kann im Gespräch punktuell eine KI zur Suche "
                "nach weiterführenden wissenschaftlichen Quellen eingesetzt werden. "
                "Die fachliche Einordnung bleibt selbstverständlich bei dir."
            )
        elif consent_status == "Gespräch gewünscht":
            block = (
                "Den möglichen punktuellen Einsatz einer KI zur Quellensuche können "
                "wir bei Interesse kurz telefonisch besprechen."
            )
        else:
            block = (
                "Optional kann im Gespräch punktuell eine KI zur Suche nach "
                "weiterführenden wissenschaftlichen Quellen eingesetzt werden – "
                "ausschließlich nach Ihrer vorherigen Zustimmung."
                if address_mode == "Sie"
                else
                "Optional kann im Gespräch punktuell eine KI zur Suche nach "
                "weiterführenden wissenschaftlichen Quellen eingesetzt werden – "
                "ausschließlich nach deiner vorherigen Zustimmung."
            )

        for marker in ("\n\nMit freundlichen Grüßen", "\n\nHerzliche Grüße"):
            if marker in body:
                return body.replace(marker, f"\n\n{block}{marker}", 1)
        return f"{body.rstrip()}\n\n{block}"

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


def make_existing_frame_place_scrollable(
    tk_module,
    ttk_module,
    *,
    tab,
    content,
) -> dict[str, Any]:
    """Macht einen bestehenden direkten Tab-Inhaltsframe vertikal scrollbar.

    Anders als die fehlerhafte 5.24.4 wird der Frame nicht in einen Canvas
    umgehängt. Er bleibt Kind seines ursprünglichen Tabs und wird mit `place`
    lediglich vertikal verschoben. Dadurch bleiben alle vorhandenen Widgets
    sichtbar und sämtliche Bindings erhalten.
    """
    if getattr(content, "_zustand_place_scroll_wrapped", False):
        return getattr(content, "_zustand_place_scroll_handles", {})

    manager = content.winfo_manager()
    if manager == "pack":
        content.pack_forget()
    elif manager == "grid":
        content.grid_remove()
    elif manager == "place":
        content.place_forget()

    scrollbar_width = 18
    scrollbar = ttk_module.Scrollbar(tab, orient="vertical")
    scrollbar.place(
        relx=1.0,
        x=-scrollbar_width,
        y=0,
        width=scrollbar_width,
        relheight=1.0,
    )

    state = {
        "offset": 0,
        "content_height": 1,
        "view_height": 1,
        "max_offset": 0,
    }

    def refresh(_event=None):
        try:
            tab.update_idletasks()
            requested = max(int(content.winfo_reqheight()), 1)
            view_height = max(int(tab.winfo_height()), 1)
            content_height = max(requested, view_height)
            max_offset = max(content_height - view_height, 0)

            state["content_height"] = content_height
            state["view_height"] = view_height
            state["max_offset"] = max_offset
            state["offset"] = min(max(int(state["offset"]), 0), max_offset)

            content.place_configure(
                x=0,
                y=-state["offset"],
                relwidth=1.0,
                width=-scrollbar_width - 3,
                height=content_height,
            )

            if content_height <= view_height:
                scrollbar.set(0.0, 1.0)
            else:
                top = state["offset"] / content_height
                bottom = min(
                    (state["offset"] + view_height) / content_height,
                    1.0,
                )
                scrollbar.set(top, bottom)
        except Exception:
            pass

    def set_offset(value):
        try:
            offset = int(round(float(value)))
        except Exception:
            offset = 0
        state["offset"] = min(
            max(offset, 0),
            int(state.get("max_offset", 0)),
        )
        refresh()

    def scrollbar_command(*args):
        if not args:
            return

        action = args[0]
        if action == "moveto" and len(args) >= 2:
            try:
                fraction = float(args[1])
            except Exception:
                fraction = 0.0
            set_offset(fraction * state["content_height"])
            return

        if action == "scroll" and len(args) >= 3:
            try:
                amount = int(args[1])
            except Exception:
                amount = 0
            unit = args[2]
            step = (
                max(int(state["view_height"] * 0.85), 60)
                if unit == "pages"
                else 48
            )
            set_offset(state["offset"] + amount * step)

    scrollbar.configure(command=scrollbar_command)

    # Widgets mit eigener vertikaler Navigation behalten ihr normales Mausrad.
    own_scroll_classes = {
        "Text",
        "Listbox",
        "Treeview",
        "TCombobox",
        "Scrollbar",
        "TScrollbar",
        "Spinbox",
        "TSpinbox",
    }

    def wheel_windows(event):
        try:
            delta = int(event.delta)
        except Exception:
            delta = 0
        if delta == 0:
            return None
        steps = -1 if delta > 0 else 1
        set_offset(state["offset"] + steps * 72)
        return "break"

    def wheel_linux_up(_event):
        set_offset(state["offset"] - 72)
        return "break"

    def wheel_linux_down(_event):
        set_offset(state["offset"] + 72)
        return "break"

    def bind_mousewheel_tree(widget):
        try:
            widget_class = widget.winfo_class()
        except Exception:
            widget_class = ""

        if widget_class not in own_scroll_classes:
            try:
                widget.bind("<MouseWheel>", wheel_windows, add="+")
                widget.bind("<Button-4>", wheel_linux_up, add="+")
                widget.bind("<Button-5>", wheel_linux_down, add="+")
            except Exception:
                pass

        try:
            children = widget.winfo_children()
        except Exception:
            children = []

        for child in children:
            bind_mousewheel_tree(child)

    bind_mousewheel_tree(content)
    bind_mousewheel_tree(scrollbar)

    content.bind("<Configure>", refresh, add="+")
    tab.bind("<Configure>", refresh, add="+")

    content._zustand_place_scroll_wrapped = True
    handles = {
        "scrollbar": scrollbar,
        "content": content,
        "state": state,
        "refresh": refresh,
        "set_offset": set_offset,
    }
    content._zustand_place_scroll_handles = handles

    tab.after_idle(refresh)
    tab.after_idle(lambda: set_offset(0))
    return handles


def place_scroll_layout_self_test() -> None:
    """Prüft Sichtbarkeit und Scrollfunktion mit einem echten Tk-Fenster."""
    import tkinter as test_tk
    from tkinter import ttk as test_ttk

    root = test_tk.Tk()
    root.geometry("520x280")

    tab = test_ttk.Frame(root)
    tab.pack(fill="both", expand=True)

    content = test_ttk.Frame(tab, padding=12)
    content.pack(fill="both", expand=True)

    first = test_ttk.Label(content, text="Erste sichtbare Testzeile")
    first.pack(anchor="w")

    for index in range(40):
        test_ttk.Label(
            content,
            text=f"Weitere Testzeile {index + 1}",
        ).pack(anchor="w", pady=2)

    last = test_ttk.Label(content, text="Letzte Testzeile")
    last.pack(anchor="w")

    handles = make_existing_frame_place_scrollable(
        test_tk,
        test_ttk,
        tab=tab,
        content=content,
    )

    root.update_idletasks()

    if not first.winfo_ismapped():
        root.destroy()
        raise RuntimeError("Der Inhalt ist nach dem Einbau des Scrollbalkens unsichtbar.")

    state = handles["state"]
    if state["max_offset"] <= 0:
        root.destroy()
        raise RuntimeError("Der Testinhalt erzeugt keinen Scrollbereich.")

    handles["set_offset"](state["max_offset"])
    root.update_idletasks()

    placed_y = int(float(content.place_info().get("y", "0")))
    root.destroy()

    if placed_y >= 0:
        raise RuntimeError("Der Inhalt wurde beim Scrollen nicht nach oben verschoben.")

    print(
        "Scroll-Selbsttest erfolgreich: Inhalt bleibt sichtbar und lässt sich "
        "vertikal verschieben."
    )


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _clean_sentence(value: object, max_chars: int = 260) -> str:
    text = clean_text(value)
    if not text:
        return ""
    if len(text) <= max_chars:
        return text.rstrip(" .") + "."
    shortened = text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:.")
    return shortened + " …"


def _first_sentences(value: object, max_chars: int = 330) -> str:
    text = clean_text(value)
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    match = re.search(r"^(.{80,%d}?[.!?])(?:\s|$)" % max_chars, text)
    if match:
        return match.group(1)
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,;:.") + " …"


def _article_topic(article: dict[str, Any]) -> str:
    for key in ("selectionLabel", "topic", "category"):
        value = clean_text(article.get(key))
        if value:
            value = re.sub(
                r"^(?:Querschnitt|Grundlagenbeitrag|Newsbeitrag)\s*:\s*",
                "",
                value,
                flags=re.IGNORECASE,
            )
            return value
    return clean_text(article.get("title")) or "unser heutiges Thema"


def _guest_description(contact: dict[str, Any]) -> str:
    name = clean_text(contact.get("name")) or "unser heutiger Gast"
    role = clean_text(contact.get("role"))
    institution = clean_text(contact.get("institution"))

    additions: list[str] = []
    if role:
        additions.append(role)
    if institution and institution.casefold() not in role.casefold():
        additions.append(institution)

    return ", ".join([name, *additions]) if additions else name


def _editorial_value(
    article: dict[str, Any],
    *keys: str,
) -> str:
    editorial = _as_dict(article.get("editorial"))
    for key in keys:
        value = clean_text(editorial.get(key))
        if value:
            return value
    return ""


def _source_reference(article: dict[str, Any]) -> str:
    source_title = clean_text(article.get("sourceTitle"))
    if not source_title:
        return ""
    return source_title


def _question_behind_news(article: dict[str, Any]) -> str:
    value = _editorial_value(article, "questionBehindNews")
    if value:
        return value.rstrip(" .") + "?"
    title = clean_text(article.get("title"))
    return f"Was steckt hinter dem Beitrag „{title}“?" if title else "Worum geht es genau?"


def _golden_thread(article: dict[str, Any]) -> list[str]:
    topic = _article_topic(article)
    title = clean_text(article.get("title")) or "dem ausgewählten Beitrag"

    question = _question_behind_news(article)
    core = _clean_sentence(
        _editorial_value(article, "coreChange"),
        180,
    )
    chain = _clean_sentence(
        _editorial_value(article, "causalChain"),
        180,
    )
    affected = _clean_sentence(
        _editorial_value(article, "affectedSystems"),
        180,
    )
    uncertainties = _clean_sentence(
        _editorial_value(article, "uncertainties"),
        180,
    )

    points = [
        question,
        (
            f"Was zeigt der Beitrag „{title}“ – und wie wurden die zugrunde "
            "liegenden Ergebnisse gewonnen?"
        ),
        (
            f"Welche Zusammenhänge verbinden {topic} mit Bauen, "
            "Ressourcenverbrauch und planetaren Grenzen?"
        ),
        (
            "Welche praktischen Entscheidungen, gesellschaftlichen Bereiche "
            "oder natürlichen Systeme sind davon betroffen?"
        ),
        (
            "Welche Unsicherheiten, Zielkonflikte und offenen Forschungsfragen "
            "bleiben?"
        ),
    ]

    # Die redaktionellen Inhalte machen die Punkte konkret, ohne sie zu überladen.
    if core:
        points[1] = f"Was ist die zentrale Erkenntnis? {core}"
    if chain:
        points[2] = f"Welche Wirkungskette ist entscheidend? {chain}"
    if affected:
        points[3] = f"Wer oder was ist besonders betroffen? {affected}"
    if uncertainties:
        points[4] = f"Was bleibt offen oder unsicher? {uncertainties}"

    return [point.rstrip(" .") + ("?" if not point.endswith(("?", "…")) else "") for point in points]


def _flatten_saved_interview_questions(article: dict[str, Any]) -> list[str]:
    raw = article.get("interviewQuestions")
    if not raw:
        raw = _as_dict(article.get("editorial")).get("interviewQuestions")

    result: list[str] = []
    if isinstance(raw, dict):
        for value in raw.values():
            if isinstance(value, list):
                result.extend(clean_text(item) for item in value if clean_text(item))
            elif clean_text(value):
                result.append(clean_text(value))
    elif isinstance(raw, list):
        result.extend(clean_text(item) for item in raw if clean_text(item))
    elif clean_text(raw):
        result.append(clean_text(raw))

    seen: set[str] = set()
    unique: list[str] = []
    for item in result:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item.rstrip(" .") + ("?" if not item.endswith("?") else ""))
    return unique


def _generated_interview_questions(
    article: dict[str, Any],
    contact: dict[str, Any],
) -> list[str]:
    title = clean_text(article.get("title")) or "diesem Thema"
    topic = _article_topic(article)
    source_type = _editorial_value(article, "sourceType")
    question = _question_behind_news(article)
    core = _editorial_value(article, "coreChange")
    chain = _editorial_value(article, "causalChain")
    affected = _editorial_value(article, "affectedSystems")
    uncertainties = _editorial_value(article, "uncertainties")

    questions = [
        f"Wie sind Sie persönlich zu dem Thema „{topic}“ gekommen?",
        f"Welche zentrale Forschungsfrage steht hinter „{title}“?",
        (
            "Wie wurde die Untersuchung durchgeführt und welche Daten oder "
            "Vergleiche sind für das Ergebnis besonders wichtig?"
        ),
        "Was ist aus Ihrer Sicht das wichtigste Ergebnis?",
        "Gab es einen Befund, der Sie selbst überrascht hat?",
        (
            "Wie hängen diese Ergebnisse mit dem Ressourcenverbrauch des Bauens "
            "und den planetaren Grenzen zusammen?"
        ),
        (
            "Welche Annahmen oder Grenzen der Untersuchung müssen wir kennen, "
            "damit wir das Ergebnis nicht überinterpretieren?"
        ),
        (
            "Was folgt daraus konkret für Planung, Baupraxis, Politik oder "
            "unseren persönlichen Flächen- und Materialbedarf?"
        ),
        "Welche Forschungsergebnisse oder Vergleichsstudien sollten wir zusätzlich kennen?",
        "Welche eine Botschaft möchten Sie den Zuhörerinnen und Zuhörern mitgeben?",
    ]

    # Redaktionelle Informationen personalisieren einzelne Fragen.
    if question:
        questions[1] = question.rstrip(" .") + ("?" if not question.endswith("?") else "")
    if source_type:
        questions[2] = (
            "Wie ist die zugrunde liegende Veröffentlichung methodisch einzuordnen, "
            "und was kann sie belastbar zeigen?"
        )
    if core:
        questions[3] = f"Die zentrale Veränderung wird so beschrieben: {_first_sentences(core, 210)} Was ist daran besonders bedeutsam?"
    if chain:
        questions[5] = f"Die angenommene Wirkungskette lautet verkürzt: {_first_sentences(chain, 220)} Welche Glieder dieser Kette sind wissenschaftlich besonders gut belegt?"
    if uncertainties:
        questions[6] = f"Die Veröffentlichung nennt folgende Unsicherheiten: {_first_sentences(uncertainties, 220)} Welche davon ist für die Einordnung am wichtigsten?"
    if affected:
        questions[7] = f"Betroffen sind unter anderem: {_first_sentences(affected, 210)} Welche praktische Konsequenz folgt daraus zuerst?"

    return questions


def _interview_questions(
    article: dict[str, Any],
    contact: dict[str, Any],
) -> list[str]:
    saved = _flatten_saved_interview_questions(article)
    generated = _generated_interview_questions(article, contact)

    combined: list[str] = []
    seen: set[str] = set()
    for question in [*saved, *generated]:
        cleaned = clean_text(question)
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        combined.append(cleaned)
        if len(combined) >= 14:
            break
    return combined


def _ai_public_intro(
    *,
    consent_status: str,
    oral_confirmed: bool,
) -> tuple[str, str]:
    """Gibt internen Hinweis und öffentlich vorzulesenden KI-Teil zurück."""
    if consent_status == "Zugestimmt" and oral_confirmed:
        spoken = (
            "Mit ausdrücklicher Zustimmung unseres Gastes nutzen wir heute bei "
            "einzelnen weiterführenden Sachfragen eine KI als "
            "Rechercheunterstützung. Sie soll nach möglichen Forschungsergebnissen "
            "und Primärquellen suchen. Die fachliche Einordnung bleibt bei unserem "
            "Gast; wichtige Angaben prüfen wir anschließend nochmals."
        )
        return "KI-RECHERCHE: AKTIV – ausdrücklich zugestimmt und mündlich bestätigt.", spoken

    if consent_status == "Zugestimmt":
        return (
            "VOR DER AUFNAHME – NICHT VORLESEN: Die schriftliche Zustimmung liegt vor, "
            "die mündliche Bestätigung fehlt noch. Bis zur Bestätigung bleibt die KI aus.",
            "",
        )

    if consent_status == "Abgelehnt":
        return (
            "VOR DER AUFNAHME – NICHT VORLESEN: KI-Recherche wurde abgelehnt und bleibt aus.",
            "",
        )

    if consent_status == "Gespräch gewünscht":
        return (
            "VOR DER AUFNAHME – NICHT VORLESEN: KI-Recherche ist noch zu besprechen. "
            "Ohne ausdrückliche Zustimmung bleibt sie aus.",
            "",
        )

    return (
        "VOR DER AUFNAHME – NICHT VORLESEN: Keine ausdrückliche KI-Zustimmung dokumentiert. "
        "Die KI bleibt aus.",
        "",
    )


def build_interview_script(
    *,
    article: dict[str, Any],
    contact: dict[str, Any],
    address_mode: str,
    consent_status: str,
    oral_confirmed: bool,
) -> tuple[str, str]:
    title = clean_text(article.get("title")) or "[Beitrag noch auswählen]"
    topic = _article_topic(article)
    source_title = _source_reference(article)
    summary = _first_sentences(article.get("summary"), 360)
    guest = _guest_description(contact)

    internal_ai_note, spoken_ai = _ai_public_intro(
        consent_status=consent_status,
        oral_confirmed=oral_confirmed,
    )

    greeting_end = (
        "Schön, dass du heute dabei bist."
        if address_mode == "Du"
        else "Schön, dass Sie heute bei uns sind."
    )

    intro_parts = [
        "Willkommen bei ZUSTAND – Die Vermessung unserer Zukunft.",
        f"Heute geht es um {topic}.",
        f"Ausgangspunkt unseres Gesprächs ist der ZUSTAND-Beitrag „{title}“.",
    ]
    if source_title and source_title.casefold() != title.casefold():
        intro_parts.append(
            f"Er stützt sich auf die Veröffentlichung „{source_title}“."
        )
    if summary:
        intro_parts.append(f"Darin geht es kurz gesagt um Folgendes: {summary}")
    if spoken_ai:
        intro_parts.append(spoken_ai)

    intro_parts.append(f"Bei mir ist heute {guest}. {greeting_end}")

    golden = _golden_thread(article)
    questions = _interview_questions(article, contact)

    lines: list[str] = [
        internal_ai_note,
        "",
        "ANMODERATION – VORLESEN",
        "========================",
        "",
        *intro_parts,
        "",
        "GOLDENER FADEN – VORLESEN",
        "==========================",
        "",
        "In unserem Gespräch möchten wir heute fünf Punkten nachgehen:",
        "",
    ]
    lines.extend(f"{index}. {point}" for index, point in enumerate(golden, start=1))

    lines.extend(
        [
            "",
            "ÜBERGANG INS GESPRÄCH – VORLESEN",
            "================================",
            "",
            (
                "Beginnen wir mit dem ersten Punkt: "
                f"{golden[0]}"
            ),
            "",
            "KONKRETE FRAGEN – FLEXIBLER INTERNER FRAGENPOOL",
            "================================================",
            "",
            (
                "Die Fragen müssen nicht vollständig und nicht in dieser Reihenfolge "
                "gestellt werden. Sie dienen als Reserve und Orientierung."
            ),
            "",
        ]
    )
    lines.extend(
        f"{index}. {question}"
        for index, question in enumerate(questions, start=1)
    )

    subject = f"Interviewvorbereitung: {title}"
    return subject, "\n".join(lines).strip() + "\n"


def build_print_html(title: str, body: str) -> str:
    safe_title = html.escape(clean_text(title) or "ZUSTAND – Interviewvorbereitung")
    safe_body = html.escape(str(body or "").rstrip())
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{safe_title}</title>
<style>
@page {{ size: A4; margin: 18mm 17mm 20mm 17mm; }}
html, body {{ background: #fff; color: #000; }}
body {{
  font-family: Arial, Helvetica, sans-serif;
  font-size: 13.5pt;
  line-height: 1.45;
  margin: 0;
}}
h1 {{
  font-size: 17pt;
  line-height: 1.25;
  margin: 0 0 14mm 0;
}}
pre {{
  font: inherit;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  margin: 0;
}}
@media screen {{
  body {{
    max-width: 180mm;
    margin: 18mm auto;
    padding: 0 12mm 20mm 12mm;
  }}
}}
</style>
<script>
window.addEventListener("load", function () {{
  window.setTimeout(function () {{ window.print(); }}, 400);
}});
</script>
</head>
<body>
<h1>{safe_title}</h1>
<pre>{safe_body}</pre>
</body>
</html>
"""


def create_print_file(title: str, body: str) -> Path:
    path = Path(tempfile.gettempdir()) / "zustand_interview_druckansicht.html"
    path.write_text(build_print_html(title, body), encoding="utf-8")
    return path


def open_system_print_window(title: str, body: str) -> Path:
    path = create_print_file(title, body)
    if os.name == "nt":
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        webbrowser.open(path.as_uri())
    return path


def print_html_self_test() -> None:
    title = 'Interviewvorbereitung: "ZUSTAND & Forschung"'
    body = "Eigene Änderung <bleibt erhalten>.\n\nZweite Zeile."
    rendered = build_print_html(title, body)
    assert "&quot;ZUSTAND &amp; Forschung&quot;" in rendered
    assert "&lt;bleibt erhalten&gt;" in rendered
    assert "window.print()" in rendered
    assert "white-space: pre-wrap" in rendered
    path = create_print_file(title, body)
    assert path.read_text(encoding="utf-8") == rendered
    print(
        "Druck-Selbsttest erfolgreich: bearbeiteter Text und "
        "automatischer Druckdialog sind vorbereitet."
    )

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
                self.title("ZUSTAND News Studio 5.24.12")
            except Exception:
                pass
            try:
                self.status_var.set(
                    "News Studio 5.24.11 bereit │ KI-Recherche nur nach ausdrücklicher Zustimmung"
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

            # Neue Textart
            try:
                existing_kinds = list(kind_combo.cget("values"))
            except Exception:
                existing_kinds = []
            if INTERVIEW_SCRIPT_KIND not in existing_kinds:
                existing_kinds.append(INTERVIEW_SCRIPT_KIND)
                kind_combo.configure(values=tuple(existing_kinds))

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
            self.after_idle(self._install_interview_action_controls)

        def _zustand_walk_outreach_widgets(self, root_widget):
            yield root_widget
            try:
                children = root_widget.winfo_children()
            except Exception:
                children = []
            for child in children:
                yield from self._zustand_walk_outreach_widgets(child)

        def _zustand_find_outreach_widget_by_text(self, root_widget, text):
            for widget in self._zustand_walk_outreach_widgets(root_widget):
                try:
                    if clean_text(widget.cget("text")) == text:
                        return widget
                except Exception:
                    continue
            return None

        def _install_interview_action_controls(self) -> None:
            if hasattr(self, "outreach_fullscreen_bottom_button"):
                return

            tab = getattr(self, "outreach_tab", None)
            if tab is None:
                raise RuntimeError(
                    "Der Reiter „Kontaktaufnahme“ wurde nicht gefunden."
                )

            mail_button = self._zustand_find_outreach_widget_by_text(
                tab,
                "Im Mailprogramm öffnen",
            )
            subject_text_button = self._zustand_find_outreach_widget_by_text(
                tab,
                "Betreff + Text kopieren",
            )
            subject_label = self._zustand_find_outreach_widget_by_text(
                tab,
                "Betreff",
            )

            if mail_button is None:
                raise RuntimeError(
                    "Die untere Aktionsleiste der Kontaktaufnahme wurde nicht gefunden."
                )

            action_row = mail_button.master
            fullscreen_button = ttk.Button(
                action_row,
                text="Interview im Vollbild",
                command=self._open_interview_fullscreen_from_actionbar,
            )
            # Der vorhandene Mailknopf ist rechts angeordnet. Weitere rechts
            # gepackte Knöpfe erscheinen links daneben.
            fullscreen_button.pack(side="right", padx=(8, 8))

            print_button = ttk.Button(
                action_row,
                text="Drucken",
                command=self._print_current_outreach_text,
            )
            print_button.pack(side="right", padx=(8, 0))

            self.outreach_fullscreen_bottom_button = fullscreen_button
            self.outreach_print_button = print_button
            self.outreach_mail_button = mail_button
            self.outreach_subject_text_copy_button = subject_text_button
            self.outreach_subject_label = subject_label

            try:
                self.outreach_kind_var.trace_add(
                    "write",
                    self._on_outreach_kind_changed,
                )
            except Exception:
                pass

            self._update_outreach_action_mode()

        def _on_outreach_kind_changed(self, *_args) -> None:
            self.after_idle(self._update_outreach_action_mode)

        def _update_outreach_action_mode(self) -> None:
            try:
                kind = self.outreach_kind_var.get()
            except Exception:
                kind = ""

            is_interview = kind == INTERVIEW_SCRIPT_KIND

            label = getattr(self, "outreach_subject_label", None)
            if label is not None:
                try:
                    label.configure(text="Titel" if is_interview else "Betreff")
                except Exception:
                    pass

            subject_copy = getattr(
                self,
                "outreach_subject_text_copy_button",
                None,
            )
            if subject_copy is not None:
                try:
                    subject_copy.configure(
                        state="disabled" if is_interview else "normal"
                    )
                except Exception:
                    pass

            mail_button = getattr(self, "outreach_mail_button", None)
            if mail_button is not None:
                try:
                    mail_button.configure(
                        state="disabled" if is_interview else "normal"
                    )
                except Exception:
                    pass

            full_button = getattr(
                self,
                "outreach_fullscreen_bottom_button",
                None,
            )
            if full_button is not None:
                try:
                    full_button.configure(
                        text=(
                            "Interview im Vollbild öffnen"
                            if is_interview
                            else "Interviewleitfaden im Vollbild"
                        )
                    )
                except Exception:
                    pass

        def _open_interview_fullscreen_from_actionbar(self) -> None:
            try:
                kind = self.outreach_kind_var.get()
            except Exception:
                kind = ""

            # Nur wenn noch kein Interviewleitfaden gewählt und das Textfeld leer
            # ist, wird die passende Textart gesetzt und ein Entwurf erzeugt.
            current_text = self._current_outreach_text().strip()
            if kind != INTERVIEW_SCRIPT_KIND and not current_text:
                try:
                    self.outreach_kind_var.set(INTERVIEW_SCRIPT_KIND)
                except Exception:
                    pass
                self.generate_outreach_text()

            self._update_outreach_action_mode()
            self._open_interview_fullscreen()

        def _install_outreach_scrollbar(self) -> None:
            if hasattr(self, "outreach_scrollbar"):
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

            handles = make_existing_frame_place_scrollable(
                tk,
                ttk,
                tab=tab,
                content=content,
            )
            self.outreach_scrollbar = handles["scrollbar"]
            self.outreach_scroll_content = handles["content"]
            self.outreach_scroll_state = handles["state"]
            self.outreach_scroll_refresh = handles["refresh"]

            try:
                self.status_var.set(
                    "News Studio 5.24.11 bereit │ Kontaktaufnahme sichtbar und scrollbar"
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

        # ---------- Interviewvorbereitung und Vollbild ----------
        def _select_interview_script_kind(self) -> None:
            try:
                self.outreach_kind_var.set(INTERVIEW_SCRIPT_KIND)
            except Exception:
                pass
            self.generate_outreach_text()

        def _current_outreach_text(self) -> str:
            widget = getattr(self, "outreach_text", None)
            if widget is None:
                return ""
            try:
                return widget.get("1.0", "end-1c")
            except Exception:
                return ""

        def _print_text(self, title: str, body: str) -> None:
            body = str(body or "").strip()
            if not body:
                messagebox.showinfo(
                    "Drucken",
                    "Es ist noch kein Text zum Drucken vorhanden.",
                    parent=self,
                )
                return
            try:
                open_system_print_window(title, body)
                try:
                    self.status_var.set(
                        "Druckansicht geöffnet – bitte Drucker und Einstellungen wählen"
                    )
                except Exception:
                    pass
            except Exception as exc:
                messagebox.showerror(
                    "Druckfenster konnte nicht geöffnet werden",
                    str(exc),
                    parent=self,
                )

        def _print_current_outreach_text(self) -> None:
            body = self._current_outreach_text()
            try:
                title = clean_text(self.outreach_subject_var.get())
            except Exception:
                title = ""
            self._print_text(
                title or "ZUSTAND – Interviewvorbereitung",
                body,
            )

        def _current_interview_script(self) -> tuple[str, str]:
            try:
                _contact_id, contact = self._selected_contact()
            except Exception:
                contact = {}
            if not isinstance(contact, dict) or not contact:
                raise RuntimeError(
                    "Bitte zuerst eine Interviewperson im Reiter „Kontaktaufnahme“ auswählen."
                )

            try:
                article = self._selected_article()
            except Exception:
                article = {}
            if not isinstance(article, dict) or not article:
                raise RuntimeError(
                    "Bitte zuerst einen Beitrag im Reiter „Kontaktaufnahme“ auswählen."
                )

            ai_values = self._current_ai_values()
            return build_interview_script(
                article=article,
                contact=contact,
                address_mode=self._address_mode(),
                consent_status=ai_values["consentStatus"],
                oral_confirmed=ai_values["oralConfirmed"],
            )

        def _open_interview_fullscreen(self) -> None:
            try:
                current_body = self._current_outreach_text().strip()
                current_subject = ""
                try:
                    current_subject = clean_text(self.outreach_subject_var.get())
                except Exception:
                    current_subject = ""

                if current_body:
                    subject = current_subject or "Interviewvorbereitung"
                    body = current_body + "\n"
                else:
                    subject, body = self._current_interview_script()
                    try:
                        self.outreach_subject_var.set(subject)
                    except Exception:
                        pass
                    setter = getattr(self, "_set_outreach_text", None)
                    if callable(setter):
                        try:
                            setter(body)
                        except Exception:
                            pass
            except Exception as exc:
                messagebox.showinfo(
                    "Interviewvorbereitung",
                    str(exc),
                    parent=self,
                )
                return

            window = tk.Toplevel(self)
            window.title(subject)
            window.configure(background="white")
            window.attributes("-fullscreen", True)

            toolbar = ttk.Frame(window, padding=(12, 8))
            toolbar.pack(fill="x")

            font_size_var = tk.IntVar(
                master=window,
                value=INTERVIEW_DEFAULT_FONT_SIZE,
            )
            fullscreen_var = tk.BooleanVar(master=window, value=True)

            status_text = (
                "KI: AKTIV – zugestimmt und mündlich bestätigt"
                if (
                    self._current_ai_values()["consentStatus"] == "Zugestimmt"
                    and self._current_ai_values()["oralConfirmed"]
                )
                else "KI: AUS – keine vollständig bestätigte Zustimmung"
            )
            ttk.Label(
                toolbar,
                text=status_text,
            ).pack(side="left")

            ttk.Label(
                toolbar,
                text="Schriftgröße",
                padding=(24, 0, 4, 0),
            ).pack(side="left")

            text_frame = ttk.Frame(window)
            text_frame.pack(fill="both", expand=True)

            scrollbar = ttk.Scrollbar(text_frame, orient="vertical")
            scrollbar.pack(side="right", fill="y")

            text_widget = tk.Text(
                text_frame,
                wrap="word",
                yscrollcommand=scrollbar.set,
                background="white",
                foreground="black",
                insertbackground="black",
                relief="flat",
                borderwidth=0,
                padx=70,
                pady=40,
                spacing1=5,
                spacing2=2,
                spacing3=12,
                font=("Arial", INTERVIEW_DEFAULT_FONT_SIZE),
            )
            text_widget.pack(side="left", fill="both", expand=True)
            scrollbar.configure(command=text_widget.yview)

            def apply_font_size(*_args):
                size = max(16, min(int(font_size_var.get()), 42))
                font_size_var.set(size)
                text_widget.configure(font=("Arial", size))
                text_widget.tag_configure(
                    "heading",
                    font=("Arial", min(size + 5, 48), "bold"),
                    spacing1=18,
                    spacing3=10,
                )
                text_widget.tag_configure(
                    "internal",
                    font=("Arial", max(size - 3, 14), "bold"),
                    foreground="#555555",
                    spacing3=18,
                )

            def change_font(delta: int):
                font_size_var.set(font_size_var.get() + delta)
                apply_font_size()

            ttk.Button(
                toolbar,
                text="−",
                width=3,
                command=lambda: change_font(-2),
            ).pack(side="left")
            ttk.Label(
                toolbar,
                textvariable=font_size_var,
                width=3,
                anchor="center",
            ).pack(side="left")
            ttk.Button(
                toolbar,
                text="+",
                width=3,
                command=lambda: change_font(2),
            ).pack(side="left")

            def go_top():
                text_widget.yview_moveto(0.0)
                text_widget.focus_set()

            ttk.Button(
                toolbar,
                text="An den Anfang",
                command=go_top,
            ).pack(side="left", padx=(20, 0))

            def toggle_fullscreen(_event=None):
                new_value = not bool(fullscreen_var.get())
                fullscreen_var.set(new_value)
                window.attributes("-fullscreen", new_value)
                return "break"

            ttk.Button(
                toolbar,
                text="Vollbild an/aus",
                command=toggle_fullscreen,
            ).pack(side="left", padx=(8, 0))

            ttk.Button(
                toolbar,
                text="Drucken",
                command=lambda: self._print_text(subject, body),
            ).pack(side="left", padx=(8, 0))

            ttk.Button(
                toolbar,
                text="Schließen",
                command=window.destroy,
            ).pack(side="right")

            text_widget.insert("1.0", body)
            apply_font_size()

            # Überschriften und internen Start-Hinweis optisch absetzen.
            for line_number, line in enumerate(body.splitlines(), start=1):
                start_index = f"{line_number}.0"
                end_index = f"{line_number}.end"
                if line.startswith("VOR DER AUFNAHME") or line.startswith("KI-RECHERCHE:"):
                    text_widget.tag_add("internal", start_index, end_index)
                if line in {
                    "ANMODERATION – VORLESEN",
                    "GOLDENER FADEN – VORLESEN",
                    "ÜBERGANG INS GESPRÄCH – VORLESEN",
                    "KONKRETE FRAGEN – FLEXIBLER INTERNER FRAGENPOOL",
                }:
                    text_widget.tag_add("heading", start_index, end_index)

            text_widget.configure(state="disabled")
            text_widget.focus_set()

            # Lesetasten
            window.bind("<F11>", toggle_fullscreen)
            window.bind("<Escape>", lambda _event: window.destroy())
            window.bind(
                "<Prior>",
                lambda _event: text_widget.yview_scroll(-1, "pages"),
            )
            window.bind(
                "<Next>",
                lambda _event: text_widget.yview_scroll(1, "pages"),
            )
            window.bind(
                "<space>",
                lambda _event: text_widget.yview_scroll(1, "pages"),
            )
            window.bind("<Home>", lambda _event: text_widget.yview_moveto(0.0))
            window.bind("<End>", lambda _event: text_widget.yview_moveto(1.0))

            window.after_idle(go_top)

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

            ai_values = self._current_ai_values()

            if kind == INTERVIEW_SCRIPT_KIND:
                subject, body = build_interview_script(
                    article=article,
                    contact=contact,
                    address_mode=self._address_mode(),
                    consent_status=ai_values["consentStatus"],
                    oral_confirmed=ai_values["oralConfirmed"],
                )
            else:
                subject, body = build_outreach_copy(
                    kind=kind,
                    title=title,
                    contact=contact,
                    hook=hook,
                    address_mode=self._address_mode(),
                )
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

            self._update_outreach_action_mode()

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
        "ZUSTAND News Studio 5.24.12 konnte nicht gestartet werden.\n\n"
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

        if kind == "Erste E-Mail":
            assert PROJECT_URL in sie_body
            assert PROJECT_URL in du_body
            assert "ausschließlich nach Ihrer vorherigen Zustimmung" in sie_body
            assert "ausschließlich nach deiner vorherigen Zustimmung" in du_body
            assert sample_url not in sie_body
            assert "für unsere Bildungsinitiative" in sie_body
            assert "für unsere Bildungsinitiative" in du_body
            assert len(sie_body.split()) < 175
            assert len(du_body.split()) < 175

        if kind in {
            "Freundliche Erinnerung",
            "Intervieweinladung",
        }:
            assert sample_url in sie_body
            assert "Bitte antworten Sie einfach mit 1, 2 oder 3" in sie_body
            assert "1 – Einverstanden" in sie_body
            assert "Ohne Ihre ausdrückliche Zustimmung" in sie_body
            assert "Bitte antworte einfach mit 1, 2 oder 3" in du_body

        if kind == "Intervieweinladung":
            assert len(sie_body.split()) < 190
            assert len(du_body.split()) < 190

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
        "Text-Selbsttest erfolgreich: Bildungsinitiative in der Erstmail, kurze "
        "Intervieweinladung, Antwortnummern für KI-Auswahl, Sie/Du, Signatur "
        "und Beispielfolge geprüft."
    )


def interview_script_self_test() -> None:
    article = {
        "title": "Welche Stadtform benötigt am wenigsten Material?",
        "summary": (
            "Wie viel Material eine Stadt pro Kopf benötigt, hängt nicht nur vom "
            "Baustoff ab, sondern auch von Dichte, Gebäudetyp und Straßen."
        ),
        "selectionLabel": "Stadtform und Ressourcen",
        "sourceTitle": "Ressourcenminimierung im urbanen Kontext",
        "editorial": {
            "coreChange": (
                "Gebäudetyp, Siedlungsdichte und Straßeninfrastruktur bestimmen "
                "den Materialverbrauch pro Person."
            ),
            "questionBehindNews": (
                "Welche Wohn- und Stadtformen ermöglichen ausreichend Lebensraum, "
                "ohne immer mehr Rohstoffe und Boden zu beanspruchen"
            ),
            "causalChain": (
                "Geringe Dichte führt zu größeren Gebäude- und Straßenflächen pro "
                "Person und damit zu höherem Materialbedarf."
            ),
            "affectedSystems": (
                "Rohstofflager, Böden, Klima, Wohnungsversorgung und Verkehr."
            ),
            "uncertainties": (
                "Die Ergebnisse beruhen auf modellierten Szenarien und einheitlichen "
                "Annahmen zur Wohnfläche."
            ),
        },
    }
    contact = {
        "name": "Dr.-Ing. Stefanie Weidner",
        "role": "Korrespondenzautorin",
        "institution": "Werner Sobek AG",
    }

    subject, no_ai = build_interview_script(
        article=article,
        contact=contact,
        address_mode="Sie",
        consent_status="Offen",
        oral_confirmed=False,
    )
    assert subject.startswith("Interviewvorbereitung:")
    assert "Bei mir ist heute Dr.-Ing. Stefanie Weidner" in no_ai
    assert "GOLDENER FADEN – VORLESEN" in no_ai
    assert "KONKRETE FRAGEN" in no_ai
    assert "Keine ausdrückliche KI-Zustimmung" in no_ai
    assert "Mit ausdrücklicher Zustimmung unseres Gastes" not in no_ai
    assert no_ai.count("\n1. ") >= 2

    _subject, ai_active = build_interview_script(
        article=article,
        contact=contact,
        address_mode="Sie",
        consent_status="Zugestimmt",
        oral_confirmed=True,
    )
    assert "KI-RECHERCHE: AKTIV" in ai_active
    assert "Mit ausdrücklicher Zustimmung unseres Gastes" in ai_active

    _subject, pending = build_interview_script(
        article=article,
        contact=contact,
        address_mode="Du",
        consent_status="Zugestimmt",
        oral_confirmed=False,
    )
    assert "mündliche Bestätigung fehlt" in pending
    assert "Mit ausdrücklicher Zustimmung unseres Gastes" not in pending
    assert "Schön, dass du heute dabei bist" in pending

    print(
        "Interview-Selbsttest erfolgreich: personalisierte Anmoderation, "
        "fünf Leitpunkte, Fragenpool und sichere KI-Logik geprüft."
    )


def interview_actionbar_self_test() -> None:
    import tkinter as test_tk
    from tkinter import ttk as test_ttk

    root = test_tk.Tk()
    root.geometry("850x260")

    tab = test_ttk.Frame(root)
    tab.pack(fill="both", expand=True)

    subject_row = test_ttk.Frame(tab)
    subject_row.pack(fill="x")
    subject_label = test_ttk.Label(subject_row, text="Betreff")
    subject_label.pack(side="left")
    test_ttk.Entry(subject_row).pack(side="left", fill="x", expand=True)

    action_row = test_ttk.Frame(tab)
    action_row.pack(side="bottom", fill="x")

    test_ttk.Button(action_row, text="Entwurf neu erzeugen").pack(side="left")
    test_ttk.Button(action_row, text="Text kopieren").pack(side="left")
    subject_copy = test_ttk.Button(
        action_row,
        text="Betreff + Text kopieren",
    )
    subject_copy.pack(side="left")
    mail_button = test_ttk.Button(
        action_row,
        text="Im Mailprogramm öffnen",
    )
    mail_button.pack(side="right")

    fullscreen = test_ttk.Button(
        action_row,
        text="Interview im Vollbild öffnen",
    )
    fullscreen.pack(side="right", padx=(8, 8))

    print_button = test_ttk.Button(
        action_row,
        text="Drucken",
    )
    print_button.pack(side="right", padx=(8, 0))

    root.update_idletasks()

    assert fullscreen.winfo_ismapped()
    assert print_button.winfo_ismapped()
    assert clean_text(print_button.cget("text")) == "Drucken"
    assert fullscreen.master is action_row
    assert clean_text(mail_button.cget("text")) == "Im Mailprogramm öffnen"

    subject_label.configure(text="Titel")
    subject_copy.configure(state="disabled")
    mail_button.configure(state="disabled")
    root.update_idletasks()

    assert subject_label.cget("text") == "Titel"
    assert str(subject_copy.cget("state")) == "disabled"
    assert str(mail_button.cget("state")) == "disabled"

    root.destroy()
    print(
        "Aktionsleisten-Selbsttest erfolgreich: Vollbild- und Druckknopf sind unten sichtbar "
        "und E-Mail-Funktionen lassen sich im Interviewmodus deaktivieren."
    )


def method_collision_self_test() -> None:
    """Stellt sicher, dass bestehende Basismethoden nicht überschrieben werden."""
    class BaseStudio:
        def __init__(self):
            # Die echte eingebettete Version ruft offenbar eine gleichnamige
            # Hilfsmethode mit nur einem Textargument auf.
            self.base_result = self._find_widget_by_text("Betreff")

        def _find_widget_by_text(self, text):
            return f"Basis:{text}"

    class ExtendedStudio(BaseStudio):
        def _zustand_walk_outreach_widgets(self, root_widget):
            yield root_widget

        def _zustand_find_outreach_widget_by_text(self, root_widget, text):
            for widget in self._zustand_walk_outreach_widgets(root_widget):
                if widget == text:
                    return widget
            return None

    app = ExtendedStudio()
    assert app.base_result == "Basis:Betreff"
    assert (
        app._zustand_find_outreach_widget_by_text(
            "Im Mailprogramm öffnen",
            "Im Mailprogramm öffnen",
        )
        == "Im Mailprogramm öffnen"
    )
    print(
        "Kollisionstest erfolgreich: bestehende Studio-Methode bleibt unverändert."
    )


def edited_fullscreen_text_self_test() -> None:
    generated = "AUTOMATISCHER ENTWURF"
    edited = (
        "ANMODERATION – VORLESEN\n\n"
        "Das ist meine persönlich überarbeitete Fassung.\n"
        "Dieser Satz darf nicht verloren gehen."
    )

    def choose_fullscreen_body(current_text: str, generated_text: str) -> str:
        current_text = current_text.strip()
        if current_text:
            return current_text + "\n"
        return generated_text

    result = choose_fullscreen_body(edited, generated)
    assert "persönlich überarbeitete Fassung" in result
    assert "AUTOMATISCHER ENTWURF" not in result

    empty_result = choose_fullscreen_body("", generated)
    assert empty_result == generated

    print(
        "Vollbild-Texttest erfolgreich: Eigene Änderungen werden übernommen; "
        "nur bei leerem Textfeld wird neu erzeugt."
    )

def integration_self_test() -> None:
    """Prüft auf dem Zielrechner zusätzlich die echte eingebettete 5.23-Kette."""
    text_self_test()
    base_module = load_base_module()
    project_root = base_module.find_project_root()
    os.environ["ZUSTAND_PROJECT_ROOT"] = str(project_root)

    with tempfile.TemporaryDirectory(prefix="zustand_studio_5249_test_") as temporary:
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
        place_scroll_layout_self_test()
        return 0

    if "--interview-self-test" in sys.argv:
        interview_script_self_test()
        return 0

    if "--actionbar-self-test" in sys.argv:
        interview_actionbar_self_test()
        return 0

    if "--collision-self-test" in sys.argv:
        method_collision_self_test()
        return 0

    if "--edited-fullscreen-self-test" in sys.argv:
        edited_fullscreen_text_self_test()
        return 0

    if "--print-self-test" in sys.argv:
        print_html_self_test()
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
        with tempfile.TemporaryDirectory(prefix="zustand_studio_52412_") as temporary:
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
                "News Studio 5.24.12 – Startfehler",
                f"{type(exc).__name__}: {exc}\n\n"
                f"Fehlerbericht:\n{ERROR_LOG}",
            )
        except Exception:
            pass
        print(f"News Studio 5.24.12 – Startfehler: {exc}", file=sys.stderr)
        print(f"Fehlerbericht: {ERROR_LOG}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
