import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from tqdm import tqdm
from typing import Any, Dict, List, Optional
import re
import sys

# Konfiguration
MAX_CONCURRENT_REQUESTS = 10
RETRY_ATTEMPTS = 5          # Anzahl der Versuche pro Request
INITIAL_BACKOFF = 1         # Sekunden
SLEEP_INTERVAL = 3600       # Für das finale Projekt (1 Stunde); zum Testen ggf. einen kleineren Wert setzen

# Zielordner für Bilder und JSONs
IMAGE_FOLDER = "images"
JSON_FOLDER = "jsons"
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(JSON_FOLDER, exist_ok=True)

# Custom HTTP-Header und Timeout
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0; +http://example.com)"
}
TIMEOUT = aiohttp.ClientTimeout(total=15)

# Globaler Cache für Produktseiten und Liste für fehlgeschlagene URLs
product_cache: Dict[str, dict] = {}
failed_urls: List[str] = []

def sanitize_filename(name: str) -> str:
    # Ersetze Leerzeichen durch Unterstriche und entferne nicht-alphanumerische Zeichen
    sanitized = re.sub(r'[^\w\-]', '_', name.strip())
    return sanitized

def should_append(new_data: dict, last_data: dict) -> bool:
    # Vergleiche alle relevanten Schlüssel außer "timestamp"
    keys = list(new_data.keys())
    keys.remove("timestamp")
    for key in keys:
        if new_data.get(key) != last_data.get(key):
            return True
    return False

async def fetch_with_retries(session: aiohttp.ClientSession, url: str,
                             retries: int = RETRY_ATTEMPTS,
                             backoff: int = INITIAL_BACKOFF) -> Optional[str]:
    for attempt in range(retries):
        try:
            async with session.get(url, timeout=TIMEOUT, headers=HEADERS) as response:
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(backoff * (2 ** attempt))
            else:
                print(f"Fehler: {url} konnte nach {retries} Versuchen nicht abgerufen werden: {e}")
                failed_urls.append(url)
                return None

async def fetch_sitemap(session: aiohttp.ClientSession, sitemap_url: str) -> List[str]:
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
    Scraped alle relevanten Informationen:
      - Titel (aus <h1 class="product-title">)
      - Kategorie, THC- und CBD-Werte (aus <div class="ingredients-info">)
      - Weitere Attribute, Preis (Einzelpreis oder Preisspanne)
      - Bewertungen, Wirkungen, Aroma, Terpene, medizinische Effekte
      - Lieferstatus, Bild-URL
      - Produktart: "Cannabisblüten" (falls ein Link mit href="/cannabisblueten/" vorhanden ist) oder "Extrakte"
      - Timestamp und URL
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
                price_min = float(parts[0].replace("€", "").replace("/g", "").replace("/ml", "").replace(",", ".").strip())
                price_max = float(parts[1].replace("€", "").replace("/g", "").replace("/ml", "").replace(",", ".").strip())
            except Exception:
                price_min, price_max = 0.0, 0.0
            price = {"min": price_min, "max": price_max}
        else:
            try:
                price_value = float(price_text.replace("€", "").replace("/g", "").replace("/ml", "").replace(",", ".").strip())
            except Exception:
                price_value = 0.0
            price = {"value": price_value}
    
    # Bewertungen, Wirkungen, Aroma, Terpene, medizinische Effekte (wie im Originalskript)
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

    effects = []
    effects_div = soup.find("div", id="effects")
    if effects_div:
        for icon_desc in effects_div.find_all("div", class_="icon-desc"):
            p = icon_desc.find("p")
            if p:
                effects.append(p.get_text(strip=True))
    
    aroma = []
    aroma_div = soup.find("div", id="aroma")
    if aroma_div:
        for icon_desc in aroma_div.find_all("div", class_="icon-desc"):
            p = icon_desc.find("p")
            if p:
                aroma.append(p.get_text(strip=True))
    
    terpenes = []
    terpenes_div = soup.find("div", id="terpenes")
    if terpenes_div:
        for icon_desc in terpenes_div.find_all("div", class_="icon-desc"):
            span_code = icon_desc.find("span")
            p_name = icon_desc.find("p")
            if span_code and p_name:
                terpenes.append({"code": span_code.get_text(strip=True), "name": p_name.get_text(strip=True)})
    
    medical_uses = []
    med_uses_div = soup.find("div", id="medical-uses")
    if med_uses_div:
        for icon_desc in med_uses_div.find_all("div", class_="icon-desc"):
            p = icon_desc.find("p")
            if p:
                medical_uses.append(p.get_text(strip=True))
    
    delivery_status = ""
    delivery_span = soup.find(lambda tag: tag.name == "span" and tag.get_text(strip=True).lower() == "lieferbar")
    if delivery_span:
        delivery_status = delivery_span.get_text(strip=True)
    
    image_url = ""
    image_div = soup.find("div", class_="product-image")
    if image_div:
        img_tag = image_div.find("img")
        if img_tag and img_tag.has_attr("src"):
            image_url = img_tag["src"]

    product_type_tag = soup.find("a", href="/cannabisblueten/")
    product_type = product_type_tag.get_text(strip=True) if product_type_tag else "Extrakte"
    
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
    async with sem:
        return await scrape_product(session, url)

