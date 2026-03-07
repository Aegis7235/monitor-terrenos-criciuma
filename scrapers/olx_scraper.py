"""
OLX Scraper — sem ScraperAPI
Usa cloudscraper + headers realistas para bypass do Cloudflare.
Fallback automático para ScraperAPI se cloudscraper falhar (opcional).
"""
import json, time, re, os
from bs4 import BeautifulSoup
from datetime import datetime

try:
    import cloudscraper
    _scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
except ImportError:
    import requests as _scraper_fallback
    _scraper = None

import requests

# Opcional: só usado se cloudscraper falhar e a chave estiver definida
SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")

OLX_URLS = [
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/criciuma",
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/icara",
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/forquilhinha",
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/nova-veneza",
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/cocal-do-sul",
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/morro-da-fumaca",
    # Expanda adicionando mais cidades abaixo:
    # "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/sideropolis",
    # "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/maracaja",
    # "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/sangao",
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


def _get_cloudscraper(url):
    """Tenta buscar com cloudscraper (gratuito, bypassa Cloudflare)."""
    try:
        r = _scraper.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200 and len(r.text) > 5000:
            return r
        print(f"[OLX] cloudscraper retornou {r.status_code} / {len(r.text)} bytes")
    except Exception as e:
        print(f"[OLX] cloudscraper erro: {e}")
    return None


def _get_scraperapi(url):
    """Fallback pago — só usa se SCRAPERAPI_KEY estiver definida."""
    if not SCRAPERAPI_KEY:
        return None
    try:
        payload = {"api_key": SCRAPERAPI_KEY, "url": url, "country_code": "br", "render": "false"}
        r = requests.get("https://api.scraperapi.com/", params=payload, timeout=60)
        if r.status_code == 200:
            print("[OLX] ⚠️  Usou ScraperAPI (fallback pago)")
            return r
    except Exception as e:
        print(f"[OLX] ScraperAPI erro: {e}")
    return None


def _get(url):
    """Tenta cloudscraper primeiro; cai no ScraperAPI só se necessário."""
    r = _get_cloudscraper(url)
    if r:
        return r
    print("[OLX] cloudscraper falhou → tentando ScraperAPI...")
    return _get_scraperapi(url)


def _total_paginas(soup):
    try:
        dl = soup.find("script", {"id": "datalayer"})
        if dl:
            m = re.search(r'"totalOfAds"\s*:\s*(\d+)', dl.string or "")
            if m:
                total = int(m.group(1))
                return max(1, (total + 24) // 25)
        # Fallback: conta paginação no HTML
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

    for base_url in OLX_URLS:
        total_pags = None

        for pagina in range(1, 11):
            url = f"{base_url}?o={pagina}" if pagina > 1 else base_url
            print(f"[OLX] Página {pagina}: {url}")
            try:
                r = _get(url)
                if not r:
                    print(f"[OLX] Sem resposta — encerrando esta URL")
                    break
                if r.status_code != 200:
                    print(f"[OLX] HTTP {r.status_code} — encerrando")
                    break

                soup = BeautifulSoup(r.text, "lxml")

                if total_pags is None:
                    total_pags = _total_paginas(soup)
                    print(f"[OLX] Total estimado de páginas: {total_pags}")

                cards = soup.find_all("section", class_=re.compile(r"olx-adcard"))
                if not cards:
                    print(f"[OLX] Nenhum card na página {pagina} — fim")
                    break

                print(f"[OLX] Página {pagina}: {len(cards)} cards")
                for card in cards:
                    a = parsear_card(card)
                    if a:
                        anuncios.append(a)

                if pagina >= total_pags:
                    break

                # Delay aleatório para não parecer bot
                time.sleep(2.5 + (pagina % 3) * 0.7)

            except Exception as e:
                print(f"[OLX] Erro: {e}")
                break

    vistos = set()
    unicos = [a for a in anuncios if a["id"] not in vistos and not vistos.add(a["id"])]
    print(f"[OLX] Total: {len(unicos)} anúncios únicos")
    return unicos
