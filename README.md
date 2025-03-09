MCOS Cannabis Scraper & PDF Generator
======================================

--------------------------------------------------
DEUTSCH
--------------------------------------------------
Beschreibung:
Dieses Projekt kombiniert Web-Scraping und PDF-Generierung in einem Python-Skript. Es loggt sich auf der Website "medcanonestop.com" ein, navigiert zu den Cannabis-Blüten, scrapt Produktinformationen (z. B. Name, Genetik, THC- und CBD-Gehalt, Preis) und speichert diese in der Datei `cannabis_strains.json`. Anschließend wird eine PDF-Tabelle aus den gescrapten Daten erstellt.

Funktionen:
- Mehrsprachige Benutzeroberfläche (Deutsch, Englisch, Französisch, Spanisch)
- Automatischer Login inklusive Cookie-Banner-Akzeptanz
- Vollständiges Laden und Scrapen der Produktseite
- Erstellung einer sortierten PDF-Tabelle der gescrapten Daten

Voraussetzungen:
- Python 3.x
- Google Chrome und ChromeDriver (im Systempfad verfügbar)
- Notwendige Python-Pakete: selenium, fpdf2, pandas
- Datei `DejaVuSans.ttf` im Skriptverzeichnis

Installation:
Installiere die benötigten Pakete mit folgendem Befehl:
    pip uninstall --yes pypdf && pip install --upgrade fpdf2 selenium pandas

Verwendung:
1. Repository klonen oder Dateien herunterladen.
2. Abhängigkeiten installieren und sicherstellen, dass `DejaVuSans.ttf` im Verzeichnis liegt.
3. Skript über die Kommandozeile starten:
       python aio.py
4. Sprache auswählen, Login-Daten eingeben und den Anweisungen folgen.
5. Nach erfolgreichem Scraping wird eine sortierte PDF erstellt.

Lizenz:
Dieses Projekt steht unter der MIT-Lizenz.

--------------------------------------------------
ENGLISH
--------------------------------------------------
Description:
This project combines web scraping and PDF generation into a single Python script. It logs into the website "medcanonestop.com", navigates to the cannabis strains page, scrapes product information (e.g. name, genetics, THC and CBD content, price) and saves it in `cannabis_strains.json`. Then, it generates a PDF table from the scraped data.

Features:
- Multilingual interface (German, English, French, Spanish)
- Automatic login including cookie banner acceptance
- Complete loading and scraping of the product page
- Creation of a sorted PDF table from the scraped data

Requirements:
- Python 3.x
- Google Chrome and ChromeDriver (available in the system PATH)
- Required Python packages: selenium, fpdf2, pandas
- The `DejaVuSans.ttf` file must be in the script directory

Installation:
Install the required packages with:
    pip uninstall --yes pypdf && pip install --upgrade fpdf2 selenium pandas

Usage:
1. Clone the repository or download the files.
2. Install dependencies and ensure `DejaVuSans.ttf` is in the same directory.
3. Run the script via the command line:
       python aio.py
4. Select your language, enter your login credentials, and follow the prompts.
5. After successful scraping, a sorted PDF will be generated.

License:
This project is licensed under the MIT License.

--------------------------------------------------
FRANÇAIS
--------------------------------------------------
Description:
Ce projet combine le web scraping et la génération de PDF dans un script Python unique. Il se connecte au site "medcanonestop.com", navigue vers la page des variétés de cannabis, extrait des informations sur les produits (par exemple, nom, génétique, teneur en THC et CBD, prix) et les enregistre dans le fichier `cannabis_strains.json`. Ensuite, il génère un tableau PDF à partir des données extraites.

Fonctionnalités:
- Interface multilingue (allemand, anglais, français, espagnol)
- Connexion automatique avec acceptation de la bannière de cookies
- Chargement complet et extraction des données de la page produit
- Création d'un tableau PDF trié à partir des données extraites

Prérequis:
- Python 3.x
- Google Chrome et ChromeDriver (disponibles dans le PATH du système)
- Modules Python requis : selenium, fpdf2, pandas
- Le fichier `DejaVuSans.ttf` doit se trouver dans le répertoire du script

Installation:
Installez les modules requis avec la commande suivante :
    pip uninstall --yes pypdf && pip install --upgrade fpdf2 selenium pandas

Utilisation:
1. Cloner le dépôt ou télécharger les fichiers.
2. Installer les dépendances et s'assurer que `DejaVuSans.ttf` se trouve dans le même répertoire.
3. Exécuter le script en ligne de commande :
       python aio.py
4. Sélectionner la langue, entrer les identifiants de connexion et suivre les instructions.
5. Une fois le scraping réussi, un PDF trié sera généré.

Licence:
Ce projet est sous licence MIT.

--------------------------------------------------
ESPAÑOL
--------------------------------------------------
Descripción:
Este proyecto combina web scraping y generación de PDF en un solo script de Python. Se conecta al sitio "medcanonestop.com", navega a la página de variedades de cannabis, extrae información de los productos (por ejemplo, nombre, genética, contenido de THC y CBD, precio) y la guarda en el archivo `cannabis_strains.json`. Posteriormente, genera una tabla en PDF a partir de los datos extraídos.

Características:
- Interfaz multilingüe (alemán, inglés, francés, español)
- Inicio de sesión automático, incluyendo la aceptación del banner de cookies
- Carga completa y scraping de la página de productos
- Creación de una tabla en PDF ordenada a partir de los datos extraídos

Requisitos:
- Python 3.x
- Google Chrome y ChromeDriver (disponibles en el PATH del sistema)
- Paquetes de Python requeridos: selenium, fpdf2, pandas
- El archivo `DejaVuSans.ttf` debe estar en el mismo directorio que el script

Instalación:
Instala los paquetes necesarios con el siguiente comando:
    pip uninstall --yes pypdf && pip install --upgrade fpdf2 selenium pandas

Uso:
1. Clona el repositorio o descarga los archivos.
2. Instala las dependencias y asegúrate de que `DejaVuSans.ttf` esté en el mismo directorio.
3. Ejecuta el script desde la línea de comandos:
       python aio.py
4. Selecciona tu idioma, introduce tus datos de inicio de sesión y sigue las instrucciones.
5. Tras un scraping exitoso, se generará un PDF ordenado.

Licencia:
Este proyecto se distribuye bajo la Licencia MIT.
