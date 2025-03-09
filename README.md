MCOS Cannabis Scraper & PDF Generator
======================================

Dieses Projekt kombiniert Web-Scraping und PDF-Generierung in einem Python-Skript. Das Skript meldet sich auf der Website "medcanonestop.com" an, navigiert zu den Cannabis-Blüten, scrapt Produktinformationen (wie Name, Genetik, THC- und CBD-Gehalt, Preis) und speichert diese in einer JSON-Datei. Anschließend wird eine PDF-Tabelle aus den gescrapten Daten erstellt. 

Features
--------
- **Mehrsprachige Benutzeroberfläche:**  
  Vor dem Start wird eine Sprachauswahl angeboten (Deutsch, Englisch, Französisch, Spanisch). Alle Menüs, Eingabeaufforderungen und PDF-Beschriftungen passen sich an die gewählte Sprache an.
  
- **Web-Scraping:**  
  Mit Selenium wird der Login durchgeführt, Cookie-Banner automatisch akzeptiert und die Produktseite vollständig geladen. Die Daten werden scrapt und in der Datei `cannabis_strains.json` gespeichert.

- **PDF-Erstellung:**  
  Mithilfe von fpdf2 und pandas werden die Daten sortiert (z. B. nach Preis, THC oder CBD) und als PDF-Tabelle ausgegeben.

Voraussetzungen
---------------
- **Python 3.x**
- **Google Chrome** und **ChromeDriver** (ChromeDriver muss im Systempfad verfügbar sein)
- **Benötigte Python-Pakete:**  
  - selenium  
  - fpdf2  
  - pandas  

Stelle sicher, dass die Datei `DejaVuSans.ttf` im selben Verzeichnis wie das Skript liegt, da diese Schriftart für die PDF-Erstellung verwendet wird.

Installation
------------
Installiere die benötigten Pakete über den folgenden Befehl (sodass nur `fpdf2` installiert ist):

    pip uninstall --yes pypdf && pip install --upgrade fpdf2 selenium pandas

Verwendung
----------
1. Klone das Repository oder lade die Dateien herunter.
2. Stelle sicher, dass alle Abhängigkeiten installiert sind und sich `DejaVuSans.ttf` im Skriptverzeichnis befindet.
3. Starte das Skript über die Kommandozeile:

       python aio.py

4. Wähle die gewünschte Sprache (1 = Deutsch, 2 = Englisch, 3 = Französisch, 4 = Spanisch).
5. Gib deine Login-Daten ein, um dich auf der Website anzumelden.
6. Nach erfolgreichem Scraping wirst du aufgefordert, eine Sortieroption für die PDF-Erstellung auszuwählen.
7. Anschließend wird eine PDF-Datei mit den sortierten Daten erstellt und im gleichen Verzeichnis gespeichert.

Hinweise
--------
- **Cookie-Banner:**  
  Das Skript versucht, eventuelle Cookie-Banner automatisch zu akzeptieren.
  
- **Sortierfunktion:**  
  Bei der PDF-Erstellung kannst du zwischen verschiedenen Sortierkriterien wählen (z. B. Preis pro Gramm THC, CBD, etc.).
  
- **Fehlermeldungen:**  
  Bei Problemen (z. B. wenn Elemente nicht gefunden werden) gibt das Skript entsprechende Fehlermeldungen aus und beendet den Vorgang.

Lizenz
------
Dieses Projekt steht unter der MIT-Lizenz. Weitere Informationen findest du in der Datei LICENSE.

---------------------------------------------------------
