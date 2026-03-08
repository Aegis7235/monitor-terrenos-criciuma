"""
Chaves na Mao Scraper - Sul Catarinense
Extrai dados via <script type="application/ld+json"> (Schema.org Offer).
Fallback: cloudscraper -> ScraperAPI
"""
import time, re, os, json
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

BASE_CHACARAS = "https://www.chavesnamao.com.br/chacaras-a-venda"

_CIDADES = [
    "sc-criciuma", "sc-icara", "sc-forquilhinha", "sc-ararangua",
    "sc-sombrio", "sc-santa-rosa-do-sul", "sc-sao-joao-do-sul",
    "sc-passo-de-torres", "sc-balneario-gaivota", "sc-praia-grande",
    "sc-timbe-do-sul", "sc-jacinto-machado",
    "sc-turvo", "sc-meleiro", "sc-ermo", "sc-morro-grande",
    "sc-lauro-muller", "sc-sideropolis", "sc-urussanga",
    "sc-nova-veneza", "sc-cocal-do-sul", "sc-morro-da-fumaca",
    "sc-balneario-rincao", "sc-jaguaruna", "sc-sangao", "sc-maracaja",
]

CNM_URLS = [f"{BASE_CHACARAS}/{c}/" for c in _CIDADES]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.chavesnamao.com.br/",
}

_stats = {"cloudscraper": 0, "scraperapi": 0, "falhou": 0}


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _get_cloudscraper(url):
    if not _scraper:
        return None
    try:
        r = _scraper.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200 and len(r.text) > 3000:
            return r.text
        print(f"[CNM] cloudscraper -> {r.status_code} / {len(r.text)} bytes")
    except Exception as e:
        print(f"[CNM] cloudscraper erro: {e}")
    return None


def _get_scraperapi(url):
    if not SCRAPERAPI_KEY:
        return None
    try:
        payload = {"api_key": SCRAPERAPI_KEY, "url": url, "country_code": "br", "render": "false"}
        r = requests.get("https://api.scraperapi.com/", params=payload, timeout=60)
        if r.status_code == 200 and len(r.text) > 3000:
            return r.text
        print(f"[CNM] ScraperAPI -> {r.status_code}")
    except Exception as e:
        print(f"[CNM] ScraperAPI erro: {e}")
    return None


def _get_html(url):
    html = _get_cloudscraper(url)
    if html:
        _stats["cloudscraper"] += 1
        print("[CNM] OK (cloudscraper)")
        return html
    html = _get_scraperapi(url)
    if html:
        _stats["scraperapi"] += 1
        print("[CNM] PAGO (ScraperAPI)")
        return html
    _stats["falhou"] += 1
    return None


# ── Paginacao ─────────────────────────────────────────────────────────────────

