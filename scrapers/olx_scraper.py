"""
OLX Scraper — Sul Catarinense
cloudscraper com fallback ScraperAPI. Logs explícitos de custo por página.
"""
import time, re, os
from bs4 import BeautifulSoup
from datetime import datetime

try:
    import cloudscraper
    _scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
except ImportError:
    _scraper = None

import requests

SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")

BASE = "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao"

OLX_URLS = [
    # ── URL regional — pega todas as cidades grandes de uma vez ───────────────
    # Criciúma, Içara, Tubarão, Araranguá, Forquilhinha, Orleans etc já vêm aqui
    f"{BASE}",

    # ── Região de Turvo e entorno ─────────────────────────────────────────────
    f"{BASE}/outras-cidades/turvo",
    f"{BASE}/outras-cidades/meleiro",
    f"{BASE}/outras-cidades/ermo",
    f"{BASE}/outras-cidades/morro-grande",

    # ── Extremo Sul SC ────────────────────────────────────────────────────────
    f"{BASE}/outras-cidades/sombrio",
    f"{BASE}/outras-cidades/santa-rosa-do-sul",
    f"{BASE}/outras-cidades/sao-joao-do-sul",
    f"{BASE}/outras-cidades/passo-de-torres",
    f"{BASE}/outras-cidades/balneario-gaivota",
    f"{BASE}/outras-cidades/praia-grande",
    f"{BASE}/outras-cidades/timbe-do-sul",
    f"{BASE}/outras-cidades/jacinto-machado",

    # ── Serra / Transição ─────────────────────────────────────────────────────
    f"{BASE}/outras-cidades/lauro-muller",
    f"{BASE}/outras-cidades/sideropolis",
    f"{BASE}/outras-cidades/treviso",
    f"{BASE}/outras-cidades/urussanga",
    f"{BASE}/outras-cidades/nova-veneza",
    f"{BASE}/outras-cidades/cocal-do-sul",
    f"{BASE}/outras-cidades/morro-da-fumaca",

    # ── Litoral Sul ───────────────────────────────────────────────────────────
    f"{BASE}/outras-cidades/balneario-rincao",
    f"{BASE}/outras-cidades/jaguaruna",
    f"{BASE}/outras-cidades/sangao",
    f"{BASE}/outras-cidades/maracaja",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.olx.com.br/",
}

_stats = {"cloudscraper": 0, "scraperapi": 0, "falhou": 0}


def _get_cloudscraper(url):
    if not _scraper:
        return None
    try:
        r = _scraper.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200 and len(r.text) > 5000:
            return r
        print(f"[OLX] cloudscraper → {r.status_code} / {len(r.text)} bytes")
    except Exception as e:
        print(f"[OLX] cloudscraper erro: {e}")
    return None


def _get_scraperapi(url):
    if not SCRAPERAPI_KEY:
        return None
    try:
        payload = {"api_key": SCRAPERAPI_KEY, "url": url, "country_code": "br", "render": "false"}
        r = requests.get("https://api.scraperapi.com/", params=payload, timeout=60)
        if r.status_code == 200 and len(r.text) > 5000:
            return r
        print(f"[OLX] ScraperAPI → {r.status_code}")
    except Exception as e:
        print(f"[OLX] ScraperAPI erro: {e}")
    return None


def _get(url):
    r = _get_cloudscraper(url)
    if r:
        _stats["cloudscraper"] += 1
        print(f"[OLX] ✅ GRÁTIS (cloudscraper)")
        return r
    print(f"[OLX] cloudscraper falhou → tentando ScraperAPI...")
    r = _get_scraperapi(url)
    if r:
        _stats["scraperapi"] += 1
        print(f"[OLX] ⚠️  PAGO (ScraperAPI)")
        return r
    _stats["falhou"] += 1
    return None


