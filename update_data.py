from playwright.sync_api import sync_playwright
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

URLS = {
    "lotto": "https://www.lotto-italia.it/lotto/estratti-ruote",
    "millionday": "https://www.lotto-italia.it/millionday/estratti"
}

def acquisisci(page, nome, url):
    print(f"Apro {nome}: {url}")

    page.goto(url, wait_until="domcontentloaded", timeout=90000)

    # aspettiamo che il sito carichi i risultati dinamici
    page.wait_for_timeout(10000)

    testo = page.locator("body").inner_text()

    Path(f"debug_rendered_{nome}.txt").write_text(
        testo,
        encoding="utf-8"
    )

    html = page.content()

    Path(f"debug_rendered_{nome}.html").write_text(
        html,
        encoding="utf-8"
    )

    print(f"{nome}: pagina caricata correttamente")


def main():
    ora = datetime.now(ZoneInfo("Europe/Rome"))

    print(
        "Avvio:",
        ora.strftime("%d/%m/%Y %H:%M:%S")
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page(
            viewport={"width": 1920, "height": 1080},
            locale="it-IT"
        )

        acquisisci(
            page,
            "lotto",
            URLS["lotto"]
        )

        acquisisci(
            page,
            "millionday",
            URLS["millionday"]
        )

        browser.close()

    print("Acquisizione completata.")


if __name__ == "__main__":
    main()
