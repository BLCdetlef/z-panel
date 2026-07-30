ZUSTAND News Studio 5.24.6
============================

Neu: Interviewvorbereitung
--------------------------
Im Reiter „Kontaktaufnahme“ gibt es zwei neue Schaltflächen:

- Anmoderation erzeugen
- Im Vollbild öffnen

Außerdem steht in „Textart“ die neue Auswahl:

    Anmoderation und Gesprächsleitfaden

Automatisch eingesetzt werden:
- Thema des ausgewählten Beitrags
- Titel des ZUSTAND-Beitrags
- zugrunde liegende Veröffentlichung
- Kurzinhalt
- Name, Funktion und Institution der ausgewählten Interviewperson
- fünf kurze Leitpunkte als vorgelesener goldener Faden
- gespeicherte Interviewfragen, sofern vorhanden
- zusätzliche personalisierte Fragen aus den redaktionellen Feldern

Die Anmoderation enthält den Übergang:

    Bei mir ist heute ...

KI-Sicherheit
-------------
Der öffentliche KI-Hinweis erscheint nur, wenn beides dokumentiert ist:

1. Zustimmung = Zugestimmt
2. mündlich bestätigt = Ja

In allen anderen Fällen bleibt die KI aus. Im Vollbild erscheint oben ein
interner Hinweis, der nicht vorgelesen werden soll.

Vollbildansicht
---------------
- große Schrift, Standardgröße 25
- Schrift mit Minus/Plus zwischen 16 und 42 veränderbar
- rechter Scrollbalken
- Leertaste oder Bild-ab: eine Seite weiter
- Bild-auf: eine Seite zurück
- Pos1/Ende: Anfang/Ende
- F11: Vollbild an/aus
- Esc: schließen

Installation
------------
1. News Studio schließen.
2. news_studio_5_24_6.py und start_news_studio_5_24_6.bat in z-panel legen.
3. news_studio_5_23.py unverändert im selben Ordner lassen.
4. start_news_studio_5_24_6.bat starten.

5.24.5 kann als funktionierende Sicherung im Ordner bleiben.

Tests
-----
Textlogik:
    py -3 news_studio_5_24_6.py --text-self-test

Interviewvorbereitung:
    py -3 news_studio_5_24_6.py --interview-self-test

Scrollansicht:
    py -3 news_studio_5_24_6.py --scroll-self-test

Eingebettete Programmkette:
    py -3 news_studio_5_24_6.py --self-test
