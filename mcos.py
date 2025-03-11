from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import getpass
import json

print("🚀 Starte WebDriver...")
driver = webdriver.Chrome()

print("🌐 Öffne Login-Seite...")
driver.get("https://medcanonestop.com/wp-login.php")

# **Login durchführen**
try:
    print("🔍 Warte auf Login-Felder...")
    username_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "input_1")))
    password_input = driver.find_element(By.ID, "input_2")
    login_button = driver.find_element(By.ID, "gform_submit_button_0")
    print("✅ Login-Felder gefunden.")
except Exception as e:
    print("❌ Fehler: Konnte Login-Felder nicht finden!", e)
    driver.quit()
    exit(1)

# Benutzer gibt seine Zugangsdaten ein
username = input("📝 Benutzername/E-Mail: ")
password = getpass.getpass("🔑 Passwort: ")

print("📩 Login-Daten eingeben...")
username_input.send_keys(username)
password_input.send_keys(password)

print("🖱️ Klicke auf Login-Button...")
login_button.click()

# **Nach Login zur Produktseite navigieren**
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

# **Klicke wiederholt auf "Mehr laden"-Button, bis alle Produkte sichtbar sind**
print("🔄 Lade alle Produkte...")
while True:
    try:
        load_more_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "load-more-archive"))
        )
        print("🖱️ Klicke auf 'Mehr laden'...")
        driver.execute_script("arguments[0].click();", load_more_button)
        time.sleep(3)  # Warte kurz, bis mehr Produkte geladen wurden
    except:
        print("✅ Alle Produkte geladen!")
        break

# **Überprüfen, ob Produkte geladen wurden**
print("🔍 Suche nach Produkten auf der Seite...")
try:
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "product-info"))
    )
    print("✅ Alle Produkte sichtbar. Starte Scraping...")
except Exception as e:
    print("❌ Fehler: Produkte konnten nicht gefunden werden. Prüfe die Seite manuell.")
    driver.quit()
    exit(1)

# **Produkt-Scraping starten**
products = []
print("🔍 Scanne Produkte...")

product_cards = driver.find_elements(By.CLASS_NAME, "product-info")

if not product_cards:
    print(f"⚠️ Keine Produkte gefunden. Prüfe HTML-Struktur.")

for card in product_cards:
    try:
        # Produktname & Genetik
        name = card.find_element(By.CLASS_NAME, "product-info_title").text
        genetics = card.find_element(By.CLASS_NAME, "genetik").text

        # THC & CBD-Werte (Erster `thc-value` ist THC, zweiter ist CBD)
        thc_values = card.find_elements(By.CLASS_NAME, "thc-value")
        thc_value = float(thc_values[0].text.replace("%", "").replace(",", ".").strip()) if thc_values else 0.0
        cbd_value = float(thc_values[1].text.replace("%", "").replace(",", ".").strip()) if len(thc_values) > 1 else 0.0

        # Preis
        price_text = card.find_element(By.CLASS_NAME, "price-from").text.replace("Ab ", "").replace("€", "").replace(",", ".").strip()
        price_value = float(price_text) if price_text else 0.0

        # Speichere Produktdaten
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

# Daten speichern
with open("cannabis_strains.json", "w", encoding="utf-8") as f:
    json.dump(products, f, ensure_ascii=False, indent=2)

print(f"✅ {len(products)} Produkte erfolgreich gespeichert in 'cannabis_strains.json'.")
driver.quit()
