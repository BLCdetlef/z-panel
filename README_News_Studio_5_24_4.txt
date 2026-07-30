ZUSTAND News Studio 5.24.4
============================

Neu
---
Der gesamte Reiter „Kontaktaufnahme“ ist jetzt vertikal scrollbar.

- sichtbarer Scrollbalken am rechten Rand
- Mausradsteuerung über Auswahlfeldern, Hinweisen und Schaltflächen
- das große Nachrichtentextfeld behält seine eigene Scrollfunktion
- beim Öffnen beginnt die Ansicht immer oben
- alle Funktionen aus 5.24.3 bleiben erhalten

Installation
------------
1. News Studio schließen.
2. news_studio_5_24_4.py und start_news_studio_5_24_4.bat in den Ordner z-panel legen.
3. news_studio_5_23.py unverändert im selben Ordner lassen.
4. start_news_studio_5_24_4.bat starten.

Die funktionierende Version 5.24.3 kann zunächst als Sicherung im Ordner bleiben.
Artikel, Kontakte, Bilder, Zustimmungsangaben und news.json werden nicht verändert.

Optionaler Test
---------------
Textlogik:

    py -3 news_studio_5_24_4.py --text-self-test

Scrollansicht:

    py -3 news_studio_5_24_4.py --scroll-self-test

Vollständige eingebettete Programmkette:

    py -3 news_studio_5_24_4.py --self-test
