ZUSTAND / Z-PANEL 5.25

ENTHALTEN
- index.html
- app.js
- styles.css
- news.json
- news_studio_5_25.py

WAS IST NEU?
- Das normale Z-PANEL bleibt unter index.html erreichbar.
- Die Homepage-Vorschau nutzt dieselbe Seite mit:
  index.html?mode=homepage
- Alle Beiträge und dieselbe Reihenfolge werden verwendet.
- Es gibt keine zweite news.json und keine Homepage-Auswahl pro Beitrag.
- Infoscreen und Z-PANEL sind derselbe Ausgabekanal.

INSTALLATION Z-PANEL
1. Bestehenden GitHub-Ordner sichern.
2. index.html, app.js, styles.css und news.json durch diese Dateien ersetzen.
3. Den Ordner assets/images unverändert lassen.
4. Auf GitHub hochladen.
5. Zuerst normal testen:
   https://blcdetlef.github.io/z-panel/
6. Danach Homepage-Modus testen:
   https://blcdetlef.github.io/z-panel/?mode=homepage

TYPO3
Als externe Ressource verwenden:
https://blcdetlef.github.io/z-panel/?mode=homepage

EMPFOHLENE IFRAME-HÖHE
Desktop zunächst 650 bis 720 px.
Mobil sollte das TYPO3-Element responsiv wachsen dürfen.

STUDIO
news_studio_5_25.py bleibt wie 5.24.16 von news_studio_5_23.py abhängig.
Die Basisdatei muss deshalb weiterhin im selben lokalen Ordner liegen.
Beim Start und nach dem Schließen wird news.json verlustfrei als Version 2
gekennzeichnet. Beiträge und Reihenfolge werden nicht verändert.

RÜCKFALL
Bei Problemen die zuvor gesicherten vier Webdateien wiederherstellen.
