ZUSTAND News Studio 5.24.14
=============================

Neu: Reiter „Messreihen“
------------------------
Der neue Reiter dient zunächst ausschließlich als interne Hintergrundhilfe
für Interviews. Er ist noch kein vollständiges digitales BRUCHLASTchart und
keine automatische wissenschaftliche Freigabe.

Je Interviewbeitrag kann genau eine Messreihe verknüpft werden.

Im Reiter werden bewusst nur die wichtigsten Angaben geführt:

- Messreihe
- zugehörige planetare Grenze
- Datenstatus
  A – geprüft
  B – Diskussionskurve
  C – nur Lehrmaterial
- Einordnung der Grenzüberschreitung
- kurze fachliche Einordnung
- Quellenlage und Einschränkungen
- wichtigste Quellen oder Suchhinweise

Startbestand
------------
Beim ersten Start legt das Studio acht vorsichtig eingeordnete Arbeitsstände
zu bereits veröffentlichten studentischen Ergebnissen an:

- CO2-Konzentration global
- weltweite Kunststoffproduktion
- Ozeanversauerung / Aragonit-Sättigung
- anthropogener Stickstoffeintrag
- blaues Wasser
- Gletscherschwund in den Alpen
- globale Waldfläche
- Living Planet Index

Diese Einträge sind ausdrücklich Prüf- und Arbeitsstände. Sie können im Studio
bearbeitet, ergänzt oder gelöscht werden.

Verknüpfung mit einem Interview
-------------------------------
1. Im Reiter „Kontaktaufnahme“ Person und Meldung/Studie auswählen.
2. Im dortigen Kasten „BRUCHLAST-Messreihe“ auf „Messreihen öffnen“ klicken.
3. Gewünschte Messreihe auswählen.
4. „Mit aktuellem Interview verknüpfen“ anklicken.

Beim Neuerzeugen von „Anmoderation und Gesprächsleitfaden“ erscheint dann ein
kurzer interner Abschnitt:

BRUCHLAST-HINTERGRUND – NICHT VORLESEN

Er enthält nur Messreihe, Grenzüberschreitung, Datenstatus, Einordnung und
Quellenlage. Bereits dauerhaft gespeicherte Leitfäden werden nicht ungefragt
überschrieben. Für ihre Ergänzung bitte „Entwurf neu erzeugen“ und anschließend
„Leitfaden speichern“ verwenden.

Speicherort
-----------
Die Messreihen werden getrennt vom öffentlichen Z-PANEL in der privaten lokalen
Studio-Ablage gespeichert:

Windows:
%LOCALAPPDATA%\ZUSTAND\NewsStudio\bruchlast_messreihen.json

Dadurch werden die internen Prüfnotizen nicht automatisch veröffentlicht.

Installation
------------
1. News Studio schließen.
2. news_studio_5_24_14.py und start_news_studio_5_24_14.bat in z-panel legen.
3. news_studio_5_23.py unverändert im selben Ordner lassen.
4. start_news_studio_5_24_14.bat starten.

5.24.13 kann als Sicherung im Ordner bleiben.

Prüfung
-------
Erfolgreich geprüft wurden:

- Python-Syntax
- eingebettete Programmkette aus 5.23
- bestehende E-Mail- und Interviewfunktionen
- dauerhafte Speicherung der Interviewleitfäden
- Messreihen-Startbestand
- Verknüpfung einer Messreihe mit einem Interviewbeitrag
- kompakter BRUCHLAST-Hintergrund im Gesprächsleitfaden
- sichtbarer Messreihen-Reiter im grafischen Oberflächentest
- Druck- und Vollbildlogik
