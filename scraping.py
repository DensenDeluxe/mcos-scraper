import asyncio
import aiohttp
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import json
import os
import re
import hashlib
from datetime import datetime
from tqdm import tqdm
import threading

# Konfiguration
MAX_CONCURRENT_REQUESTS = 3  # Maximale gleichzeitige Requests
RETRY_ATTEMPTS = 10
INITIAL_BACKOFF = 2
SLEEP_INTERVAL = 600  # Wartezeit zwischen den Loops in Sekunden
SCRAPE_TIMEOUT = 30   # Timeout in Sekunden für jeden scrape_product-Aufruf

# Zielordner für Bilder und JSONs
IMAGE_FOLDER = "images"
JSON_FOLDER = "jsons"
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(JSON_FOLDER, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MyScraper/1.0; +http://example.com)"}
TIMEOUT = aiohttp.ClientTimeout(total=20)

failed_urls = []
success_count = 0
fail_count = 0

# Exit-Event zur sauberen Beendigung
exit_event = threading.Event()

def slugify(value):
    value = str(value).lower()
    value = re.sub(r'[^\w\s-]', '', value)
    value = re.sub(r'[-\s]+', '-', value)
    return value.strip('-_')

def parse_price(price_str):
    price_str = price_str.replace("€", "").strip()
    match = re.match(r"([\d,\.]+)\s*(?:/)?\s*([a-zA-Z]+)", price_str)
    if match:
        numeric_str, unit = match.groups()
        try:
            value = float(numeric_str.replace(",", "."))
        except ValueError:
            value = None
        return {"value": value, "unit": unit}
    else:
        return {"value": None, "unit": None}

def parse_component_value(value_str):
    value_str = value_str.strip()
    match = re.match(r"([\d,\.]+)\s*([a-zA-Z%]+)?", value_str)
    if match:
        numeric_str = match.group(1)
        unit = match.group(2) if match.group(2) else ""
        try:
            value = float(numeric_str.replace(",", "."))
        except ValueError:
            value = None
        return {"value": value, "unit": unit}
    return {"value": None, "unit": ""}

async def fetch_with_retries(session, url):
    for attempt in range(RETRY_ATTEMPTS):
        try:
            async with session.get(url, timeout=TIMEOUT, headers=HEADERS) as response:
                if response.status == 429:
                    await asyncio.sleep((attempt + 1) * 5)
                    continue
                response.raise_for_status()
                return await response.text()
        except Exception:
            await asyncio.sleep((attempt + 1) * INITIAL_BACKOFF)
    failed_urls.append(url)
    return None

async def fetch_sitemap(session, sitemap_url):
    text = await fetch_with_retries(session, sitemap_url)
    if text is None:
        return []
    root = ET.fromstring(text)
    ns = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [url.find("ns:loc", ns).text for url in root.findall("ns:url", ns) if url.find("ns:loc", ns) is not None]

async def scrape_product(session, url):
    html = await fetch_with_retries(session, url)
    if not html:
        return None
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return None

    title_tag = soup.find("h1", class_="product-title")
    title = title_tag.get_text(strip=True) if title_tag else "Unbekannt"

    ingredients_div = soup.find("div", class_="ingredients-info")
    thc_value = {"value": None, "unit": ""}
    cbd_value = {"value": None, "unit": ""}
    if ingredients_div:
        try:
            thc_span = ingredients_div.find("span", class_="thc-value")
            cbd_span = ingredients_div.find("span", class_="cbd-value")
            if thc_span:
                thc_value = parse_component_value(thc_span.get_text(strip=True))
            if cbd_span:
                cbd_value = parse_component_value(cbd_span.get_text(strip=True))
        except Exception:
            pass

    price = {}
    price_p = soup.find("p", id="price-value")
    if price_p:
        price_text = price_p.get_text(strip=True)
        parts = price_text.split("-")
        if len(parts) == 2:
            price["min"] = parse_price(parts[0])
            price["max"] = parse_price(parts[1])
        else:
            price["value"] = parse_price(price_text)

    delivery_status = "Unbekannt"
    delivery_span = soup.find("span", string="lieferbar")
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

    return {
        "title": title,
        "thc": thc_value,
        "cbd": cbd_value,
        "price": price,
        "delivery_status": delivery_status,
        "image_url": image_url,
        "product_type": product_type,
        "timestamp": timestamp,
        "url": url,
    }

async def bounded_scrape_product(sem, session, url):
    async with sem:
        return await scrape_product(session, url)

def update_product_file(product):
    url_hash = hashlib.md5(product["url"].encode()).hexdigest()[:8]
    base_slug = slugify(product.get("title", "product"))
    filename = os.path.join(JSON_FOLDER, f"{base_slug}_{url_hash}.json")
    new_snapshot = product

    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "history" not in data:
            data["history"] = []
        data["history"].append(new_snapshot)
        data["last_updated"] = new_snapshot["timestamp"]
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        data = {
            "title": product.get("title"),
            "url": product.get("url"),
            "product_type": product.get("product_type"),
            "last_updated": product["timestamp"],
            "history": [new_snapshot]
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

async def download_image(session, image_url, local_file):
    try:
        headers = HEADERS.copy()
        async with session.head(image_url, timeout=TIMEOUT, headers=headers) as head_resp:
            head_resp.raise_for_status()
            remote_size_str = head_resp.headers.get("Content-Length")
            if remote_size_str and os.path.exists(local_file):
                remote_size = int(remote_size_str)
                local_size = os.path.getsize(local_file)
                if local_size == remote_size:
                    return
        async with session.get(image_url, timeout=TIMEOUT, headers=headers) as get_resp:
            get_resp.raise_for_status()
            content = await get_resp.read()
            with open(local_file, "wb") as f:
                f.write(content)
    except Exception:
        pass

async def download_images_for_products(products):
    images_to_download = {}
    for product in products:
        image_url = product.get("image_url", "").strip()
        if image_url:
            base = os.path.basename(image_url.split("?")[0])
            if not base:
                base = f"{slugify(product.get('title', 'image'))}.jpg"
            local_file = os.path.join(IMAGE_FOLDER, base)
            images_to_download[image_url] = local_file
    if images_to_download:
        async with aiohttp.ClientSession(timeout=TIMEOUT, headers=HEADERS) as session:
            tasks = [download_image(session, url, local_file) for url, local_file in images_to_download.items()]
            pbar_img = tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Bilder", 
                            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]")
            for _ in pbar_img:
                await _
            pbar_img.close()
        print("Bilder-Download abgeschlossen.")

def update_manifest():
    """Scannt den JSON_FOLDER und speichert alle JSON-Dateinamen in manifest.json im Hauptverzeichnis."""
    files = [f for f in os.listdir(JSON_FOLDER) if f.endswith('.json')]
    files.sort()
    with open("manifest.json", "w", encoding="utf-8") as mf:
        json.dump(files, mf, ensure_ascii=False, indent=2)

async def wait_with_countdown(wait_time):
    """Zeigt einen Countdown im Terminal an."""
    for remaining in range(wait_time, 0, -1):
        print(f"Neuer Scrape-Durchlauf in {remaining} Sekunden...", end="\r")
        await asyncio.sleep(1)
    print(" " * 80, end="\r")

async def run_scraping_cycle():
    global failed_urls, success_count, fail_count
    failed_urls = []
    products_this_cycle = []
    async with aiohttp.ClientSession(timeout=TIMEOUT, headers=HEADERS) as session:
        sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        # 1. Re-Scraping der fehlgeschlagenen URLs (falls vorhanden)
        if os.path.exists("failed_urls.txt"):
            with open("failed_urls.txt", "r", encoding="utf-8") as f:
                failed_list = [line.strip() for line in f if line.strip()]
            if failed_list:
                tasks_failed = [asyncio.create_task(asyncio.wait_for(bounded_scrape_product(sem, session, url), timeout=SCRAPE_TIMEOUT))
                                for url in failed_list]
                if tasks_failed:
                    pbar_fail = tqdm(total=len(tasks_failed), desc="Failed URLs", dynamic_ncols=True,
                                     bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                                     postfix=f"Success: 0, Fail: 0")
                    for future in asyncio.as_completed(tasks_failed):
                        try:
                            product = await future
                        except Exception:
                            product = None
                        if product:
                            products_this_cycle.append(product)
                            update_product_file(product)
                            success_count += 1
                        else:
                            fail_count += 1
                        pbar_fail.postfix = f"Success: {success_count}, Fail: {fail_count}"
                        pbar_fail.update(1)
                    pbar_fail.close()
            if os.path.exists("failed_urls.txt"):
                os.remove("failed_urls.txt")
            print("Re-Scraping fehlgeschlagener URLs abgeschlossen.")
        # 2. Neue URLs aus der Sitemap abarbeiten
        sitemap_urls = [
            "https://medcanonestop.com/medcan_product-sitemap.xml",
            "https://medcanonestop.com/medcan_product-sitemap2.xml"
        ]
        sitemap_tasks = [fetch_sitemap(session, url) for url in sitemap_urls]
        results = await asyncio.gather(*sitemap_tasks)
        product_urls = list(set(sum(results, [])))
        tasks_new = [asyncio.create_task(asyncio.wait_for(bounded_scrape_product(sem, session, url), timeout=SCRAPE_TIMEOUT))
                     for url in product_urls]
        if tasks_new:
            pbar_new = tqdm(total=len(tasks_new), desc="Neue Produkte", dynamic_ncols=True,
                            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
                            postfix=f"Success: {success_count}, Fail: {fail_count}")
            for future in asyncio.as_completed(tasks_new):
                try:
                    product = await future
                except Exception as e:
                    product = None
                    # Fehler werden hier über myDebug ausgegeben
                    print("Task error: " + str(e))
                if product:
                    products_this_cycle.append(product)
                    update_product_file(product)
                    success_count += 1
                else:
                    fail_count += 1
                pbar_new.postfix = f"Success: {success_count}, Fail: {fail_count}"
                pbar_new.update(1)
            pbar_new.close()
            print("Neue Produkte abgeschlossen.")
    # 3. Download der Bilder für alle in diesem Durchlauf gescrapten Produkte
    if products_this_cycle:
        await download_images_for_products(products_this_cycle)
    # 4. Fehlgeschlagene URLs speichern, falls vorhanden
    if failed_urls:
        with open("failed_urls.txt", "w", encoding="utf-8") as f:
            f.writelines(f"{url}\n" for url in failed_urls)
        print("Fehlgeschlagene URLs gespeichert.")
    # 5. Manifest aktualisieren (Output unterdrückt)
    update_manifest()
    print("Scraping-Durchlauf abgeschlossen.")

async def main_loop():
    while not exit_event.is_set():
        await run_scraping_cycle()
        if exit_event.is_set():
            break
        await wait_with_countdown(SLEEP_INTERVAL)

if __name__ == '__main__':
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\nSTRG+C erkannt – Skript wird beendet.")
        exit_event.set()
