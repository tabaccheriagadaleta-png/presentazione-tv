import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9"
}

URL_LOTTO = "https://www.estrazionedellotto.it/ultime-estrazioni-lotto"
URL_10ELOTTO = "https://www.estrazionedellotto.it/10elotto/risultati/archivio-10elotto-2026"
URL_SIMBOLOTTO = "https://www.estrazionedellotto.it/simbolotto/archivio-simbolotto"

RUOTE = [
    "Bari",
    "Cagliari",
    "Firenze",
    "Genova",
    "Milano",
    "Napoli",
    "Palermo",
    "Roma",
    "Torino",
    "Venezia",
    "Nazionale"
]


def scarica(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def testo_pagina(url):
    html = scarica(url)
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(" ", strip=True)


def giorno_settimana(data_str):
    dt = datetime.strptime(data_str, "%d/%m/%Y")

    giorni = [
        "Lunedì",
        "Martedì",
        "Mercoledì",
        "Giovedì",
        "Venerdì",
        "Sabato",
        "Domenica"
    ]

    return giorni[dt.weekday()]


def parse_lotto():
    testo = testo_pagina(URL_LOTTO)

    match = re.search(
        r"Estrazione\s+n\.\s*(\d+)\s+(\d{2}/\d{2}/\d{4})(.*?)(?:Estrazione\s+n\.|$)",
        testo,
        re.S
    )

    if not match:
        raise RuntimeError("Impossibile trovare l'ultima estrazione Lotto")

    concorso = match.group(1)
    data = match.group(2)
    blocco = match.group(3)

    ruote = {}

    for i, ruota in enumerate(RUOTE):
        if i < len(RUOTE) - 1:
            prossima = RUOTE[i + 1]
            pattern = rf"{ruota}\s+((?:\d+\s+){{4}}\d+)\s+{prossima}"
        else:
            pattern = rf"{ruota}\s+((?:\d+\s+){{4}}\d+)"

        m = re.search(pattern, blocco)

        if not m:
            raise RuntimeError(f"Ruota {ruota} non trovata")

        numeri = [int(x) for x in re.findall(r"\d+", m.group(1))]

        if len(numeri) != 5:
            raise RuntimeError(f"Numeri non validi per {ruota}: {numeri}")

        ruote[ruota] = {
            "numeri": numeri,
            "oro": numeri[4]
        }

    return {
        "giorno": giorno_settimana(data),
        "data": data,
        "concorso": concorso,
        "ruote": ruote
    }


def parse_10elotto():
    testo = testo_pagina(URL_10ELOTTO)

    match = re.search(
        r"Estrazione\s+n\.\s*(\d+)\s+(\d{2}/\d{2}/\d{4})(.*?)(?:Estrazione\s+n\.|$)",
        testo,
        re.S
    )

    if not match:
        raise RuntimeError("Impossibile trovare il 10eLotto")

    blocco = match.group(3)

    prima_oro = blocco.split("Numero Oro")[0]
    numeri = [int(x) for x in re.findall(r"\b\d{1,2}\b", prima_oro)]

    # prendiamo gli ultimi 20 numeri prima di "Numero Oro"
    numeri = numeri[-20:]

    m_oro = re.search(
        r"Numero Oro\s+(\d+)",
        blocco
    )

    m_doppio = re.search(
        r"Doppio Oro\s+(\d+)\s+(\d+)",
        blocco
    )

    m_extra = re.search(
        r"Extra\s+((?:\d+\s+){14}\d+)",
        blocco
    )

    if not m_oro:
        raise RuntimeError("Numero Oro 10eLotto non trovato")

    if not m_doppio:
        raise RuntimeError("Doppio Oro non trovato")

    if not m_extra:
        raise RuntimeError("Numeri Extra non trovati")

    extra = [
        int(x)
        for x in re.findall(r"\d+", m_extra.group(1))
    ]

    if len(numeri) != 20:
        raise RuntimeError(
            f"Attesi 20 numeri 10eLotto, trovati {len(numeri)}"
        )

    if len(extra) != 15:
        raise RuntimeError(
            f"Attesi 15 Extra, trovati {len(extra)}"
        )

    return {
        "numeri": numeri,
        "oro": int(m_oro.group(1)),
        "doppio_oro": [
            int(m_doppio.group(1)),
            int(m_doppio.group(2))
        ],
        "extra": extra
    }


def parse_simbolotto():
    testo = testo_pagina(URL_SIMBOLOTTO)

    pattern = (
        r"(\d{1,2})\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|"
        r"luglio|agosto|settembre|ottobre|novembre|dicembre)\s+2026\s+"
        r"(.*?)(?=\d{1,2}\s+(?:gennaio|febbraio|marzo|aprile|maggio|"
        r"giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+2026|$)"
    )

    m = re.search(pattern, testo, re.I | re.S)

    if not m:
        raise RuntimeError("Estrazione Simbolotto non trovata")

    blocco = m.group(2)

    coppie = re.findall(
        r"\b(\d{1,2})\s*-\s*([A-Za-zÀ-ÿ]+)",
        blocco
    )

    coppie = coppie[:5]

    if len(coppie) != 5:
        raise RuntimeError(
            f"Attesi 5 simboli, trovati {len(coppie)}"
        )

    numeri = [int(n) for n, _ in coppie]
    simboli = [nome for _, nome in coppie]

    return {
        "numeri": numeri,
        "simboli": simboli
    }


def main():
    path = Path("data.json")

    if path.exists():
        dati = json.loads(
            path.read_text(encoding="utf-8")
        )
    else:
        dati = {}

    lotto = parse_lotto()
    dieci = parse_10elotto()
    simbolotto = parse_simbolotto()

    dati["lotto"] = lotto
    dati["10elotto"] = dieci
    dati["simbolotto"] = simbolotto

    ora = datetime.now(
        ZoneInfo("Europe/Rome")
    )

    dati["ultimo_aggiornamento"] = ora.strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    path.write_text(
        json.dumps(
            dati,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print("Aggiornamento completato")
    print("Lotto:", lotto["concorso"], lotto["data"])
    print("10eLotto:", len(dieci["numeri"]), "numeri")
    print("Simbolotto:", simbolotto["simboli"])


if __name__ == "__main__":
    main()
