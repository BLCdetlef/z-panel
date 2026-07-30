ZUSTAND News Studio 5.24.3
============================

Neu im Reiter „Kontaktaufnahme“
-------------------------------
Unterhalb der Ansprache erscheint der Bereich:

    Optionale KI-Recherche im Interview

Dort können Sie pro Kontakt und Beitrag festhalten:

- KI-Recherche als freiwillige Wahlmöglichkeit anbieten: Ja/Nein
- Beispielfolge: Link zu einer bereits veröffentlichten Folge
- Zustimmung:
  - Offen
  - Zugestimmt
  - Abgelehnt
  - Gespräch gewünscht
- mündlich bestätigt: Ja/Nein

Der Link zur Beispielfolge wird als gemeinsamer Standard gespeichert und steht
dadurch bei weiteren Anfragen automatisch zur Verfügung.

Texterzeugung
-------------
Bei offenem Zustimmungsstatus enthält die Kontaktaufnahme:

- den optionalen Link zur Beispielfolge,
- einen kurzen freiwilligen Hinweis auf die mögliche KI-Recherche,
- drei klare Wahlmöglichkeiten,
- eine ausführliche Fußnote zu Rolle, Grenzen und Quellenprüfung.

Die KI wird nur punktuell und nach Ankündigung eingesetzt. Ohne vorherige
ausdrückliche Zustimmung bleibt sie vollständig außen vor.

Bei „Zugestimmt“ erzeugt das Studio eine Bestätigung des vereinbarten Rahmens.
Bei „Abgelehnt“ wird ausdrücklich festgehalten, dass das Interview ohne KI
stattfindet. Bei „Gespräch gewünscht“ wird die Entscheidung auf das kurze
Vorgespräch verschoben.

Im Telefonleitfaden erscheint ein eigener Abschnitt mit Zustimmungsfrage,
aktuellem Status und dem Satz zur erneuten Bestätigung am Beginn der Aufnahme.

Datenschutz
-----------
Die Zustimmungsangaben werden ausschließlich in der bereits vorhandenen privaten
lokalen Kontaktdatenbank gespeichert. Sie gelangen nicht in news.json und nicht
in öffentliche Artikeldaten.

Installation
------------
1. News Studio schließen.
2. news_studio_5_24_3.py und start_news_studio_5_24_3.bat in den Ordner z-panel legen.
3. news_studio_5_23.py unverändert im selben Ordner lassen.
4. start_news_studio_5_24_3.bat starten.

Die funktionierende Version 5.24.2 kann zunächst als Sicherung im Ordner bleiben.

Optionaler Test
---------------
Im Ordner z-panel:

    py -3 news_studio_5_24_3.py --self-test

Erwartete Abschlussmeldung:

    Integrationstest erfolgreich: eingebettete 5.23-Kette wurde geladen.
