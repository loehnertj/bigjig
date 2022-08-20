Jigsoid Jigsaw puzzle game

*jigsoid [adj]*: Having the look and feel of an actual jigsaw puzzle.

For the moment, this is just dumped here with all flaws that might or might not be there. Feel free to open issues / PR's.


# Installation:

Python 3 ONLY. No it won't work with python2. Move on.

You need python3-qtpy, python3-pyqt5.qtopengl, gcc.

Install with `pip install -U .`

Run with `jigsoid`.



# Controls

 * Mausrad zoomt
 * Q: Zoom umschalten zwischen Alles sichtbar und 1:1
 * LMT / Leertaste ziehen = Ansicht verschieben
 * LMT / Leertaste drücken = Teil aufnehmen / ablegen
 * A: Links drehen
 * W / RMT (wenn Teil aufgenommen): rechts drehen
 * S / RMT klicken: Teil wählen/abwählen
 * S / RMT ziehen: im Rahmen wählen
 * W klicken: Auswahl aufheben
 * W / Shift+RMT ziehen: im Rahmen abwählen
 * E: gewählte Teile im Raster anordnen und um Cursor zentrieren
 
# Empfehlungen

- sortieren (am Anfang): Teile nacheinander mit S wählen, dann mit E an einen freien Platz beamen
- Gruppen bilden (mitte): passende Teile mit S wählen, dann mit E in die Nähe der Anbaustelle beamen
- einzelne fehlende Teile platzieren (zum Ende hin):
    - mit Q in Totale
    - mit Q auf Vorrat zoomen
    - Teil aufnehmen
    - mit Q in Totale, Stelle suchen
    - mit Q Stelle zoomen, ggf. mit Leertaste/LMT Ansicht schieben
    - wiederholen mit dem nächsten Teil
