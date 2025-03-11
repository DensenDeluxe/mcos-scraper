import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from tqdm import tqdm  # Für Fortschrittsanzeige
from typing import Any, Dict, List, Optional

# Google Drive Upload Imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Konfiguration
MAX_CONCURRENT_REQUESTS = 10
RETRY_ATTEMPTS = 20  # Anzahl der Versuche pro Request
INITIAL_BACKOFF = 1  # Sekunden
SLEEP_INTERVAL = 1  # Wartezeit zwischen den Zyklen (300 Sekunden = 5 Minuten)

# Zielordner für Bilder
IMAGE_FOLDER = "images"
os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Google Drive Ordner-ID (aus deinem Link)
FOLDER_ID = '18eI4kf0h6nTPob9ICYjfw_btXq1Mge8_'

# Custom HTTP-Header und Timeout
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0; +http://example.com)"
}
TIMEOUT = aiohttp.ClientTimeout(total=15)

# Globaler Cache für Produktseiten
product_cache: Dict[str, dict] = {}

# Liste für fehlgeschlagene URLs
failed_urls: List[str] = []

def upload_file_to_drive(file_path: str, mime_type: str = 'application/json') -> None:
    """
    Lädt die angegebene Datei in den festgelegten Google Drive-Ordner hoch.
    Stelle sicher, dass die Datei 'credentials.json' im selben Verzeichnis liegt und der Drive API-Zugriff aktiviert ist.
    """
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    try:
        creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': os.path.basename(file_path),
            'parents': [FOLDER_ID]
        }
        media = MediaFileUpload(file_path, mimetype=mime_type)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"Datei '{os.path.basename(file_path)}' erfolgreich hochgeladen. Drive File ID: {file.get('id')}")
    except Exception as e:
        print(f"Fehler beim Hochladen in Google Drive: {e}")

async def fetch_with_retries(session: aiohttp.ClientSession, url: str, retries: int = RETRY_ATTEMPTS, backoff: int = INITIAL_BACKOFF) -> Optional[str]:
    """Versucht, den Inhalt einer URL abzurufen, und wiederholt dies bei Fehlern."""
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=TIMEOUT, headers=HEADERS) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            if attempt < retries - 1:
                wait_time = backoff * (2 ** attempt)
                await asyncio.sleep(wait_time)
            else:
                print(f"Fehler: {url} konnte nach {retries} Versuchen nicht abgerufen werden: {e}")
                failed_urls.append(url)
                return None

async def fetch_sitemap(session: aiohttp.ClientSession, sitemap_url: str) -> List[str]:
    """Lädt eine XML-Sitemap herunter und extrahiert alle URLs."""
    text = await fetch_with_retries(session, sitemap_url)
    if text is None:
        return []
    root = ET.fromstring(text)
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = []
    for url in root.findall("ns:url", ns):
        loc = url.find("ns:loc", ns)
        if loc is not None:
            urls.append(loc.text)
    return urls