def _total_paginas(soup):
    try:
        pags = soup.find_all("a", href=re.compile(r'pagina=\d+'))
        if pags:
            nums = [int(re.search(r'pagina=(\d+)', p["href"]).group(1))
                    for p in pags if re.search(r'pagina=(\d+)', p.get("href", ""))]
            if nums:
                return max(nums)
        total_tag = soup.find(string=re.compile(r'\d+\s+im[oo]ve[li]s?', re.I))
        if total_tag:
            m = re.search(r'(\d+)', total_tag)
            if m:
                return max(1, (int(m.group(1)) + 19) // 20)
    except Exception:
        pass
    return 5


# ── Extracao ld+json ──────────────────────────────────────────────────────────

def _extrair_area_url(url):
    m = re.search(r'-(\d+(?:[.,]\d+)?)m2-', url, re.I)
    if m:
        return int(re.sub(r'[.,]', '', m.group(1)))
    return None


def _extrair_area_floorsize(item_offered):
    fs = item_offered.get("floorSize", {})
    texto = fs.get("unitText", "")
    if texto:
        m = re.search(r'([\d.,]+)', texto)
        if m:
            return int(re.sub(r'[.,]', '', m.group(1)))
    return None


def _extrair_id(url):
    m = re.search(r'/id-(\d+)/', url)
    return m.group(1) if m else None


def parsear_offer(offer):
    try:
        url     = offer.get("url", "")
        titulo  = offer.get("name", "").strip()
        preco_s = offer.get("price", "0")

        if not url or not titulo:
            return None

        anuncio_id = _extrair_id(url)
        if not anuncio_id:
            return None

        try:
            preco = int(float(str(preco_s))) if preco_s else None
            if preco == 0:
                preco = None
        except (ValueError, TypeError):
            preco = None

        item = offer.get("itemOffered", {})

        area = _extrair_area_floorsize(item)
        if not area:
            area = _extrair_area_url(url)
        if not area:
            desc = item.get("description", "")
            m = re.search(r'([\d.,]+)\s*m[²2]', desc, re.I)
            if m:
                area = int(re.sub(r'[.,]', '', m.group(1)))

        addr   = item.get("address", {})
        bairro = addr.get("addressLocality", "").strip()
        regiao = addr.get("addressRegion", "")
        cidade = regiao.split(",")[0].strip() if regiao else ""
        estado = regiao.split(",")[-1].strip() if "," in regiao else "SC"
        rua    = addr.get("streetAddress", "").strip()
        if rua in ("nao disponivel", "nao disponível", ""):
            rua = ""

        geo = item.get("geo", {})
        lat = float(geo.get("latitude",  0) or 0)
        lon = float(geo.get("longitude", 0) or 0)

        return {
            "id":          f"cnm_{anuncio_id}",
            "titulo":      titulo[:120],
            "preco":       preco,
            "area_m2":     area,
            "cidade":      cidade,
            "bairro":      bairro,
            "rua":         rua,
            "estado":      estado,
            "lat":         lat if lat != 0 else None,
            "lon":         lon if lon != 0 else None,
            "url":         url,
            "fonte":       "ChavesNaMao",
            "foto":        item.get("image", ""),
            "descricao":   item.get("description", "")[:300],
            "data_coleta": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"[CNM] Erro ao parsear offer: {e}")
        return None


def extrair_offers_ldjson(soup):
    offers = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        for obj in (data if isinstance(data, list) else [data]):
            tipo = obj.get("@type", "")

            # Offer direto
            if tipo == "Offer":
                a = parsear_offer(obj)
                if a:
                    offers.append(a)
                continue

            # itemListElement (formato usado pelo CNM)
            raw = obj.get("itemListElement", [])
            if isinstance(raw, dict):
                raw = [raw]
            for sub in raw:
                if not isinstance(sub, dict):
                    continue
                if sub.get("@type") == "Offer":
                    a = parsear_offer(sub)
                    if a:
                        offers.append(a)
                elif sub.get("@type") == "ListItem":
                    inner = sub.get("item", {})
                    if isinstance(inner, dict) and inner.get("@type") == "Offer":
                        a = parsear_offer(inner)
                        if a:
                            offers.append(a)

            # offers — pode ser Offer direto, ItemList, ou AggregateOffer
            raw = obj.get("offers", [])
            if isinstance(raw, dict):
                raw = [raw]
            for sub in raw:
                if not isinstance(sub, dict):
                    continue
                if sub.get("@type") == "Offer":
                    a = parsear_offer(sub)
                    if a:
                        offers.append(a)
                elif sub.get("@type") == "ItemList":
                    # RealEstateListing -> offers -> ItemList -> itemListElement -> Offer
                    subitems = sub.get("itemListElement", [])
                    if isinstance(subitems, dict):
                        subitems = [subitems]
                    for subitem in subitems:
                        if not isinstance(subitem, dict):
                            continue
                        if subitem.get("@type") == "Offer":
                            a = parsear_offer(subitem)
                            if a:
                                offers.append(a)
                        elif subitem.get("@type") == "ListItem":
                            inner = subitem.get("item", {})
                            if isinstance(inner, dict) and inner.get("@type") == "Offer":
                                a = parsear_offer(inner)
                                if a:
                                    offers.append(a)

    return offers


# ── Scraper principal ─────────────────────────────────────────────────────────

def scrape_chavesnamao():
    anuncios = []
    for k in _stats:
        _stats[k] = 0

    for base_url in CNM_URLS:
        total_pags = None
        nome_url = base_url.rstrip("/").split("/")[-1] or "sc"
        print(f"\n[CNM] -- {nome_url} --")

        for pagina in range(1, 11):
            url = f"{base_url}?pagina={pagina}" if pagina > 1 else base_url
            print(f"[CNM] Pagina {pagina}...")

            try:
                html = _get_html(url)
                if not html:
                    print("[CNM] Sem resposta -- proxima cidade")
                    break

                soup = BeautifulSoup(html, "lxml")

                if pagina == 1:
                    total_pags = _total_paginas(soup)

                novos_offers = extrair_offers_ldjson(soup)

                if not novos_offers:
                    print("[CNM] Sem offers -- fim desta cidade")
                    break

                antes = len(anuncios)
                anuncios.extend(novos_offers)
                print(f"[CNM] +{len(anuncios) - antes} anuncios")

                if pagina >= total_pags:
                    break

                time.sleep(2.0 + (pagina % 3) * 0.5)

            except Exception as e:
                print(f"[CNM] Erro: {e}")
                break

    vistos = set()
    unicos = [a for a in anuncios if a["id"] not in vistos and not vistos.add(a["id"])]

    print(f"\n[CNM] -- Resumo --")
    print(f"[CNM] cloudscraper: {_stats['cloudscraper']} paginas")
    print(f"[CNM] ScraperAPI:   {_stats['scraperapi']} paginas")
    print(f"[CNM] Falhou:       {_stats['falhou']} paginas")
    print(f"[CNM] Total: {len(unicos)} anuncios unicos")
    return unicos
