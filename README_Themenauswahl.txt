ZUSTAND News Studio 5.23 und Z-PANEL-Themenauswahl
===================================================

1. Vorher eine Sicherung des bisherigen Projektordners anlegen.

2. news_studio_5_23.py in den Hauptordner des Z-PANEL-Projekts legen.
   Die Datei ist eigenständig. Die früheren news_studio_*.py-Dateien werden
   zum Start nicht mehr benötigt, sollten vorerst aber als Sicherung bleiben.

3. News Studio 5.23 starten.

4. Im Reiter „Abspielfolge“ einen Grundlagenblock auswählen.
   Unten erscheint das neue Feld „Thema“.
   Beispiele:
   - Klimawandel
   - Gesundheit und Lebensgrundlagen
   - Biodiversität
   Mehrere Grundlagen dürfen exakt dasselbe Thema erhalten.

5. Ohne eigenen Eintrag verwendet das Studio vorläufig den vollständigen Titel
   des Grundlagenbeitrags als Thema. Vorhandene selectionLabel-Werte aus 5.22
   werden beim Laden und Export weiterhin erkannt.

6. Danach news.json wie gewohnt neu erzeugen. News mit explainerId übernehmen
   automatisch das Thema ihrer Grundlage. Meldungen ohne Grundlage bleiben nur
   in „Alle Themen“.

7. Im Web-Panel index.html, app.js und styles.css durch die neuen Dateien ersetzen.
   Beim Öffnen erscheint zunächst die Themenauswahl. Eine einzelne Themenwahl
   enthält nur die zugehörigen News und Grundlagen. Leitbild, Redaktionskodex und
   unzugeordnete Meldungen erscheinen weiterhin unter „Alle Themen“.

8. Die beigefügte news.json ist nur eine sofort testbare Fassung des zuletzt
   hochgeladenen Datenstands. Für KL_0014 ist beispielhaft „Klimawandel“ gesetzt;
   andere Grundlagen verwenden zunächst ihren Titel als Rückfallwert. Nach der
   Bearbeitung im Studio news.json erneut erzeugen.

Technischer Selbsttest ohne Fenster:
python news_studio_5_23.py --self-test