def _total_paginas(soup):
    try:
        dl = soup.find("script", {"id": "datalayer"})
        if dl:
            m = re.search(r'"totalOfAds"\s*:\s*(\d+)', dl.string or "")
            if m:
                total = int(m.group(1))
                return max(1, (total + 24) // 25)
        pags = soup.find_all("a", attrs={"data-testid": re.compile(r"pagination")})
        if pags:
            nums = [int(re.search(r'\d+', p.get_text()).group()) for p in pags if re.search(r'\d+', p.get_text())]
            if nums:
                return max(nums)
    except Exception:
        pass
    return 10


def parsear_card(section):
    try:
        link = section.find("a", attrs={"data-testid": "adcard-link"})
        if not link:
            return None
        url = link.get("href", "")
        id_match = re.search(r'-(\d{7,})$', url.rstrip("/"))
        anuncio_id = id_match.group(1) if id_match else ""
        if not anuncio_id:
            return None

        titulo = ""
        titulo_tag = section.find("h2", class_=re.compile(r"olx-adcard__title"))
        if titulo_tag:
            titulo = titulo_tag.get_text(strip=True)

        preco = None
        preco_tag = section.find("h3", class_=re.compile(r"olx-adcard__price"))
        if preco_tag:
            nums = re.sub(r"\D", "", preco_tag.get_text(strip=True))
            preco = int(nums) if nums else None

        cidade, bairro = "", ""
        loc_tag = section.find("p", class_=re.compile(r"olx-adcard__location"))
        if loc_tag:
            partes = [p.strip() for p in loc_tag.get_text(strip=True).split(",")]
            cidade = partes[0] if partes else ""
            bairro = partes[1] if len(partes) > 1 else ""

        area = None
        detail = section.find("div", class_=re.compile(r"olx-adcard__detail"), attrs={"aria-label": True})
        if detail:
            m = re.search(r'(\d+)\s*metros quadrados', detail["aria-label"], re.I)
            if m:
                area = int(m.group(1))
        if area is None:
            m = re.search(r'(\d[\d\.]*)\s*m[²2]', section.get_text(" ", strip=True), re.I)
            if m:
                area = int(re.sub(r"\.", "", m.group(1)))

        foto = None
        media = section.find("div", class_=re.compile(r"olx-adcard__media"))
        if media:
            source = media.find("source", attrs={"type": "image/webp"})
            if source and (source.get("srcset") or source.get("srcSet")):
                foto = (source.get("srcset") or source.get("srcSet") or "").split(",")[0].strip().split(" ")[0]

        return {
            "id":          f"olx_{anuncio_id}",
            "titulo":      titulo[:120],
            "preco":       preco,
            "area_m2":     area,
            "cidade":      cidade,
            "bairro":      bairro,
            "estado":      "SC",
            "url":         url,
            "fonte":       "OLX",
            "foto":        foto,
            "descricao":   "",
            "data_coleta": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"[OLX] Erro ao parsear card: {e}")
        return None


def scrape_olx():
    anuncios = []
    _stats["cloudscraper"] = 0
    _stats["scraperapi"] = 0
    _stats["falhou"] = 0

    for base_url in OLX_URLS:
        total_pags = None
        nome_url = base_url.split("/")[-1] or "regional-sc"
        print(f"\n[OLX] ── {nome_url} ──")

        for pagina in range(1, 21):
            url = f"{base_url}?o={pagina}" if pagina > 1 else base_url
            print(f"[OLX] Página {pagina}...")
            try:
                r = _get(url)
                if not r:
                    print(f"[OLX] Sem resposta — próxima URL")
                    break

                soup = BeautifulSoup(r.text, "lxml")

                if total_pags is None:
                    total_pags = _total_paginas(soup)
                    print(f"[OLX] Total de páginas: {total_pags}")

                cards = soup.find_all("section", class_=re.compile(r"olx-adcard"))
                if not cards:
                    print(f"[OLX] Sem cards — fim desta URL")
                    break

                print(f"[OLX] {len(cards)} cards encontrados")
                for card in cards:
                    a = parsear_card(card)
                    if a:
                        anuncios.append(a)

                if pagina >= total_pags:
                    break

                time.sleep(2.5 + (pagina % 3) * 0.7)

            except Exception as e:
                print(f"[OLX] Erro: {e}")
                break

    vistos = set()
    unicos = [a for a in anuncios if a["id"] not in vistos and not vistos.add(a["id"])]

    print(f"\n[OLX] ── Resumo ──")
    print(f"[OLX] ✅ Grátis (cloudscraper): {_stats['cloudscraper']} páginas")
    print(f"[OLX] ⚠️  Pago  (ScraperAPI):   {_stats['scraperapi']} páginas")
    print(f"[OLX] ❌ Falhou:                {_stats['falhou']} páginas")
    print(f"[OLX] Total: {len(unicos)} anúncios únicos")
    return unicos
