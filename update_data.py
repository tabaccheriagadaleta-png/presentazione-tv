import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date, timedelta
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

DATA_FILE = Path("data.json")

URL_MILLIONDAY = "https://www.estrazioni.it/millionday/"
ADM_BASE = (
    "https://www.adm.gov.it/portale/monopoli/giochi/"
    "gioco-del-lotto/lotto_g/lotto_estr"
)

RUOTE = [
    "BARI",
    "CAGLIARI",
    "FIRENZE",
    "GENOVA",
    "MILANO",
    "NAPOLI",
    "PALERMO",
    "ROMA",
    "TORINO",
    "VENEZIA",
    "NAZIONALE"
]

SIMBOLI = {
    1: "Italia",
    2: "Mela",
    3: "Gatta",
    4: "Maiale",
    5: "Mano",
    6: "Luna",
    7: "Vaso",
    8: "Braghe",
    9: "Culla",
    10: "Fagioli",
    11: "Topi",
    12: "Soldato",
    13: "Rana",
    14: "Baule",
    15: "Ragazzo",
    16: "Naso",
    17: "Sfortuna",
    18: "Cerino",
    19: "Risata",
    20: "Festa",
    21: "Lupo",
    22: "Balestra",
    23: "Amo",
    24: "Pizza",
    25: "Natale",
    26: "Elmo",
    27: "Scala",
    28: "Ombrello",
    29: "Diamante",
    30: "Cacio",
    31: "Anguria",
    32: "Disco",
    33: "Elica",
    34: "Testa",
    35: "Uccello",
    36: "Nacchere",
    37: "Piano",
    38: "Pigna",
    39: "Forbici",
    40: "Quadro",
    41: "Buffone",
    42: "Caffè",
    43: "Funghi",
    44: "Prigione",
    45: "Rondine"
}


def carica_dati():
    if DATA_FILE.exists():
        return json.loads(
            DATA_FILE.read_text(encoding="utf-8")
        )

    return {}


