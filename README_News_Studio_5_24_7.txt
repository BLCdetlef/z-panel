ZUSTAND News Studio 5.24.7
============================

Korrektur der Interviewansicht
------------------------------
Der Vollbildknopf aus 5.24.6 befand sich oben im scrollbaren Einstellungsbereich
und war dadurch in der gezeigten Interviewvorbereitung nicht sichtbar.

In 5.24.7 befindet sich der Knopf dauerhaft unten in der bereits sichtbaren
Aktionsleiste:

    Interview im Vollbild öffnen

Beim Anklicken wird automatisch die Textart
„Anmoderation und Gesprächsleitfaden“ gewählt und anschließend die
Vollbildansicht geöffnet.

Kontextabhängige Aktionsleiste
-----------------------------
Bei der Textart „Anmoderation und Gesprächsleitfaden“:

- „Betreff“ wird zu „Titel“
- „Betreff + Text kopieren“ ist deaktiviert
- „Im Mailprogramm öffnen“ ist deaktiviert
- „Text kopieren“ bleibt verfügbar
- der Vollbildknopf bleibt sichtbar und aktiv

Bei normalen E-Mail-Textarten stehen die E-Mail-Funktionen wieder wie bisher
zur Verfügung.

Installation
------------
1. News Studio schließen.
2. news_studio_5_24_7.py und start_news_studio_5_24_7.bat in z-panel legen.
3. news_studio_5_23.py unverändert im selben Ordner lassen.
4. start_news_studio_5_24_7.bat starten.

5.24.6 kann als Sicherung im Ordner bleiben.

Tests
-----
Textlogik:
    py -3 news_studio_5_24_7.py --text-self-test

Interviewtext:
    py -3 news_studio_5_24_7.py --interview-self-test

Untere Aktionsleiste:
    py -3 news_studio_5_24_7.py --actionbar-self-test

Scrollansicht:
    py -3 news_studio_5_24_7.py --scroll-self-test

Eingebettete Programmkette:
    py -3 news_studio_5_24_7.py --self-test
