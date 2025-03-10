#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCOS Multi-Language Scraper & PDF Generator

Dieses Skript führt folgende Schritte aus:
1. Sprachauswahl (Deutsch, Englisch, Französisch, Spanisch)
2. Login auf der Zielseite, Navigation zu den Cannabis-Blüten und Scraping der Produktdaten.
3. Speicherung der Daten in "cannabis_strains.json".
4. Einlesen der Daten, Sortierabfrage und Erstellung einer mehrsprachigen PDF-Tabelle (Dateiname: mcos.pdf).

Voraussetzungen:
- Selenium
- fpdf2
- pandas
- Die Schriftart-Datei "DejaVuSans.ttf" muss im selben Verzeichnis liegen.
"""

import json
import getpass
import time
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
from fpdf import FPDF
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Übersetzungen für die verschiedenen Sprachen inklusive Sortierrichtungen
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "de": {
        "language_selection": "Bitte wählen Sie Ihre Sprache:\n1. Deutsch\n2. Englisch\n3. Französisch\n4. Spanisch\nAuswahl: ",
        "username_prompt": "📝 Benutzername/E-Mail: ",
        "password_prompt": "🔑 Passwort: ",
        "starting_webdriver": "🚀 Starte WebDriver...",
        "open_login": "🌐 Öffne Login-Seite...",
        "waiting_for_login_fields": "🔍 Warte auf Login-Felder...",
        "login_fields_found": "✅ Login-Felder gefunden.",
        "enter_login_data": "📩 Login-Daten eingeben...",
        "click_login_button": "🖱️ Klicke auf Login-Button...",
        "cookie_accepted": "✅ Cookie-Banner akzeptiert.",
        "no_cookie_banner": "ℹ️ Kein Cookie-Banner gefunden oder bereits geschlossen.",
        "wait_for_redirect": "⏳ Warte 5 Sekunden auf Weiterleitung...",
        "current_url": "📍 Aktuelle URL nach Login: {}",
        "logged_in": "✅ Erfolgreich eingeloggt! Wechsle zur Produktseite...",
        "manual_navigation": "⚠️ Keine Weiterleitung erkannt! Manuell zu den Blüten wechseln...",
        "load_all_products": "🔄 Lade alle Produkte...",
        "click_load_more": "🖱️ Klicke auf 'Mehr laden'...",
        "all_products_loaded": "✅ Alle Produkte geladen!",
        "search_products": "🔍 Suche nach Produkten auf der Seite...",
        "all_products_visible": "✅ Alle Produkte sichtbar. Starte Scraping...",
        "no_products_found": "⚠️ Keine Produkte gefunden. Prüfe die HTML-Struktur.",
        "scraping_product": "✅ {} - {} | THC: {}%, CBD: {}%, Preis: {} €/g",
        "scraping_error": "⚠️ Fehler beim Scraping eines Produkts: {}",
        "products_saved": "✅ {} Produkte erfolgreich gespeichert in 'cannabis_strains.json'.",
        "pdf_sort_menu": "\n🔍 Wie möchtest du die Ergebnisse sortieren?\n1️⃣ Preis pro Gramm THC\n2️⃣ Preis pro Gramm CBD\n3️⃣ Preis pro Gramm\n4️⃣ THC-Gehalt\n5️⃣ CBD-Gehalt\n6️⃣ Name\nGib die Nummer deiner Wahl ein: ",
        "invalid_input": "❌ Ungültige Eingabe! Beende das Programm.",
        "sort_order_prompt": "\n🔼 Aufsteigend (a) oder 🔽 Absteigend (d)? (a/d): ",
        "ascending": "aufsteigend",
        "descending": "absteigend",
        "pdf_title": "MCOS Grassorten vom {} sortiert {} nach {}",
        "pdf_saved": "\n✅ PDF gespeichert: {}",
        "col_num": "#",
        "col_name": "Name",
        "col_type": "Typ",
        "col_thc": "THC (%)",
        "col_cbd": "CBD (%)",
        "col_price": "Preis pro g",
        "col_price_thc": "Preis pro g THC",
        "col_price_cbd": "Preis pro g CBD"
    },
    "en": {
        "language_selection": "Please select your language:\n1. German\n2. English\n3. French\n4. Spanish\nChoice: ",
        "username_prompt": "📝 Username/Email: ",
        "password_prompt": "🔑 Password: ",
        "starting_webdriver": "🚀 Starting WebDriver...",
        "open_login": "🌐 Opening login page...",
        "waiting_for_login_fields": "🔍 Waiting for login fields...",
        "login_fields_found": "✅ Login fields found.",
        "enter_login_data": "📩 Entering login data...",
        "click_login_button": "🖱️ Clicking on login button...",
        "cookie_accepted": "✅ Cookie banner accepted.",
        "no_cookie_banner": "ℹ️ No cookie banner found or already closed.",
        "wait_for_redirect": "⏳ Waiting 5 seconds for redirect...",
        "current_url": "📍 Current URL after login: {}",
        "logged_in": "✅ Logged in successfully! Navigating to product page...",
        "manual_navigation": "⚠️ No redirect detected! Manually navigating to product page...",
        "load_all_products": "🔄 Loading all products...",
        "click_load_more": "🖱️ Clicking 'Load more'...",
        "all_products_loaded": "✅ All products loaded!",
        "search_products": "🔍 Searching for products on the page...",
        "all_products_visible": "✅ All products visible. Starting scraping...",
        "no_products_found": "⚠️ No products found. Check HTML structure.",
        "scraping_product": "✅ {} - {} | THC: {}%, CBD: {}%, Price: {} €/g",
        "scraping_error": "⚠️ Error scraping a product: {}",
        "products_saved": "✅ {} products successfully saved in 'cannabis_strains.json'.",
        "pdf_sort_menu": "\n🔍 How would you like to sort the results?\n1️⃣ Price per gram THC\n2️⃣ Price per gram CBD\n3️⃣ Price per gram\n4️⃣ THC content\n5️⃣ CBD content\n6️⃣ Name\nEnter your choice: ",
        "invalid_input": "❌ Invalid input! Exiting.",
        "sort_order_prompt": "\n🔼 Ascending (a) or 🔽 Descending (d)? (a/d): ",
        "ascending": "ascending",
        "descending": "descending",
        "pdf_title": "MCOS Strains from {} sorted {} by {}",
        "pdf_saved": "\n✅ PDF saved: {}",
        "col_num": "#",
        "col_name": "Name",
        "col_type": "Type",
        "col_thc": "THC (%)",
        "col_cbd": "CBD (%)",
        "col_price": "Price per g",
        "col_price_thc": "Price per g THC",
        "col_price_cbd": "Price per g CBD"
    },
    "fr": {
        "language_selection": "Veuillez sélectionner votre langue:\n1. Allemand\n2. Anglais\n3. Français\n4. Espagnol\nChoix: ",
        "username_prompt": "📝 Nom d'utilisateur/Email: ",
        "password_prompt": "🔑 Mot de passe: ",
        "starting_webdriver": "🚀 Démarrage du WebDriver...",
        "open_login": "🌐 Ouverture de la page de connexion...",
        "waiting_for_login_fields": "🔍 Attente des champs de connexion...",
        "login_fields_found": "✅ Champs de connexion trouvés.",
        "enter_login_data": "📩 Saisie des données de connexion...",
        "click_login_button": "🖱️ Clic sur le bouton de connexion...",
        "cookie_accepted": "✅ Bannière de cookie acceptée.",
        "no_cookie_banner": "ℹ️ Aucune bannière de cookie trouvée ou déjà fermée.",
        "wait_for_redirect": "⏳ Attente de 5 secondes pour la redirection...",
        "current_url": "📍 URL actuelle après la connexion: {}",
        "logged_in": "✅ Connecté avec succès! Navigation vers la page produit...",
        "manual_navigation": "⚠️ Aucune redirection détectée! Navigation manuelle vers la page produit...",
        "load_all_products": "🔄 Chargement de tous les produits...",
        "click_load_more": "🖱️ Clic sur 'Charger plus'...",
        "all_products_loaded": "✅ Tous les produits chargés!",
        "search_products": "🔍 Recherche des produits sur la page...",
        "all_products_visible": "✅ Tous les produits sont visibles. Début du scraping...",
        "no_products_found": "⚠️ Aucun produit trouvé. Vérifiez la structure HTML.",
        "scraping_product": "✅ {} - {} | THC: {}%, CBD: {}%, Prix: {} €/g",
        "scraping_error": "⚠️ Erreur lors du scraping d'un produit: {}",
        "products_saved": "✅ {} produits enregistrés avec succès dans 'cannabis_strains.json'.",
        "pdf_sort_menu": "\n🔍 Comment souhaitez-vous trier les résultats?\n1️⃣ Prix par gramme THC\n2️⃣ Prix par gramme CBD\n3️⃣ Prix par gramme\n4️⃣ Teneur en THC\n5️⃣ Teneur en CBD\n6️⃣ Nom\nEntrez votre choix: ",
        "invalid_input": "❌ Entrée invalide! Arrêt du programme.",
        "sort_order_prompt": "\n🔼 Ascendant (a) ou Descendant (d)? (a/d): ",
        "ascending": "ascendant",
        "descending": "descendant",
        "pdf_title": "MCOS Variétés du {} triées {} par {}",
        "pdf_saved": "\n✅ PDF enregistré: {}",
        "col_num": "#",
        "col_name": "Nom",
        "col_type": "Type",
        "col_thc": "THC (%)",
        "col_cbd": "CBD (%)",
        "col_price": "Prix par g",
        "col_price_thc": "Prix par g THC",
        "col_price_cbd": "Prix par g CBD"
    },
    "es": {
        "language_selection": "Por favor seleccione su idioma:\n1. Alemán\n2. Inglés\n3. Francés\n4. Español\nElección: ",
        "username_prompt": "📝 Nombre de usuario/Correo electrónico: ",
        "password_prompt": "🔑 Contraseña: ",
        "starting_webdriver": "🚀 Iniciando WebDriver...",
        "open_login": "🌐 Abriendo página de inicio de sesión...",
        "waiting_for_login_fields": "🔍 Esperando los campos de inicio de sesión...",
        "login_fields_found": "✅ Campos de inicio de sesión encontrados.",
        "enter_login_data": "📩 Ingresando datos de inicio de sesión...",
        "click_login_button": "🖱️ Haciendo clic en el botón de inicio de sesión...",
        "cookie_accepted": "✅ Banner de cookies aceptado.",
        "no_cookie_banner": "ℹ️ No se encontró banner de cookies o ya está cerrado.",
        "wait_for_redirect": "⏳ Esperando 5 segundos para la redirección...",
        "current_url": "📍 URL actual después del inicio de sesión: {}",
        "logged_in": "✅ ¡Inicio de sesión exitoso! Navegando a la página de productos...",
        "manual_navigation": "⚠️ ¡No se detectó redirección! Navegando manualmente a la página de productos...",
        "load_all_products": "🔄 Cargando todos los productos...",
        "click_load_more": "🖱️ Haciendo clic en 'Cargar más'...",
        "all_products_loaded": "✅ ¡Todos los productos cargados!",
        "search_products": "🔍 Buscando productos en la página...",
        "all_products_visible": "✅ Todos los productos visibles. Iniciando scraping...",
        "no_products_found": "⚠️ No se encontraron productos. Verifique la estructura HTML.",
        "scraping_product": "✅ {} - {} | THC: {}%, CBD: {}%, Precio: {} €/g",
        "scraping_error": "⚠️ Error al hacer scraping de un producto: {}",
        "products_saved": "✅ {} productos guardados exitosamente en 'cannabis_strains.json'.",
        "pdf_sort_menu": "\n🔍 ¿Cómo le gustaría ordenar los resultados?\n1️⃣ Precio por gramo de THC\n2️⃣ Precio por gramo de CBD\n3️⃣ Precio por gramo\n4️⃣ Contenido de THC\n5️⃣ Contenido de CBD\n6️⃣ Nombre\nIngrese su elección: ",
        "invalid_input": "❌ Entrada no válida! Saliendo.",
        "sort_order_prompt": "\n🔼 Ascendente (a) o Descendente (d)? (a/d): ",
        "ascending": "ascendente",
        "descending": "descendente",
        "pdf_title": "MCOS Variedades del {} ordenadas {} por {}",
        "pdf_saved": "\n✅ PDF guardado: {}",
        "col_num": "#",
        "col_name": "Nombre",
        "col_type": "Tipo",
        "col_thc": "THC (%)",
        "col_cbd": "CBD (%)",
        "col_price": "Precio por g",
        "col_price_thc": "Precio por g THC",
        "col_price_cbd": "Precio por g CBD"
    }
}


def choose_language() -> str:
    """
    Fordert den Benutzer zur Sprachauswahl auf und gibt den entsprechenden Sprachcode zurück.
    Standard ist Englisch ("en").
    """
    lang_choice = input(TRANSLATIONS["en"]["language_selection"]).strip()
    mapping = {"1": "de", "2": "en", "3": "fr", "4": "es"}
    return mapping.get(lang_choice, "en")


def scrape_products(t: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Führt den Login durch und scraped die Produktdaten.

    Args:
        t: Übersetzungs-Dictionary für die gewählte Sprache.

    Returns:
        Eine Liste von Dictionaries, die die Produktdaten enthalten.
    """
    print(t["starting_webdriver"])
    driver = webdriver.Chrome()

    print(t["open_login"])
    driver.get("https://medcanonestop.com/wp-login.php")

    try:
        print(t["waiting_for_login_fields"])
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "input_1"))
        )
        password_input = driver.find_element(By.ID, "input_2")
        login_button = driver.find_element(By.ID, "gform_submit_button_0")
        print(t["login_fields_found"])
    except Exception as e:
        print(f"{t['invalid_input']} {e}")
        driver.quit()
        exit(1)

    username = input(t["username_prompt"])
    password = getpass.getpass(t["password_prompt"])

    print(t["enter_login_data"])
    username_input.send_keys(username)
    password_input.send_keys(password)

    # Cookie-Banner schließen, falls vorhanden
    try:
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.cmplz-btn.cmplz-accept"))
        )
        cookie_button.click()
        print(t["cookie_accepted"])
        time.sleep(2)
    except Exception as e:
        print(f"{t['no_cookie_banner']} {e}")

    print(t["click_login_button"])
    try:
        login_button.click()
    except Exception as e:
        print(f"{t['invalid_input']} {e}")
        driver.quit()
        exit(1)

    print(t["wait_for_redirect"])
    time.sleep(5)
    current_url = driver.current_url
    print(t["current_url"].format(current_url))

    if "mein-konto" in current_url or "dashboard" in current_url:
        print(t["logged_in"])
        driver.get("https://medcanonestop.com/cannabisblueten/")
        time.sleep(5)
    else:
        print(t["manual_navigation"])
        driver.get("https://medcanonestop.com/cannabisblueten/")
        time.sleep(5)

    print(t["load_all_products"])
    while True:
        try:
            load_more_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "load-more-archive"))
            )
            print(t["click_load_more"])
            driver.execute_script("arguments[0].click();", load_more_button)
            time.sleep(3)
        except Exception:
            print(t["all_products_loaded"])
            break

    print(t["search_products"])
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-info"))
        )
        print(t["all_products_visible"])
    except Exception as e:
        print(f"{t['invalid_input']} {e}")
        driver.quit()
        exit(1)

    products: List[Dict[str, Any]] = []
    product_cards = driver.find_elements(By.CLASS_NAME, "product-info")
    if not product_cards:
        print(t["no_products_found"])

    for card in product_cards:
        try:
            name = card.find_element(By.CLASS_NAME, "product-info_title").text
            genetics = card.find_element(By.CLASS_NAME, "genetik").text

            thc_values = card.find_elements(By.CLASS_NAME, "thc-value")
            thc_value = float(thc_values[0].text.replace("%", "").replace(",", ".").strip()) if thc_values else 0.0
            cbd_value = float(thc_values[1].text.replace("%", "").replace(",", ".").strip()) if len(thc_values) > 1 else 0.0

            price_text = card.find_element(By.CLASS_NAME, "price-from").text.replace("Ab ", "").replace("€", "").replace(",", ".").strip()
            price_value = float(price_text) if price_text else 0.0

            products.append({
                "name": name,
                "type": genetics,
                "thc": thc_value,
                "cbd": cbd_value,
                "price_per_g": price_value
            })

            print(t["scraping_product"].format(name, genetics, thc_value, cbd_value, price_value))
        except Exception as e:
            print(t["scraping_error"].format(e))

    with open("cannabis_strains.json", "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(t["products_saved"].format(len(products)))
    driver.quit()
    return products


def create_pdf(t: Dict[str, str]) -> None:
    """
    Liest die gespeicherten Produktdaten, sortiert sie und erstellt ein PDF.

    Args:
        t: Übersetzungs-Dictionary für die gewählte Sprache.
    """
    try:
        with open("cannabis_strains.json", "r", encoding="utf-8") as f:
            products: List[Dict[str, Any]] = json.load(f)
    except Exception as e:
        print(f"{t['invalid_input']} {e}")
        exit(1)

    if not products:
        print(t["invalid_input"])
        exit()

    sort_option = input(t["pdf_sort_menu"]).strip()
    sort_keys = {
        "1": ("price_per_g_thc", t["col_price_thc"]),
        "2": ("price_per_g_cbd", t["col_price_cbd"]),
        "3": ("price_per_g", t["col_price"]),
        "4": ("thc", t["col_thc"]),
        "5": ("cbd", t["col_cbd"]),
        "6": ("name", t["col_name"])
    }
    sort_data = sort_keys.get(sort_option)
    if not sort_data:
        print(t["invalid_input"])
        exit()
    sort_key, sort_text = sort_data

    order_option = input(t["sort_order_prompt"]).strip().lower()
    reverse_order = order_option == "d"
    order_text = t["descending"] if reverse_order else t["ascending"]

    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    # Der PDF-Titel nutzt nun das aktuelle Datum, aber der Dateiname ist fest "mcos.pdf"
    pdf_title = t["pdf_title"].format(current_time, order_text, sort_text)
    pdf_filename = "mcos.pdf"

    for product in products:
        if product["thc"] > 0:
            product["price_per_g_thc"] = f"{round(product['price_per_g'] / (product['thc'] / 100), 2):.2f} €"
        else:
            product["price_per_g_thc"] = "---"
        if product["cbd"] > 0:
            product["price_per_g_cbd"] = f"{round(product['price_per_g'] / (product['cbd'] / 100), 2):.2f} €"
        else:
            product["price_per_g_cbd"] = "---"
        product["price_per_g"] = f"{product['price_per_g']:.2f} €"

    try:
        sorted_products = sorted(
            products,
            key=lambda x: float(x[sort_key])
            if isinstance(x[sort_key], (int, float))
            else float(x[sort_key].replace(" €", "").strip()),
            reverse=reverse_order
        )
    except Exception as e:
        print(f"{t['invalid_input']} {e}")
        exit(1)

    for i, product in enumerate(sorted_products, start=1):
        product["num"] = i

    df = pd.DataFrame(
        sorted_products,
        columns=[
            "num", "name", "type", "thc", "cbd",
            "price_per_g", "price_per_g_thc", "price_per_g_cbd"
        ]
    )
    df.columns = [
        t["col_num"], t["col_name"], t["col_type"],
        t["col_thc"], t["col_cbd"],
        t["col_price"], t["col_price_thc"], t["col_price_cbd"]
    ]

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.set_font("DejaVu", "", 12)
    pdf.cell(277, 8, pdf_title, ln=True, align="C")
    pdf.ln(8)

    pdf.set_font("DejaVu", "", 9)
    column_widths = [10, 60, 30, 20, 20, 30, 45, 45]
    columns = df.columns.tolist()
    for i, col in enumerate(columns):
        pdf.cell(column_widths[i], 6, col, border=1, align="C")
    pdf.ln()

    pdf.set_font("DejaVu", "", 8)
    for _, row in df.iterrows():
        for i, col in enumerate(columns):
            pdf.cell(column_widths[i], 6, str(row[col]), border=1, align="C")
        pdf.ln()

    pdf.output(pdf_filename, "F")
    print(t["pdf_saved"].format(pdf_filename))


def main() -> None:
    """Hauptfunktion: Führt Sprachauswahl, Scraping und PDF-Erstellung aus."""
    lang = choose_language()
    t = TRANSLATIONS[lang]
    products = scrape_products(t)
    create_pdf(t)


if __name__ == '__main__':
    main()
