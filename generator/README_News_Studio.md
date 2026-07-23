# ZUSTAND News Studio

Das News Studio ist eine kleine grafische Anwendung für Windows. Sie prüft die redaktionellen Dateien und erzeugt anschließend die fertige `news.json`.

## Installation

Diese Dateien gehören in den vorhandenen Ordner:

```text
z-panel/generator/
```

- `news_studio.py`
- `news_studio_starten.bat`

Die vorhandene Datei `news_erzeugen.py` darf bestehen bleiben. Das News Studio arbeitet jedoch eigenständig.

## Start

Doppelklick auf:

```text
news_studio_starten.bat
```

## Funktionen

- Anzahl der Artikel, Quellen, Bilder und Bildmetadaten anzeigen
- JSON-Dateien auf Lesbarkeit prüfen
- leere und ungültige JSON-Dateien erkennen
- Pflichtfelder der Artikel prüfen
- Artikelstatus prüfen
- Quellen-IDs prüfen
- Bild und Bildmetadaten zur `imageId` prüfen
- doppelte Artikel- und Quellen-IDs erkennen
- fertige `news.json` erzeugen
- Artikel nach Veröffentlichungsdatum sortieren

## Wichtig

Nur JSON-Dateien im Ordner `newsredaktion/artikel/` werden als veröffentlichungsfähige Artikel geprüft. Unfertige Beiträge gehören in `newsredaktion/entwuerfe/`.

Zulässige Statuswerte für Artikel im Veröffentlichungsordner:

- `freigegeben`
- `veroeffentlicht`
