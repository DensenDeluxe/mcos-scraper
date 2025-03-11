import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime
from tqdm import tqdm
from typing import Any, Dict, List, Optional

# Konfiguration
MAX_CONCURRENT_REQUESTS = 10
RETRY_ATTEMPTS = 5
INITIAL_BACKOFF = 1
SLEEP_INTERVAL = 300  # 5 Minuten zwischen den Zyklen

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; PriceTracker/1.0; +http://example.com)"
}
TIMEOUT = aiohttp.ClientTimeout(total=15)

# Globaler Cache und Liste für fehlgeschlagene URLs
product_cache: Dict[str, Any] = {}
failed_urls: List[str] = []

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

async def scrape_product(session: aiohttp.ClientSession, url: str) -> Optional[Dict[str, Any]]:
    """
    Ruft die Produktseite ab und extrahiert:
      - Den Produktnamen (aus <h1 class="product-title">)
      - Den Preis (Preisspanne oder Einzelpreis; bei "Keine Verfugbarkeit" als None)
      - Den THC-Wert (aus <span class="thc-value"> innerhalb eines div.ingredients-info)
      - Einen Timestamp
    """
    if url in product_cache:
        return product_cache[url]
    
    html = await fetch_with_retries(session, url)
    if html is None:
        return None

    soup = BeautifulSoup(html, 'lxml')

    # Produktname
    title_tag = soup.find("h1", class_="product-title")
    title = title_tag.get_text(strip=True) if title_tag else None
    if not title:
        return None

    # Preisinformationen
    price = None
    price_p = soup.find("p", id="price-value")
    if price_p:
        if price_p.find("span", class_="unknown-availability"):
            price = None
        else:
            price_inner = price_p.find("span", class_="price-inner")
            if price_inner:
                price_text = price_inner.get_text(separator=" ", strip=True)
                price_text = price_text.replace("€", "").replace("/g", "").replace("/ml", "").strip()
                if "-" in price_text:
                    parts = price_text.split("-")
                    try:
                        min_price = float(parts[0].replace(",", ".").strip())
                        max_price = float(parts[1].replace(",", ".").strip())
                        price = {"min": min_price, "max": max_price}
                    except Exception:
                        price = None
                else:
                    try:
                        single_price = float(price_text.replace(",", ".").strip())
                        price = {"value": single_price}
                    except Exception:
                        price = None

    # THC-Wert extrahieren (als Prozentwert, z.B. 22.5 für 22,5%)
    thc_value = None
    ingredients_div = soup.find("div", class_="ingredients-info")
    if ingredients_div:
        thc_span = ingredients_div.find("span", class_="thc-value")
        if thc_span:
            try:
                thc_value = float(thc_span.get_text(strip=True).replace("%", "").replace(",", "."))
            except Exception:
                thc_value = None

    timestamp = datetime.now().isoformat()
    product_data = {"title": title, "price": price, "thc": thc_value, "timestamp": timestamp}
    product_cache[url] = product_data
    return product_data

async def scrape_product_with_sem(sem: asyncio.Semaphore, session: aiohttp.ClientSession, url: str) -> Optional[Dict[str, Any]]:
    async with sem:
        return await scrape_product(session, url)

def update_prices_json(new_products: List[Dict[str, Any]]) -> None:
    data = {}
    if os.path.exists("prices.json"):
        try:
            with open("prices.json", "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden von prices.json: {e}")
    
    for product in new_products:
        if product and "title" in product:
            title = product["title"]
            entry = {
                "timestamp": product["timestamp"],
                "price": product["price"],
                "thc": product["thc"]
            }
            if title in data:
                data[title].append(entry)
            else:
                data[title] = [entry]
    
    with open("prices.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Preisdaten wurden in 'prices.json' aktualisiert.")

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
    
    update_prices_json(products)
    
    if failed_urls:
        with open("failed_urls.txt", "w", encoding="utf-8") as f:
            for url in failed_urls:
                f.write(url + "\n")
        print(f"{len(failed_urls)} URLs konnten nicht abgerufen werden. Details in 'failed_urls.txt'.")

async def main_loop() -> None:
    while True:
        print("\n--- Neuer Scraping-Zyklus gestartet ---")
        await run_scraping_cycle()
        print(f"Warte {SLEEP_INTERVAL} Sekunden bis zum nächsten Zyklus...\n")
        await asyncio.sleep(SLEEP_INTERVAL)

if __name__ == '__main__':
    asyncio.run(main_loop())
