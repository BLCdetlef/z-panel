# Z-PANEL 2.0 – Infoscreen

Online-Adresse:

https://blcdetlef.github.io/z-panel/

## Was diese Version macht

- immer genau ein Artikel auf dem Bildschirm
- großes Bild links
- Überschrift und Kurztext rechts
- automatischer Wechsel nach 30 Sekunden
- Pause/Weiter-Schalter
- Schalter „Mehr lesen“
- Schalter „Nächster Artikel“
- Fortschrittsbalken und Countdown
- weiche Überblendung
- Tastatursteuerung:
  - Pfeil rechts: nächster Artikel
  - Pfeil links: vorheriger Artikel
  - Leertaste: Pause/Weiter
- responsive Darstellung auf Notebook, Tablet und Smartphone

## Installation

Die folgenden Dateien in den Hauptordner des lokalen Repositories `z-panel` kopieren:

- `index.html`
- `styles.css`
- `app.js`

Vorhandene Versionen dieser drei Dateien ersetzen.

`news.json`, `assets` und die Redaktionsordner nicht löschen oder ersetzen.

## Veröffentlichung

1. GitHub Desktop öffnen.
2. Änderungen kontrollieren.
3. Commit-Nachricht: `Z-Panel 2.0 Infoscreen`
4. `Commit to main`
5. `Push origin`
6. Nach kurzer Wartezeit diese Seite neu laden:

https://blcdetlef.github.io/z-panel/

Am besten mit `Strg + F5`, damit der Browser die alten Dateien nicht aus dem Cache verwendet.

## Bilder

Das Panel verwendet zuerst:

- `imageFile`
- ersatzweise `imageUrl`

aus dem jeweiligen Artikelobjekt in `news.json`.

Falls kein Bildpfad enthalten ist, erscheint ein neutraler Platzhalter. Dann muss der Generator später so ergänzt werden, dass er den passenden Bildpfad in `news.json` einträgt.
