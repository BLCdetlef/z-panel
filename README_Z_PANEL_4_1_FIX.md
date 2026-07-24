# Z-Panel 4.1 – Automatik-Fix

Diese Version basiert auf dem hochgeladenen Originalprojekt.

Behoben wurde der Fehler, dass der automatische Artikelwechsel nach dem ersten Beitrag stehen blieb. Ursache war, dass der Timer während des asynchronen Bildwechsels in jedem Browser-Frame erneut `nextArticle()` aufrief. Dadurch wurde der laufende Wechsel immer wieder abgebrochen.

Geändert wurden nur:

- `app.js`: Übergangssperre und sichere Timer-Rücksetzung
- diese README-Datei

Der Browsertitel lautet bereits **ZUSTAND Infoscreen**. Bilder werden weiterhin vorgeladen und vor dem Wechsel dekodiert.

## Einspielen

Den Inhalt dieses ZIP-Ordners über den lokalen Repository-Ordner kopieren. Anschließend in GitHub Desktop die Änderung an `app.js` prüfen, committen und pushen. Danach die veröffentlichte Seite mit `Strg+F5` neu laden und mindestens zwei automatische Wechsel abwarten.
