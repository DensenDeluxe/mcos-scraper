import json
import pandas as pd
from fpdf import FPDF
from datetime import datetime

# **Daten aus JSON laden**
with open("cannabis_strains.json", "r", encoding="utf-8") as f:
    products = json.load(f)

# **Prüfen, ob Daten vorhanden sind**
if not products:
    print("❌ Keine Daten zum Sortieren gefunden!")
    exit()

# **Menü zur Auswahl der Sortierung**
print("\n🔍 Wie möchtest du die Ergebnisse sortieren?")
print("1️⃣ Preis pro Gramm THC")
print("2️⃣ Preis pro Gramm CBD")
print("3️⃣ Preis pro Gramm")
print("4️⃣ THC-Gehalt")
print("5️⃣ CBD-Gehalt")
print("6️⃣ Name")
sort_option = input("Gib die Nummer deiner Wahl ein: ").strip()

# **Zuordnung der Sortierfelder & Texte**
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

# **Sortierreihenfolge abfragen**
order_option = input("\n🔼 Aufsteigend (a) oder 🔽 Absteigend (d)? (a/d): ").strip().lower()
reverse_order = order_option == "d"
order_text = "absteigend" if reverse_order else "aufsteigend"

# **Aktuelles Datum & Uhrzeit holen**
current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
filename_time = datetime.now().strftime("%d-%m-%Y-%H-%M")

# **Dynamische PDF-Überschrift & Dateiname**
pdf_title = f"MCOS Grassorten vom {current_time} sortiert {order_text} nach {sort_text}"
pdf_filename = f"mcos-{filename_time}.pdf"

# **Preis pro Gramm THC & CBD berechnen & Formatierung auf xx.xx €**
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

# **Daten sortieren**
sorted_products = sorted(products, key=lambda x: float(x[sort_key].replace(" €", "")) if isinstance(x[sort_key], str) and "€" in x[sort_key] else float("inf"), reverse=reverse_order)

# **Nummerierung hinzufügen**
for i, product in enumerate(sorted_products, start=1):
    product["num"] = i

# **Pandas DataFrame für PDF erstellen**
df = pd.DataFrame(sorted_products, columns=["num", "name", "type", "thc", "cbd", "price_per_g", "price_per_g_thc", "price_per_g_cbd"])
df.columns = ["#", "Name", "Typ", "THC (%)", "CBD (%)", "Preis pro g", "Preis pro g THC", "Preis pro g CBD"]

# **PDF-Erstellung mit Unicode-fähiger Schriftart**
pdf = FPDF(orientation="L", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

# **Nutze eine UTF-8 kompatible Schriftart**
pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)

# **Setze dynamische Überschrift (12pt)**
pdf.set_font("DejaVu", "", 12)
pdf.cell(277, 8, pdf_title, ln=True, align="C")
pdf.ln(8)

# **Setze Schriftgröße für Tabellenkopf (9pt)**
pdf.set_font("DejaVu", "", 9)
column_widths = [10, 60, 30, 20, 20, 30, 45, 45]
columns = df.columns.tolist()

# **Header der Tabelle**
for i, col in enumerate(columns):
    pdf.cell(column_widths[i], 6, col, border=1, align="C")
pdf.ln()

# **Setze Schriftgröße für Tabelleninhalte (8pt)**
pdf.set_font("DejaVu", "", 8)

# **Daten in die Tabelle schreiben**
for _, row in df.iterrows():
    for i, col in enumerate(columns):
        value = str(row[col])
        pdf.cell(column_widths[i], 6, value, border=1, align="C")
    pdf.ln()

# **PDF speichern**
pdf.output(pdf_filename, "F")

print(f"\n✅ PDF gespeichert: {pdf_filename}")
