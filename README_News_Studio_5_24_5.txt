ZUSTAND News Studio 5.24.5
============================

Korrektur
---------
Die Scrolllösung aus 5.24.4 zeigte zwar den Scrollbalken, machte aber den
vorhandenen Inhalt des Reiters „Kontaktaufnahme“ unsichtbar.

5.24.5 basiert deshalb wieder auf der funktionierenden Version 5.24.3.
Der bestehende Inhaltsrahmen wird nicht in einen Canvas umgehängt. Er bleibt
an seiner ursprünglichen Stelle und wird beim Scrollen lediglich vertikal
verschoben.

Ergebnis
--------
- der Inhalt des Reiters bleibt sichtbar
- vertikaler Scrollbalken am rechten Rand
- Mausradsteuerung über normalen Bedienelementen
- das große Nachrichtentextfeld behält seine eigene Scrollfunktion
- alle KI-, Zustimmungs-, Signatur- und Sie-/Du-Funktionen bleiben erhalten

Installation
------------
1. News Studio schließen.
2. news_studio_5_24_5.py und start_news_studio_5_24_5.bat in z-panel legen.
3. news_studio_5_23.py unverändert im selben Ordner lassen.
4. start_news_studio_5_24_5.bat starten.

5.24.4 bitte nicht mehr verwenden. 5.24.3 kann als funktionierende Sicherung
im Ordner bleiben.

Tests
-----
Textlogik:
    py -3 news_studio_5_24_5.py --text-self-test

Scrollansicht:
    py -3 news_studio_5_24_5.py --scroll-self-test

Eingebettete Programmkette:
    py -3 news_studio_5_24_5.py --self-test
