# ZUSTAND-Newsredaktion

Dieser Ordner ist der redaktionelle Arbeitsbereich des ZUSTAND-News-Panels.

## Ordner

- `artikel/`: freigegebene Beiträge
- `quellen/`: Stammdaten zu Institutionen und Primärquellen
- `entwuerfe/`: Beiträge in Bearbeitung
- `archiv/`: nicht mehr aktive Beiträge
- `vorlagen/`: JSON-Vorlagen

## Dateinamen

Artikel:

`KL_0001_wmo_2026.json`

Bilddateien und Bildmetadaten:

`KL_0001_ausgetrockneter_boden.jpg`  
`KL_0001_ausgetrockneter_boden.json`

Quellen:

`WMO.json`, `PIK.json`, `IPCC.json`

## Statuswerte

- `entwurf`
- `freigegeben`
- `veroeffentlicht`
- `archiviert`

## Ablauf

1. Neuen Beitrag aus `vorlagen/artikel_vorlage.json` erzeugen.
2. Beitrag zunächst in `entwuerfe/` speichern.
3. Quelle und Bildmetadaten ergänzen.
4. Nach Prüfung nach `artikel/` verschieben.
5. Dateinamen in `artikel/index.json` eintragen.
6. Generator ausführen.
7. Die erzeugte Datei `news.json` wird vom Z-Panel geladen.

## Generator starten

Windows:

`generator\news_erzeugen.bat`

Alternativ:

`python generator/news_erzeugen.py`

Der Generator prüft Pflichtfelder, Quellen und Bilder und erzeugt im Projekt-Hauptordner `news.json`.