async def download_image(session: aiohttp.ClientSession, image_url: str, dest_folder: str) -> Optional[str]:
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
    async with sem:
        return await download_image(session, image_url, IMAGE_FOLDER)

async def download_images_for_products(products: List[Dict[str, Any]]) -> None:
    async with aiohttp.ClientSession(timeout=TIMEOUT, headers=HEADERS) as session:
        sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        tasks = [download_image_with_sem(sem, session, product.get("image_url", ""))
                 for product in products if product.get("image_url")]
        for _ in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Downloading Images"):
            await _
        for product in products:
            if product.get("image_url"):
                filename = product["image_url"].split("/")[-1].split("?")[0]
                local_path = os.path.join(IMAGE_FOLDER, filename)
                product["image_path"] = local_path if os.path.exists(local_path) else None

def update_product_json(product_data: dict) -> dict:
    """
    Schreibt (oder aktualisiert) die separate JSON für ein Produkt in JSON_FOLDER.
    Es wird geprüft, ob der neue Datensatz (ohne Timestamp) von dem letzten abweicht.
    Falls nicht – es sei denn, mehr als 1 Stunde ist vergangen – wird kein neuer Eintrag angehängt.
    """
    filename = sanitize_filename(product_data["title"]) + ".json"
    filepath = os.path.join(JSON_FOLDER, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = []
    if history:
        last = history[-1]
        new_ts = datetime.fromisoformat(product_data["timestamp"])
        last_ts = datetime.fromisoformat(last["timestamp"])
        if should_append(product_data, last) or (new_ts - last_ts).total_seconds() >= 3600:
            history.append(product_data)
    else:
        history.append(product_data)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    return history[-1]

async def run_scraping_cycle() -> None:
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
    
    # Erstelle einen Index, der für jede Sorte den aktuellsten Datensatz enthält
    index = {}
    for product in products:
        latest = update_product_json(product)
        index[product["title"]] = latest
    
    with open("index.json", "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print("Scraping abgeschlossen. Index wurde in 'index.json' gespeichert.")
    
    if failed_urls:
        with open("failed_urls.txt", "w", encoding="utf-8") as f:
            for url in failed_urls:
                f.write(url + "\n")
        print(f"{len(failed_urls)} URLs konnten nicht abgerufen werden. Details in 'failed_urls.txt'.")

# Neue Funktion: Wartezeit, die entweder durch normalen Sleep oder durch Tastendruck (Leertaste) beendet werden kann.
async def wait_for_space_or_timeout(timeout: int):
    async def wait_for_space():
        # Diese Implementierung verwendet msvcrt, was unter Windows funktioniert.
        # Unter Unix müsste ein alternativer Ansatz gewählt werden.
        if sys.platform == "win32":
            import msvcrt
            loop = asyncio.get_running_loop()
            def check_space():
                while True:
                    if msvcrt.kbhit():
                        key = msvcrt.getch()
                        if key == b' ':
                            return
            await loop.run_in_executor(None, check_space)
        else:
            # Unter Unix: blockiert input() – dies ist nur ein Platzhalter.
            await asyncio.to_thread(input, "Drücke Leertaste und Enter, um manuell einen neuen Durchlauf zu starten: ")
    # Warte parallel auf Timeout oder Space
    sleep_task = asyncio.create_task(asyncio.sleep(timeout))
    space_task = asyncio.create_task(wait_for_space())
    done, pending = await asyncio.wait([sleep_task, space_task], return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()

async def main_loop() -> None:
    while True:
        print("\n--- Neuer Scraping-Zyklus gestartet ---")
        await run_scraping_cycle()
        print(f"Warte {SLEEP_INTERVAL} Sekunden bis zum nächsten Zyklus oder drücke die Leertaste, um sofort neu zu starten...")
        await wait_for_space_or_timeout(SLEEP_INTERVAL)

if __name__ == '__main__':
    asyncio.run(main_loop())
