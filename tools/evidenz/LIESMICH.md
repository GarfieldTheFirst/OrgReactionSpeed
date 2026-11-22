# Evidenz-Browser neu erzeugen

`build.py` erzeugt aus der Evidenzdatenbank und der Zulieferung des Autorenteams zwei Dateien im Ordner `evidenz/`: den Evidenz-Browser (`index.html`, eine einzelne Datei mit eingebetteten Daten) und den Auszug für die Belegansicht des Leitfadens (`belege.js`).

```bash
python3 -I tools/evidenz/build.py <Evidenzdatenbank.json> tools/evidenz/template.html evidenz/index.html <codenamen.json> <Ordner mit den CSV 1 bis 5> evidenz/belege.js
```

Die Evidenzdatenbank und die CSV der Zulieferung liegen beim Autorenteam und gehören nicht in dieses Repository. `codenamen.json` darf `{}` enthalten, die Namen kommen aus dem Kodierbuch (CSV 3).

Der Leitfaden zeigt die Belegzeichen nur, wenn die Adresse `?belege` enthält. Ohne diesen Zusatz lädt er `belege.js` nicht.
