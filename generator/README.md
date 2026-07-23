# News-Generator

Der Generator liest alle passenden JSON-Dateien automatisch ein.

## Gelesene Ordner

- `newsredaktion/artikel/`
- `newsredaktion/quellen/`
- `assets/images/`

`index.json` wird nicht mehr benötigt und vom Generator ignoriert.

## Windows

Doppelklick auf:

`news_erzeugen.bat`

## Kommandozeile

```text
python generator/news_erzeugen.py
```

Bei Fehlern wird keine neue `news.json` erzeugt. Erfolgreich geprüfte Artikel werden nach Veröffentlichungsdatum sortiert; der neueste Beitrag steht zuerst.
