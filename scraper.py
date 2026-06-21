"""
Scraper Euronext - Tableau des cours EBM-DPAR (Blé de Meunerie)
-----------------------------------------------------------------
Récupère le tableau de cours affiché sur la page produit Euronext
(rendu en JavaScript) et l'envoie à un Google Apps Script Web App
qui se charge de l'écrire dans le Google Sheet.

Aucun screenshot ni OCR (lecture directe du DOM rendu par Playwright),
et aucun Google Cloud / compte de service (écriture via Apps Script).
"""

import asyncio
import os
from datetime import datetime, timezone

from playwright.async_api import async_playwright
import requests

URL = "https://live.euronext.com/fr/product/commodities-futures/EBM-DPAR"

# Ces deux valeurs viennent des secrets GitHub (voir scrape.yml) :
# - WEBAPP_URL : l'URL de ton déploiement Apps Script (.../exec)
# - WEBAPP_SECRET : doit être identique à SECRET dans Code.gs
WEBAPP_URL = os.environ["WEBAPP_URL"]
WEBAPP_SECRET = os.environ["WEBAPP_SECRET"]


async def scrape_table():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(URL, wait_until="networkidle")

        # Attendre que le(s) message(s) "En cours de chargement..." disparaissent
        try:
            await page.wait_for_selector(
                "text=En cours de chargement...", state="detached", timeout=20000
            )
        except Exception:
            pass  # si le sélecteur de texte ne matche pas exactement, on continue
        await page.wait_for_timeout(2000)  # marge de sécurité pour le rendu final

        # ⚠️ IMPORTANT : sélecteur à vérifier/ajuster.
        # Ouvre la page dans Chrome, clic droit sur le tableau "Cours" > Inspecter,
        # repère la classe ou l'id du <table> concerné, et remplace "table" ci-dessous
        # par un sélecteur plus précis si plusieurs tableaux existent sur la page
        # (ex: "table.quote-table tbody tr" ou "#block-instrumentquotes table tr").
        rows = await page.locator("table tbody tr").all()

        data = []
        for row in rows:
            cells = await row.locator("td").all_inner_texts()
            if cells:
                data.append([c.strip().replace("\n", " ") for c in cells])

        await browser.close()
        return data


def push_to_sheet(data):
    timestamp = datetime.now(timezone.utc).isoformat(timespec="minutes")
    payload = {"secret": WEBAPP_SECRET, "timestamp": timestamp, "rows": data}
    response = requests.post(WEBAPP_URL, json=payload, timeout=30)
    response.raise_for_status()
    print(response.text)


async def main():
    data = await scrape_table()
    if data:
        push_to_sheet(data)
        print(f"{len(data)} ligne(s) envoyée(s) au Sheet.")
    else:
        print("Aucune donnée trouvée -- vérifie le sélecteur du tableau (voir commentaire ci-dessus).")


if __name__ == "__main__":
    asyncio.run(main())
