# Z-PANEL 3.0 – Digital Signage

Online-Adresse:

https://blcdetlef.github.io/z-panel/

## Gestaltung

Diese Version ist für einen üblichen 16:9-Werbemonitor ausgelegt:

- vollständige Browserbreite
- circa 52 Prozent Bild links
- circa 48 Prozent Text rechts
- große Typografie
- dunkles Digital-Signage-Design
- automatischer Wechsel nach 30 Sekunden
- Pause/Weiter
- Mehr lesen
- Nächster Artikel
- Vollbildtaste
- Fortschrittsanzeige
- Pfeiltasten und Leertaste

## Installation

Diese Dateien in den Hauptordner des lokalen Repositories `z-panel` kopieren und vorhandene Versionen ersetzen:

- `index.html`
- `styles.css`
- `app.js`

Nicht ersetzen oder löschen:

- `news.json`
- `assets`
- `newsredaktion`
- `generator`

Danach mit GitHub Desktop:

1. Commit: `Z-Panel 3.0 Digital Signage`
2. `Commit to main`
3. `Push origin`
4. Seite mit `Strg + F5` neu laden

## Bilder: einfachste und robuste Lösung

Der Browser kann nicht selbst nach beliebig benannten Dateien im Ordner suchen.

Deshalb bitte jedes Artikelbild nach seiner `imageId` benennen.

Beispiele:

- `imageId`: `KL_0001_01`
- Bilddatei: `assets/images/KL_0001_01.jpg`

und:

- `imageId`: `BD_0001_01`
- Bilddatei: `assets/images/BD_0001_01.png`

Z-Panel 3.0 versucht automatisch diese vier Varianten:

- `assets/images/IMAGE-ID.webp`
- `assets/images/IMAGE-ID.jpg`
- `assets/images/IMAGE-ID.jpeg`
- `assets/images/IMAGE-ID.png`

Du musst deshalb zunächst den Generator nicht ändern.

## Alternative für spätere Generator-Version

Der Generator kann zusätzlich einen eindeutigen Pfad in `news.json` schreiben:

```json
"imageFile": "assets/images/BD_0001_01.png"
```

Ein vorhandenes `imageFile` hat Vorrang vor der automatischen Suche über `imageId`.

## Wichtig bei GitHub

Dateinamen unterscheiden Groß- und Kleinschreibung.

`BD_0001_01.png` funktioniert nicht, wenn in `imageId` beispielsweise `bd_0001_01` steht.

Auch Leerzeichen, Umlaute und Sonderzeichen in Bilddateinamen möglichst vermeiden.
