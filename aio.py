#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kombiniertes Skript:
1. Führt den Login durch, navigiert zu den Cannabis-Blüten und scraped die Produktdaten.
2. Speichert die Daten in "cannabis_strains.json".
3. Liest die JSON-Daten ein, fragt nach Sortieroptionen und erstellt eine PDF-Tabelle.
"""

import time
import json
import getpass
from datetime import datetime

# Selenium-Imports für das Scraping
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# PDF-Erstellung Imports
import pandas as pd
from fpdf import FPDF

def scrape_products():
    """Führt den Login durch und scraped die Produktdaten von der Zielseite."""
    print("🚀 Starte WebDriver...")
    driver = webdriver.Chrome()

    print("🌐 Öffne Login-Seite...")
    driver.get("https://medcanonestop.com/wp-login.php")

    # Login-Felder suchen
    try:
        print("🔍 Warte auf Login-Felder...")
        username_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "input_1"))
        )
        password_input = driver.find_element(By.ID, "input_2")
        login_button = driver.find_element(By.ID, "gform_submit_button_0")
        print("✅ Login-Felder gefunden.")
    except Exception as e:
        print("❌ Fehler: Konnte Login-Felder nicht finden!", e)
        driver.quit()
        exit(1)

    # Benutzer gibt Zugangsdaten ein
    username = input("📝 Benutzername/E-Mail: ")
    password = getpass.getpass("🔑 Passwort: ")

    print("📩 Login-Daten eingeben...")
    username_input.send_keys(username)
    password_input.send_keys(password)
    
    # Cookie-Banner schließen, falls vorhanden
    try:
        cookie_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.cmplz-btn.cmplz-accept"))
        )
        cookie_button.click()
        print("✅ Cookie-Banner akzeptiert.")
        time.sleep(2)
    except Exception as e:
        print("ℹ️ Kein Cookie-Banner gefunden oder bereits geschlossen.", e)

    print("🖱️ Klicke auf Login-Button...")
    try:
        login_button.click()
    except Exception as e:
        print("❌ Fehler beim Klicken auf den Login-Button:", e)
        driver.quit()
        exit(1)

    # Nach Login zur Produktseite navigieren
    print("⏳ Warte 5 Sekunden auf Weiterleitung...")
    time.sleep(5)
    current_url = driver.current_url
    print(f"📍 Aktuelle URL nach Login: {current_url}")

    if "mein-konto" in current_url or "dashboard" in current_url:
        print("✅ Erfolgreich eingeloggt! Wechsle zur Produktseite...")
        driver.get("https://medcanonestop.com/cannabisblueten/")
        time.sleep(5)
    else:
        print("⚠️ Keine Weiterleitung erkannt! Manuell zu den Blüten wechseln...")
        driver.get("https://medcanonestop.com/cannabisblueten/")
        time.sleep(5)

    # Alle Produkte laden ("Mehr laden"-Button klicken)
    print("🔄 Lade alle Produkte...")
    while True:
        try:
            load_more_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "load-more-archive"))
            )
            print("🖱️ Klicke auf 'Mehr laden'...")
            driver.execute_script("arguments[0].click();", load_more_button)
            time.sleep(3)
        except Exception:
            print("✅ Alle Produkte geladen!")
            break

    # Überprüfen, ob Produkte geladen wurden
    print("🔍 Suche nach Produkten auf der Seite...")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-info"))
        )
        print("✅ Alle Produkte sichtbar. Starte Scraping...")
    except Exception as e:
        print("❌ Fehler: Produkte konnten nicht gefunden werden. Prüfe die Seite manuell.", e)
        driver.quit()
        exit(1)

    # Produkte scrapen
    products = []
    product_cards = driver.find_elements(By.CLASS_NAME, "product-info")
    if not product_cards:
        print("⚠️ Keine Produkte gefunden. Prüfe die HTML-Struktur.")

    for card in product_cards:
        try:
            # Produktname & Genetik
            name = card.find_element(By.CLASS_NAME, "product-info_title").text
            genetics = card.find_element(By.CLASS_NAME, "genetik").text

            # THC & CBD-Werte (Erster Wert: THC, zweiter Wert: CBD)
            thc_values = card.find_elements(By.CLASS_NAME, "thc-value")
            thc_value = float(thc_values[0].text.replace("%", "").replace(",", ".").strip()) if thc_values else 0.0
            cbd_value = float(thc_values[1].text.replace("%", "").replace(",", ".").strip()) if len(thc_values) > 1 else 0.0

            # Preis
            price_text = card.find_element(By.CLASS_NAME, "price-from").text.replace("Ab ", "").replace("€", "").replace(",", ".").strip()
            price_value = float(price_text) if price_text else 0.0

            # Produktdaten speichern
            products.append({
                "name": name,
                "type": genetics,
                "thc": thc_value,
                "cbd": cbd_value,
                "price_per_g": price_value
            })

            print(f"✅ {name} - {genetics} | THC: {thc_value}%, CBD: {cbd_value}%, Preis: {price_value} €/g")
        except Exception as e:
            print(f"⚠️ Fehler beim Scraping eines Produkts: {e}")

    # Daten in JSON speichern
    with open("cannabis_strains.json", "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    print(f"✅ {len(products)} Produkte erfolgreich gespeichert in 'cannabis_strains.json'.")
    driver.quit()
    return products

def create_pdf():
    """Liest die gespeicherten Produktdaten ein, sortiert sie und erstellt ein PDF."""
    # Daten aus JSON laden
    try:
        with open("cannabis_strains.json", "r", encoding="utf-8") as f:
            products = json.load(f)
    except Exception as e:
        print("❌ Fehler beim Laden der JSON-Daten:", e)
        exit(1)

    if not products:
        print("❌ Keine Daten zum Sortieren gefunden!")
        exit()

    # Menü zur Auswahl der Sortierung
    print("\n🔍 Wie möchtest du die Ergebnisse sortieren?")
    print("1️⃣ Preis pro Gramm THC")
    print("2️⃣ Preis pro Gramm CBD")
    print("3️⃣ Preis pro Gramm")
    print("4️⃣ THC-Gehalt")
    print("5️⃣ CBD-Gehalt")
    print("6️⃣ Name")
    sort_option = input("Gib die Nummer deiner Wahl ein: ").strip()

    sort_keys = {
        "1": ("price_per_g_thc", "Preis pro Gramm THC"),
        "2": ("price_per_g_cbd", "Preis pro Gramm CBD"),
        "3": ("price_per_g", "Preis pro Gramm"),
        "4": ("thc", "THC-Gehalt"),
        "5": ("cbd", "CBD-Gehalt"),
        "6": ("name", "Name")
    }
    sort_data = sort_keys.get(sort_option)
    if not sort_data:
        print("❌ Ungültige Eingabe! Beende das Programm.")
        exit()

    sort_key, sort_text = sort_data

    # Sortierreihenfolge abfragen
    order_option = input("\n🔼 Aufsteigend (a) oder 🔽 Absteigend (d)? (a/d): ").strip().lower()
    reverse_order = order_option == "d"
    order_text = "absteigend" if reverse_order else "aufsteigend"

    # Aktuelles Datum & Uhrzeit holen
    current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
    filename_time = datetime.now().strftime("%d-%m-%Y-%H-%M")

    # Dynamische PDF-Überschrift & Dateiname
    pdf_title = f"MCOS Grassorten vom {current_time} sortiert {order_text} nach {sort_text}"
    pdf_filename = f"mcos-{filename_time}.pdf"

    # Berechnungen für Preis pro Gramm THC & CBD
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

    # Angepasste Sortierung: Falls der Wert numerisch ist, wird er direkt verwendet, ansonsten aus dem formatierten String extrahiert
    try:
        sorted_products = sorted(
            products,
            key=lambda x: float(x[sort_key]) if isinstance(x[sort_key], (int, float))
                else float(x[sort_key].replace(" €", "").strip()),
            reverse=reverse_order
        )
    except Exception as e:
        print("❌ Fehler beim Sortieren der Daten:", e)
        exit(1)

    # Nummerierung hinzufügen
    for i, product in enumerate(sorted_products, start=1):
        product["num"] = i

    # DataFrame für PDF-Tabelle erstellen
    df = pd.DataFrame(sorted_products, columns=["num", "name", "type", "thc", "cbd", "price_per_g", "price_per_g_thc", "price_per_g_cbd"])
    df.columns = ["#", "Name", "Typ", "THC (%)", "CBD (%)", "Preis pro g", "Preis pro g THC", "Preis pro g CBD"]

    # PDF-Erstellung
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Nutze eine UTF-8 kompatible Schriftart (stelle sicher, dass "DejaVuSans.ttf" im selben Verzeichnis liegt)
    pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
    pdf.set_font("DejaVu", "", 12)
    pdf.cell(277, 8, pdf_title, ln=True, align="C")
    pdf.ln(8)

    # Tabellenkopf erstellen
    pdf.set_font("DejaVu", "", 9)
    column_widths = [10, 60, 30, 20, 20, 30, 45, 45]
    columns = df.columns.tolist()
    for i, col in enumerate(columns):
        pdf.cell(column_widths[i], 6, col, border=1, align="C")
    pdf.ln()

    # Tabelleninhalt schreiben
    pdf.set_font("DejaVu", "", 8)
    for _, row in df.iterrows():
        for i, col in enumerate(columns):
            pdf.cell(column_widths[i], 6, str(row[col]), border=1, align="C")
        pdf.ln()

    # PDF speichern
    pdf.output(pdf_filename, "F")
    print(f"\n✅ PDF gespeichert: {pdf_filename}")

def main():
    # Zuerst Produkte scrapen
    products = scrape_products()
    # Anschließend PDF aus den gescrapten Daten erstellen
    create_pdf()

if __name__ == '__main__':
    main()
