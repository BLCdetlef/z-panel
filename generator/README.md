# News-Generator

## Windows

Doppelklick auf:

`news_erzeugen.bat`

## Kommandozeile

```text
python generator/news_erzeugen.py
```

Der Generator liest:

- `newsredaktion/artikel/index.json`
- `newsredaktion/quellen/index.json`
- Artikeldateien in `newsredaktion/artikel/`
- Bilder und Bildmetadaten in `assets/images/`

Bei Fehlern wird keine neue `news.json` geschrieben.