def salva_dati(dati):
    DATA_FILE.write_text(
        json.dumps(
            dati,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def giorno_italiano(data_str):
    dt = datetime.strptime(
        data_str,
        "%d/%m/%Y"
    )

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


def get_json(url):
    risposta = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    print(
        "HTTP",
        risposta.status_code,
        url
    )

    risposta.raise_for_status()

    return risposta.json()


def get_text(url, params=None):
    risposta = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=30
    )

    print(
        "HTTP",
        risposta.status_code,
        risposta.url
    )

    risposta.raise_for_status()

    return risposta.text


# --------------------------------------------------
# MILLIONDAY
# --------------------------------------------------

def aggiorna_millionday(dati):
    try:
        html = get_text(URL_MILLIONDAY)

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        estrazioni = []

        for riga in soup.select("table.dati tbody tr"):
            celle = riga.find_all("td")

            if len(celle) < 4:
                continue

            data_it = celle[0].get_text(
                " ",
                strip=True
            )

            concorso_txt = celle[1].get_text(
                " ",
                strip=True
            )

            if not re.fullmatch(
                r"\d{2}/\d{2}/\d{4}",
                data_it
            ):
                continue

            if not concorso_txt.isdigit():
                continue

            numeri = [
                int(x.get_text(strip=True))
                for x in celle[2].select(
                    ".pallina"
                )
            ]

            extra = [
                int(x.get_text(strip=True))
                for x in celle[3].select(
                    ".pallina"
                )
            ]

            if (
                len(numeri) != 5
                or len(extra) != 5
            ):
                continue

            estrazioni.append({
                "data": data_it,
                "concorso": int(
                    concorso_txt
                ),
                "numeri": numeri,
                "extra": extra
            })

        if not estrazioni:
            raise RuntimeError(
                "Nessuna estrazione MillionDAY trovata"
            )

        dati.setdefault(
            "millionday",
            {}
        )

        # Trova la data più recente
        data_recente = max(
            datetime.strptime(
                e["data"],
                "%d/%m/%Y"
            )
            for e in estrazioni
        ).strftime("%d/%m/%Y")

        oggi = [
            e
            for e in estrazioni
            if e["data"] == data_recente
        ]

        # Ordine concorso crescente:
        # primo = 13:00
        # secondo = 20:30
        oggi.sort(
            key=lambda e: e["concorso"]
        )

        if len(oggi) >= 1:
            e13 = oggi[0]

            dati["millionday"]["13"] = {
                "giorno": giorno_italiano(
                    e13["data"]
                ),
                "data": e13["data"],
                "concorso": e13["concorso"],
                "numeri": e13["numeri"],
                "extra": e13["extra"]
            }

        if len(oggi) >= 2:
            e20 = oggi[1]

            dati["millionday"]["2030"] = {
                "giorno": giorno_italiano(
                    e20["data"]
                ),
                "data": e20["data"],
                "concorso": e20["concorso"],
                "numeri": e20["numeri"],
                "extra": e20["extra"]
            }

        print(
            "MillionDAY:",
            data_recente,
            "- estrazioni disponibili:",
            len(oggi)
        )

    except Exception as e:
        print(
            "ATTENZIONE MillionDAY:",
            repr(e)
        )

# --------------------------------------------------
# CALCOLO NUMERO CONCORSO LOTTO
# --------------------------------------------------

def concorso_teorico_anno(
    giorno
):
    inizio = date(
        giorno.year,
        1,
        1
    )

    totale = 0
    d = inizio

    while d <= giorno:
        # martedì, giovedì,
        # venerdì, sabato
        if d.weekday() in (
            1,
            3,
            4,
            5
        ):
            totale += 1

        d += timedelta(days=1)

    return totale


# --------------------------------------------------
# ADM LOTTO + SIMBOLOTTO
# --------------------------------------------------

def scarica_concorso_adm(
    anno,
    concorso
):
    params = {
        "_it_sogei_wda_web_portlet_WebDisplayAamsPortlet_anno":
            anno,

        "_it_sogei_wda_web_portlet_WebDisplayAamsPortlet_prog":
            concorso,

        "p_p_cacheability":
            "cacheLevelPage",

        "p_p_id":
            "it_sogei_wda_web_portlet_WebDisplayAamsPortlet",

        "p_p_lifecycle":
            "2",

        "p_p_mode":
            "view",

        "p_p_state":
            "normal"
    }

    html = get_text(
        ADM_BASE,
        params=params
    )

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    testo = soup.get_text(
        " ",
        strip=True
    )

    if (
        "Estrazione n" not in testo
        and "RUOTA" not in testo
    ):
        raise RuntimeError(
            "Pagina ADM non valida"
        )

    return testo


def parse_adm(
    testo
):
    intestazione = re.search(
        r"Estrazione\s+n[°.]?\s*"
        r"(\d+)\s+del\s+"
        r"(\d{2}/\d{2}/\d{4})",
        testo,
        re.I
    )

    if not intestazione:
        raise RuntimeError(
            "Numero concorso/data ADM non trovati"
        )

    concorso = intestazione.group(1)
    data_estrazione = intestazione.group(2)

    ruote = {}

    for i, ruota in enumerate(RUOTE):

        if i < len(RUOTE) - 1:
            prossima = RUOTE[i + 1]

            pattern = (
                rf"{ruota}\s+"
                rf"(\d{{1,2}})\s+"
                rf"(\d{{1,2}})\s+"
                rf"(\d{{1,2}})\s+"
                rf"(\d{{1,2}})\s+"
                rf"(\d{{1,2}})"
                rf".*?"
                rf"Numero Oro:\s*"
                rf"(\d{{1,2}})"
                rf".*?"
                rf"{prossima}"
            )

        else:
            pattern = (
                rf"{ruota}\s+"
                rf"(\d{{1,2}})\s+"
                rf"(\d{{1,2}})\s+"
                rf"(\d{{1,2}})\s+"
                rf"(\d{{1,2}})\s+"
                rf"(\d{{1,2}})"
                rf".*?"
                rf"Numero Oro:\s*"
                rf"(\d{{1,2}})"
            )

        m = re.search(
            pattern,
            testo,
            re.I | re.S
        )

        if not m:
            raise RuntimeError(
                f"Ruota ADM non trovata: {ruota}"
            )

        numeri = [
            int(m.group(1)),
            int(m.group(2)),
            int(m.group(3)),
            int(m.group(4)),
            int(m.group(5))
        ]

        oro = int(
            m.group(6)
        )

        ruote[
            ruota.title()
        ] = {
            "numeri": numeri,
            "oro": oro
        }

    m_simbolotto = re.search(
        r"Simbolotto.*?"
        r"(\d{1,2})\s+"
        r"(\d{1,2})\s+"
        r"(\d{1,2})\s+"
        r"(\d{1,2})\s+"
        r"(\d{1,2})",
        testo,
        re.I | re.S
    )

    if not m_simbolotto:
        raise RuntimeError(
            "Simbolotto ADM non trovato"
        )

    simbolotto_numeri = [
        int(m_simbolotto.group(i))
        for i in range(1, 6)
    ]

    simbolotto_simboli = [
        SIMBOLI[n]
        for n in simbolotto_numeri
    ]

    return {
        "lotto": {
            "giorno":
                giorno_italiano(
                    data_estrazione
                ),

            "data":
                data_estrazione,

            "concorso":
                concorso,

            "ruote":
                ruote
        },

        "simbolotto": {
            "numeri":
                simbolotto_numeri,

            "simboli":
                simbolotto_simboli
        }
    }


def aggiorna_lotto_adm(
    dati
):
    oggi = datetime.now(
        ZoneInfo("Europe/Rome")
    ).date()

    teorico = concorso_teorico_anno(
        oggi
    )

    # Proviamo alcuni concorsi
    # attorno a quello teorico.
    candidati = [
        teorico + 2,
        teorico + 1,
        teorico,
        teorico - 1,
        teorico - 2,
        teorico - 3,
        teorico - 4
    ]

    ultimo_valido = None

    for concorso in candidati:

        if concorso <= 0:
            continue

        try:
            testo = scarica_concorso_adm(
                oggi.year,
                concorso
            )

            risultato = parse_adm(
                testo
            )

            data_dt = datetime.strptime(
                risultato["lotto"]["data"],
                "%d/%m/%Y"
            ).date()

            # niente estrazioni future
            if data_dt > oggi:
                continue

            if (
                ultimo_valido is None
                or data_dt >
                ultimo_valido[0]
            ):
                ultimo_valido = (
                    data_dt,
                    risultato
                )

        except Exception as e:
            print(
                f"Concorso {concorso}:",
                repr(e)
            )

    if ultimo_valido is None:
        raise RuntimeError(
            "Nessun concorso ADM valido"
        )

    risultato = ultimo_valido[1]

    dati["lotto"] = (
        risultato["lotto"]
    )

    dati["simbolotto"] = (
        risultato["simbolotto"]
    )

    print(
        "Lotto ADM:",
        dati["lotto"]["concorso"],
        dati["lotto"]["data"]
    )


# --------------------------------------------------
# 10ELOTTO CALCOLATO DAL LOTTO
# --------------------------------------------------

def calcola_10elotto(
    dati
):
    lotto = dati.get(
        "lotto",
        {}
    )

    ruote = lotto.get(
        "ruote",
        {}
    )

    cittadine = [
        "Bari",
        "Cagliari",
        "Firenze",
        "Genova",
        "Milano",
        "Napoli",
        "Palermo",
        "Roma",
        "Torino",
        "Venezia"
    ]

    if any(
        r not in ruote
        for r in cittadine
    ):
        print(
            "10eLotto non calcolato:"
            " Lotto incompleto"
        )
        return

    estratti = {
        r: ruote[r]["numeri"]
        for r in cittadine
    }

    principali = []

    # prima e seconda colonna,
    # poi successive se ci sono duplicati
    for colonna in range(5):

        for ruota in cittadine:

            n = estratti[ruota][
                colonna
            ]

            if n not in principali:
                principali.append(n)

            if len(principali) == 20:
                break

        if len(principali) == 20:
            break

    principali = sorted(
        principali[:20]
    )

    bari = estratti["Bari"]

    oro = bari[0]

    doppio_oro = [
        bari[0],
        bari[1]
    ]

    # Gli Extra li lasciamo invariati
    # se già presenti, finché non
    # validiamo definitivamente la
    # regola automatica.
    vecchio = dati.get(
        "10elotto",
        {}
    )

    dati["10elotto"] = {
        "numeri":
            principali,

        "oro":
            oro,

        "doppio_oro":
            doppio_oro,

        "extra":
            vecchio.get(
                "extra",
                []
            )
    }

    print(
        "10eLotto principali calcolati"
    )


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    dati = carica_dati()

    print(
        "=== AGGIORNAMENTO ESTRAZIONI ==="
    )

    aggiorna_millionday(
        dati
    )

    try:
        aggiorna_lotto_adm(
            dati
        )

        calcola_10elotto(
            dati
        )

    except Exception as e:
        print(
            "ATTENZIONE Lotto/ADM:",
            repr(e)
        )

    ora = datetime.now(
        ZoneInfo("Europe/Rome")
    )

    dati[
        "ultimo_aggiornamento"
    ] = ora.strftime(
        "%d/%m/%Y %H:%M:%S"
    )

    salva_dati(
        dati
    )

    print(
        "data.json salvato"
    )


if __name__ == "__main__":
    main()