async def scrape_product(session: aiohttp.ClientSession, url: str) -> dict:
    """
    Ruft die Produktseite ab und extrahiert alle relevanten Informationen:
      - Titel (aus <h1 class="product-title">)
      - Kategorie und THC/CBD (aus <div class="ingredients-info">)
      - Attribute (aus <div class="attributes-row">)
      - Preis (aus <p id="price-value">)
      - Bewertungen (aus <div class="average-score">)
      - Wirkungen (aus <div id="effects">)
      - Aroma (aus <div id="aroma">)
      - Terpene (aus <div id="terpenes">)
      - Medizinische Effekte (aus <div id="medical-uses">)
      - Lieferstatus (z. B. "lieferbar")
      - Bild-URL (aus <div class="product-image">)
      - Produktart (wenn ein Link mit href="/cannabisblueten/" vorhanden ist, dann "Cannabisblüten", sonst "Extrakte")
      - Timestamp und URL der Seite.
    """
    if url in product_cache:
        return product_cache[url]

    html = await fetch_with_retries(session, url)
    if html is None:
        return {}
    
    soup = BeautifulSoup(html, 'lxml')
    
    # Titel
    title_tag = soup.find("h1", class_="product-title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    
    # Kategorie und THC/CBD
    ingredients_div = soup.find("div", class_="ingredients-info")
    if ingredients_div:
        paragraphs = ingredients_div.find_all("p")
        category = paragraphs[0].get_text(strip=True) if paragraphs else ""
        thc_span = ingredients_div.find("span", class_="thc-value")
        cbd_span = ingredients_div.find("span", class_="cbd-value")
        try:
            thc_value = float(thc_span.get_text(strip=True).replace("%", "").replace(",", ".")) if thc_span else 0.0
        except Exception:
            thc_value = 0.0
        try:
            cbd_value = float(cbd_span.get_text(strip=True).replace("%", "").replace(",", ".")) if cbd_span else 0.0
        except Exception:
            cbd_value = 0.0
    else:
        category, thc_value, cbd_value = "", 0.0, 0.0

    # Attribute
    attributes = {}
    attributes_div = soup.find("div", class_="attributes-row")
    if attributes_div:
        for wrap in attributes_div.find_all("div", class_="info-text-wrap"):
            p = wrap.find("p")
            if p:
                spans = p.find_all("span")
                if len(spans) >= 2:
                    label = spans[0].get_text(strip=True).rstrip(":")
                    value = spans[1].get_text(strip=True)
                    attributes[label] = value

    # Preis
    price = {}
    price_p = soup.find("p", id="price-value")
    if price_p:
        price_text = price_p.get_text(strip=True)
        parts = price_text.split("-")
        if len(parts) == 2:
            try:
                price_min = float(parts[0].replace("€", "").replace("/g", "").replace(",", ".").strip())
                price_max = float(parts[1].replace("€", "").replace("/g", "").replace(",", ".").strip())
            except Exception:
                price_min, price_max = 0.0, 0.0
            price = {"min": price_min, "max": price_max}
        else:
            try:
                price_value = float(price_text.replace("€", "").replace("/g", "").replace(",", ".").strip())
            except Exception:
                price_value = 0.0
            price = {"value": price_value}
    
    # Bewertungen
    ratings = {}
    avg_score_div = soup.find("div", class_="average-score")
    if avg_score_div:
        for p in avg_score_div.find_all("p"):
            text_info = p.find("span", class_="text-info")
            review_rate = p.find("span", class_="review-rate")
            if text_info and review_rate:
                label = text_info.get_text(strip=True).split(":")[0]
                try:
                    value = float(review_rate.get_text(strip=True))
                except:
                    value = review_rate.get_text(strip=True)
                ratings[label] = value
        total_rating_p = avg_score_div.find("p", class_="total-rating")
        if total_rating_p:
            try:
                total_rating = float(total_rating_p.get_text(strip=True).split(":")[-1].strip())
            except Exception:
                total_rating = None
            ratings["Gesamt"] = total_rating

    # Wirkungen
    effects = []
    effects_div = soup.find("div", id="effects")
    if effects_div:
        for icon_desc in effects_div.find_all("div", class_="icon-desc"):
            p = icon_desc.find("p")
            if p:
                effects.append(p.get_text(strip=True))
    
    # Aroma
    aroma = []
    aroma_div = soup.find("div", id="aroma")
    if aroma_div:
        for icon_desc in aroma_div.find_all("div", class_="icon-desc"):
            p = icon_desc.find("p")
            if p:
                aroma.append(p.get_text(strip=True))
    
    # Terpene
    terpenes = []
    terpenes_div = soup.find("div", id="terpenes")
    if terpenes_div:
        for icon_desc in terpenes_div.find_all("div", class_="icon-desc"):
            span_code = icon_desc.find("span")
            p_name = icon_desc.find("p")
            if span_code and p_name:
                terpenes.append({"code": span_code.get_text(strip=True), "name": p_name.get_text(strip=True)})

    # Medizinische Effekte
    medical_uses = []
    med_uses_div = soup.find("div", id="medical-uses")
    if med_uses_div:
        for icon_desc in med_uses_div.find_all("div", class_="icon-desc"):
            p = icon_desc.find("p")
            if p:
                medical_uses.append(p.get_text(strip=True))
    
    # Lieferstatus
    delivery_status = ""
    delivery_span = soup.find(lambda tag: tag.name == "span" and tag.get_text(strip=True).lower() == "lieferbar")
    if delivery_span:
        delivery_status = delivery_span.get_text(strip=True)
    
    # Bild-URL
    image_url = ""
    image_div = soup.find("div", class_="product-image")
    if image_div:
        img_tag = image_div.find("img")
        if img_tag and img_tag.has_attr("src"):
            image_url = img_tag["src"]

    # Produktart
    product_type_tag = soup.find("a", href="/cannabisblueten/")
    product_type = product_type_tag.get_text(strip=True) if product_type_tag else "Extrakte"
    
    # Timestamp
    timestamp = datetime.now().isoformat()
    
    product_data = {
        "title": title,
        "category": category,
        "thc": thc_value,
        "cbd": cbd_value,
        "attributes": attributes,
        "price": price,
        "ratings": ratings,
        "effects": effects,
        "aroma": aroma,
        "terpenes": terpenes,
        "medical_uses": medical_uses,
        "delivery_status": delivery_status,
        "image_url": image_url,
        "product_type": product_type,
        "timestamp": timestamp,
        "url": url
    }
    product_cache[url] = product_data
    return product_data

async def scrape_product_with_sem(sem: asyncio.Semaphore, session: aiohttp.ClientSession, url: str) -> dict:
    """Wrapper-Funktion zur Begrenzung gleichzeitiger Anfragen."""
    async with sem:
        return await scrape_product(session, url)

async def download_image(session: aiohttp.ClientSession, image_url: str, dest_folder: str) -> Optional[str]:
    """
    Lädt ein Bild herunter und speichert es im angegebenen Ordner.
    Überspringt den Download, wenn die Datei bereits existiert.
    """
    filename = image_url.split("/")[-1].split("?")[0]
    local_path = os.path.join(dest_folder, filename)
    if os.path.exists(local_path):
        return local_path

    try:
        async with session.get(image_url, timeout=TIMEOUT, headers=HEADERS) as response:
            response.raise_for_status()
            content = await response.read()
            with open(local_path, "wb") as f:
                f.write(content)
        return local_path
    except Exception as e:
        print(f"Fehler beim Herunterladen des Bildes {image_url}: {e}")
        return None

async def download_image_with_sem(sem: asyncio.Semaphore, session: aiohttp.ClientSession, image_url: str) -> Optional[str]:
    """Wrapper-Funktion für den Bilddownload zur Begrenzung paralleler Downloads."""
    async with sem:
        return await download_image(session, image_url, IMAGE_FOLDER)

async def download_images_for_products(products: List[Dict[str, Any]]) -> None:
    """
    Lädt Bilder für alle Produkte herunter und aktualisiert die Produktdaten mit den lokalen Pfaden.
    Es wird ein Fortschrittsbalken angezeigt.
    """
    async with aiohttp.ClientSession(timeout=TIMEOUT, headers=HEADERS) as session:
        sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        tasks = [download_image_with_sem(sem, session, product["image_url"])
                 for product in products if product.get("image_url")]
        
        # Fortschrittsanzeige für den Bilddownload
        for _ in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Downloading Images"):
            await _
        
        # Zuordnung der lokalen Bildpfade
        for product in products:
            if product.get("image_url"):
                filename = product["image_url"].split("/")[-1].split("?")[0]
                local_path = os.path.join(IMAGE_FOLDER, filename)
                product["image_path"] = local_path if os.path.exists(local_path) else None

async def run_scraping_cycle() -> None:
    """
    Führt einen kompletten Scraping-Zyklus durch:
      - Abrufen und Auswerten der XML-Sitemaps
      - Scraping der Produktseiten
      - Download der Bilder
      - Speichern der Daten als JSON mit Zeitstempel
      - Upload der JSON-Datei in Google Drive
    """
    global product_cache, failed_urls
    product_cache = {}
    failed_urls = []
    
    sitemap_urls = [
        "https://medcanonestop.com/medcan_product-sitemap.xml",
        "https://medcanonestop.com/medcan_product-sitemap2.xml"
    ]
    async with aiohttp.ClientSession(timeout=TIMEOUT, headers=HEADERS) as session:
        sitemap_tasks = [fetch_sitemap(session, url) for url in sitemap_urls]
        results = await asyncio.gather(*sitemap_tasks)
        product_urls = []
        for urls in results:
            product_urls.extend(urls)
        product_urls = list(set(product_urls))
        print(f"Gesamtzahl der Produkt-URLs: {len(product_urls)}")
        
        sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        tasks = [asyncio.create_task(scrape_product_with_sem(sem, session, url)) for url in product_urls]
        
        products = []
        for task in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Scraping Produkte"):
            result = await task
            if result:
                products.append(result)
    
    await download_images_for_products(products)
    
    timestamp_for_filename = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_filename = f"cannabis_products_{timestamp_for_filename}.json"
    with open(json_filename, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    print(f"Scraping abgeschlossen. Daten wurden in '{json_filename}' gespeichert.")
    
    if failed_urls:
        with open("failed_urls.txt", "w", encoding="utf-8") as f:
            for url in failed_urls:
                f.write(url + "\n")
        print(f"{len(failed_urls)} URLs konnten nicht abgerufen werden. Details in 'failed_urls.txt'.")
    
    # JSON-Datei in Google Drive hochladen
    upload_file_to_drive(json_filename)

async def main_loop() -> None:
    """
    Führt kontinuierlich Scraping-Zyklen durch und lädt die neuen JSON-Dateien in Google Drive hoch.
    """
    while True:
        print("\n--- Neuer Scraping-Zyklus gestartet ---")
        await run_scraping_cycle()
        print(f"Warte {SLEEP_INTERVAL} Sekunden bis zum nächsten Zyklus...\n")
        await asyncio.sleep(SLEEP_INTERVAL)

if __name__ == '__main__':
    asyncio.run(main_loop())
