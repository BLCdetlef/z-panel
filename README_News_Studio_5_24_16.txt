ZUSTAND News Studio 5.24.16
=============================

Neu: Reiter „Messreihen“ wieder vollständig scrollbar
------------------------------------------------------
Der gesamte Inhalt des Reiters „Messreihen“ kann jetzt senkrecht gescrollt
werden. Rechts im Reiter befindet sich ein Seiten-Scrollbalken.

Die einzelnen Textfelder behalten zusätzlich ihre eigene Scrollfunktion. So
können auch längere Einordnungen und Quellenhinweise vollständig gelesen und
bearbeitet werden.

Größeres Feld „Einordnung“
--------------------------
Das Textfeld „Einordnung“ ist jetzt doppelt so hoch und verwendet eine etwas
größere Schrift. Es bietet dadurch mehr Platz für verständliche fachliche
Erläuterungen statt nur sehr kurzer Statussätze.

Biodiversität verständlicher erklärt
-------------------------------------
Der Startbestand „Living Planet Index“ wurde umbenannt in:

„Biodiversität – Living Planet Index (Kontextindikator)“

Die Einordnung erklärt nun:

- Biodiversität lässt sich nicht mit einer einzigen Zahl messen.
- Der Living Planet Index (LPI) wertet Zeitreihen beobachteter
  Wirbeltierpopulationen aus.
- Als Messgrößen dienen Individuenzahlen, Populationsdichten oder geeignete
  Ersatzgrößen wie Nester und Brutpaare.
- Der Living Planet Report 2024 beruht auf 34.836 Populationen von 5.495 Arten.
- Der Ausgangswert 1970 wird auf 1,00 gesetzt.
- Ein LPI von ungefähr 0,27 im Jahr 2020 bedeutet einen mittleren relativen
  Rückgang der beobachteten Populationen um 73 Prozent.
- Das bedeutet nicht, dass 73 Prozent aller Tiere verschwunden oder
  73 Prozent aller Arten ausgestorben sind.
- Der LPI ist ein Frühwarn- und Kontextindikator, aber nicht selbst die
  Kontrollvariable der planetaren Grenze.

Zusätzlich werden die beiden direkten Kontrollvariablen der planetaren Grenze
„Integrität der Biosphäre“ getrennt erläutert:

1. Genetische Vielfalt
   Messgröße: Aussterberate in E/MSY
   E/MSY = ausgestorbene Arten pro einer Million Arten und Jahre

2. Funktionale Integrität
   Messgröße: HANPP
   HANPP beschreibt den Anteil der Nettoprimärproduktion, den Menschen durch
   Ernte, Landnutzung und andere Eingriffe der Biosphäre entziehen oder verändern.

Diese Größen dürfen nicht zu einer einzigen scheinbar einheitlichen Kurve
verbunden werden.

Bestehende private Messreihen-Datenbank
---------------------------------------
Die Datei bruchlast_messreihen.json wird beim Start auf Datenbankversion 3
aktualisiert.

Eigene Änderungen bleiben erhalten. Die ausführlichere Biodiversitäts-
Einordnung wird nur dann automatisch übernommen, wenn dort noch genau der
unveränderte alte Starttext aus 5.24.15 gespeichert war.

Bereits gespeicherte Interviewleitfäden
---------------------------------------
Bereits dauerhaft gespeicherte Gesprächsleitfäden werden nicht automatisch
überschrieben. Soll die neue Biodiversitäts-Einordnung in einen Leitfaden
übernommen werden:

1. Beitrag und Messreihe auswählen.
2. „Entwurf neu erzeugen“ anklicken.
3. Text prüfen und gegebenenfalls bearbeiten.
4. „Leitfaden speichern“ anklicken.

Installation
------------
1. News Studio schließen.
2. news_studio_5_24_16.py und start_news_studio_5_24_16.bat in z-panel legen.
3. news_studio_5_23.py unverändert im selben Ordner lassen.
4. start_news_studio_5_24_16.bat starten.

5.24.15 kann als Sicherung im Ordner bleiben.

Prüfung
-------
Erfolgreich geprüft wurden:

- Python-Syntax
- eingebettete Programmkette aus 5.23
- Messreihen-Datenbankmigration auf Version 3
- verlustfreie Erhaltung eigener Bearbeitungen
- neue Biodiversitäts-Einordnung und Orientierungswerte
- Übernahme der Messreihen in den Gesprächsleitfaden
- bestehende E-Mail-, Speicher-, Vollbild- und Druckfunktionen

Ein automatisierter vollständiger Bildschirmtest war in der Testumgebung nicht
möglich. Die geänderten GUI-Bausteine wurden deshalb zusätzlich strukturell im
Programmcode geprüft.
