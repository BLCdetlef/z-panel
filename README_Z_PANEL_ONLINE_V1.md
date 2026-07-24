# Z-PANEL Online V1

## Einbau

Diese drei Dateien in den Hauptordner deines GitHub-Repositories `z-panel` kopieren:

- `index.html`
- `styles.css`
- `app.js`

Die bereits erzeugte `news.json` muss ebenfalls im Hauptordner liegen.

Die vorhandenen Verzeichnisse, insbesondere `assets/images`, bleiben unverändert.

## Veröffentlichung mit GitHub Desktop

1. Dateien in den lokalen Ordner `Dokumente/GitHub/z-panel` kopieren.
2. GitHub Desktop öffnen.
3. Änderungen prüfen.
4. Commit-Nachricht, zum Beispiel: `Z-Panel Online V1`.
5. `Commit to main`.
6. `Push origin`.
7. GitHub Pages nach ein bis drei Minuten neu laden.

## Aufruf

Bei einem Repository namens `z-panel` lautet die typische Adresse:

`https://DEIN-GITHUB-NAME.github.io/z-panel/`

## Funktionen

- automatische Anzeige aus `news.json`
- responsive Darstellung für Notebook, Tablet und Smartphone
- Filter nach planetarer Grenze
- Volltextsuche
- Artikelansicht im Dialogfenster
- Quellenlink
- Anzeige von Bild und Alt-Text aus den Bildmetadaten
- verständliche Fehlermeldung, falls `news.json` fehlt

## Wichtig

Im Klimaartikel KL_0001 sollte weiterhin geprüft sein:

`"planetaryBoundary": "KL"`

Das Online-Panel veröffentlicht nur das, was in der aktuellen `news.json` enthalten ist.
