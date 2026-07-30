ZUSTAND News Studio 5.24.9
============================

Neu
---
Der Vollbildmodus übernimmt jetzt den Text, der aktuell im großen Textfeld
sichtbar ist.

Damit bleiben eigene Änderungen erhalten, zum Beispiel:

- gekürzte oder ergänzte Anmoderation
- veränderte Reihenfolge der Leitpunkte
- eigene Übergänge
- gestrichene oder ergänzte Fragen
- persönliche Formulierungen

Wichtig
-------
Der Knopf „Interview im Vollbild öffnen“ erzeugt den Entwurf nicht mehr
automatisch neu, wenn bereits Text im Feld steht.

Nur wenn das Textfeld leer ist, wird ein neuer Interviewleitfaden erzeugt.

Der Knopf „Entwurf neu erzeugen“ überschreibt weiterhin den Text im Feld.
Diesen Knopf daher nur verwenden, wenn die bisherigen Änderungen verworfen
werden sollen.

Installation
------------
1. News Studio schließen.
2. news_studio_5_24_9.py und start_news_studio_5_24_9.bat in z-panel legen.
3. news_studio_5_23.py unverändert im selben Ordner lassen.
4. start_news_studio_5_24_9.bat starten.

5.24.8 kann als Sicherung im Ordner bleiben.

Tests
-----
Eigene Änderungen im Vollbild:
    py -3 news_studio_5_24_9.py --edited-fullscreen-self-test

Kollisionstest:
    py -3 news_studio_5_24_9.py --collision-self-test

Interviewtext:
    py -3 news_studio_5_24_9.py --interview-self-test

Aktionsleiste:
    py -3 news_studio_5_24_9.py --actionbar-self-test

Scrollansicht:
    py -3 news_studio_5_24_9.py --scroll-self-test
