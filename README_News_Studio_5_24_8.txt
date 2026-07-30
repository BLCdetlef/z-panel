ZUSTAND News Studio 5.24.8
============================

Korrektur
---------
In 5.24.7 verwendete die neue Suche nach der unteren Aktionsleiste den Namen:

    _find_widget_by_text

Dieser Name wird bereits in der eingebetteten Studio-Grundversion verwendet,
allerdings mit einer anderen Parameterzahl. Dadurch wurde die vorhandene Methode
beim Start unbeabsichtigt überschrieben und es erschien:

    TypeError: ... _find_widget_by_text() missing 1 required positional argument: 'text'

5.24.8 verwendet nun eindeutig benannte Hilfsmethoden:

    _zustand_walk_outreach_widgets
    _zustand_find_outreach_widget_by_text

Die vorhandenen Methoden der Grundversion bleiben dadurch vollständig
unverändert.

Installation
------------
1. News Studio schließen.
2. news_studio_5_24_8.py und start_news_studio_5_24_8.bat in z-panel legen.
3. news_studio_5_23.py unverändert im selben Ordner lassen.
4. start_news_studio_5_24_8.bat starten.

5.24.7 bitte nicht mehr verwenden.

Erwartetes Ergebnis
-------------------
Im Reiter „Kontaktaufnahme“ steht unten neben den bisherigen Aktionen:

    Interview im Vollbild öffnen

Beim Interviewleitfaden werden die E-Mail-Schaltflächen deaktiviert.

Tests
-----
Kollisionstest:
    py -3 news_studio_5_24_8.py --collision-self-test

Textlogik:
    py -3 news_studio_5_24_8.py --text-self-test

Interviewtext:
    py -3 news_studio_5_24_8.py --interview-self-test

Untere Aktionsleiste:
    py -3 news_studio_5_24_8.py --actionbar-self-test

Scrollansicht:
    py -3 news_studio_5_24_8.py --scroll-self-test
