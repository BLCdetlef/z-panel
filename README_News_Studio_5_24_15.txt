ZUSTAND News Studio 5.24.15
=============================

Neu: Gerundete Orientierungswerte im Reiter „Messreihen“
---------------------------------------------------------
Jede Messreihe besitzt jetzt ein zusätzliches Textfeld:

„Gerundete Orientierungswerte mit Jahr und Maßeinheit“

Es enthält nur wenige Werte, die den Zustand verständlich machen sollen:

- früherer beziehungsweise vorindustrieller Referenzwert
- planetare Belastungsgrenze, wenn wissenschaftlich definiert
- heutiger grob gerundeter Wert
- gegebenenfalls Hochrisikogrenze oder klar bezeichnetes Zukunftsszenario

Die Werte sind interne Interview-Hintergründe. Sie sind keine automatisch
freigegebenen Chartpunkte und ersetzen nicht die Prüfung der Originalquelle.

Startbestand
------------
Gerundete Orientierungswerte wurden ergänzt für:

- globale CO2-Konzentration
- weltweite Kunststoffproduktion beziehungsweise -nutzung
- Aragonit-Sättigung des Oberflächenmeeres
- anthropogene Stickstofffixierung
- blaues Wasser / Störungen der Fließgewässer
- Gletscherschwund in den Alpen
- Landnutzungswandel / Waldbedeckung
- Living Planet Index mit zusätzlichem Bezug zu direkten PB-Kontrollvariablen

Wichtige Unterscheidungen bleiben sichtbar:

- Messwert ist nicht dasselbe wie Szenario.
- Kunststoffproduktion ist keine definierte planetare Kontrollvariable.
- Gletscherschwund ist eine Kontextgröße, keine eigene planetare Grenze.
- Globale Waldfläche und Living Planet Index sind nicht identisch mit den
  direkten Kontrollvariablen der jeweiligen planetaren Grenze.
- Die bisherige studentische Reihe zum blauen Wasser bleibt als Kurve
  überprüfungsbedürftig; die neuen Orientierungswerte beziehen sich auf die
  konsistente Kontrollvariable des Planetaren Gesundheitschecks 2025.

Interviewleitfaden
------------------
Bei einer verknüpften Messreihe erscheinen die Werte automatisch im Abschnitt:

BRUCHLAST-HINTERGRUND – NICHT VORLESEN

Sie werden dort als Aufzählung unter „Gerundete Orientierungswerte“ angezeigt.
Bereits dauerhaft gespeicherte Gesprächsleitfäden werden nicht automatisch
überschrieben. Dazu „Entwurf neu erzeugen“ und anschließend „Leitfaden speichern“
verwenden.

Bestehende Messreihen-Datenbank
-------------------------------
Die private Datei bruchlast_messreihen.json wird automatisch auf Datenbankversion 2
ergänzt. Eigene Bezeichnungen, Einordnungen, Quellenhinweise und Verknüpfungen
bleiben erhalten. Nur das neue Wertefeld wird bei den bekannten acht Startreihen
ergänzt, sofern es bisher leer ist.

Installation
------------
1. News Studio schließen.
2. news_studio_5_24_15.py und start_news_studio_5_24_15.bat in z-panel legen.
3. news_studio_5_23.py unverändert im selben Ordner lassen.
4. start_news_studio_5_24_15.bat starten.

5.24.14 kann als Sicherung im Ordner bleiben.

Prüfung
-------
Erfolgreich geprüft wurden:

- Python-Syntax
- eingebettete Programmkette aus 5.23
- Migration der vorhandenen Messreihen-Datenbank
- Speichern und Laden eigener Orientierungswerte
- Übernahme in den Gesprächsleitfaden
- sichtbares Wertefeld im grafischen Oberflächentest
- bestehende E-Mail-, Interview-, Vollbild- und Druckfunktionen
