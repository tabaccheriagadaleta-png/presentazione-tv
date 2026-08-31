import requests
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8"
}

URLS = {
    "lotto": "https://www.lotto-italia.it/lotto/estratti-ruote",
    "millionday": "https://www.lotto-italia.it/millionday/estratti"
}

def scarica(nome, url):
    print(f"Scarico {nome}: {url}")

    risposta = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    print(f"{nome}: HTTP {risposta.status_code}")
    print(f"{nome}: {len(risposta.text)} caratteri ricevuti")

    risposta.raise_for_status()

    Path(f"debug_{nome}.html").write_text(
        risposta.text,
        encoding="utf-8"
    )

    return risposta.text


def main():
    ora = datetime.now(ZoneInfo("Europe/Rome"))
    print("Avvio aggiornamento:", ora.strftime("%d/%m/%Y %H:%M:%S"))

    lotto_html = scarica(
        "lotto",
        URLS["lotto"]
    )

    millionday_html = scarica(
        "millionday",
        URLS["millionday"]
    )

    print("Download completato correttamente.")
    print("Creati:")
    print("- debug_lotto.html")
    print("- debug_millionday.html")


if __name__ == "__main__":
    main()
