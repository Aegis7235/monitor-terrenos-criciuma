"""
Chaves na Mão Scraper — Sul Catarinense
Estratégia:
  1. Playwright (headless Chrome) — renderiza JS, garante ld+json completo
  2. cloudscraper — fallback grátis, funciona para cidades grandes
  3. ScraperAPI (render=true) — fallback pago
Extrai dados via <script type="application/ld+json"> (Schema.org Offer).
"""
import time, re, os, json
from bs4 import BeautifulSoup
from datetime import datetime

# ── Playwright (opcional) ─────────────────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright
    _playwright_ok = True
except ImportError:
    _playwright_ok = False

# ── cloudscraper (opcional) ───────────────────────────────────────────────────
try:
    import cloudscraper
    _scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
except ImportError:
    _scraper = None

import requests

SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")

BASE_TERRENOS = "https://www.chavesnamao.com.br/terrenos-a-venda"
BASE_CHACARAS = "https://www.chavesnamao.com.br/chacaras-a-venda"

_CIDADES = [
    # Nucleo
    "sc-criciuma", "sc-icara", "sc-forquilhinha", "sc-ararangua",
    # Extremo Sul SC
    "sc-sombrio", "sc-santa-rosa-do-sul", "sc-sao-joao-do-sul",
    "sc-passo-de-torres", "sc-balneario-gaivota", "sc-praia-grande",
    "sc-timbe-do-sul", "sc-jacinto-machado",
    # Regiao de Turvo
    "sc-turvo", "sc-meleiro", "sc-ermo", "sc-morro-grande",
    # Serra / Transicao
    "sc-lauro-muller", "sc-sideropolis", "sc-urussanga",
    "sc-nova-veneza", "sc-cocal-do-sul", "sc-morro-da-fumaca",
    # Litoral Sul
    "sc-balneario-rincao", "sc-jaguaruna", "sc-sangao", "sc-maracaja",
]

CNM_URLS = (
    [f"{BASE_TERRENOS}/{c}/" for c in _CIDADES] +
    [f"{BASE_CHACARAS}/{c}/"  for c in _CIDADES]
)

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

_stats = {"playwright": 0, "cloudscraper": 0, "scraperapi": 0, "falhou": 0}
_pw_instance = None  # reutiliza browser entre chamadas


# ── Playwright ────────────────────────────────────────────────────────────────

def _get_playwright(url):
    """Abre URL com Playwright (headless Chrome), aguarda ld+json carregar."""
    if not _playwright_ok:
        return None
    global _pw_instance
    try:
        if _pw_instance is None:
            _pw_instance = sync_playwright().start()

        browser = _pw_instance.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=HEADERS["User-Agent"],
            locale="pt-BR",
            extra_http_headers={"Accept-Language": HEADERS["Accept-Language"]},
        )
        page = ctx.new_page()

        # Bloqueia imagens/fontes para acelerar
        page.route("**/*.{png,jpg,jpeg,gif,webp,woff,woff2,ttf}", lambda r: r.abort())

        page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # Aguarda até o ld+json com Offer aparecer (max 10s)
        try:
            page.wait_for_function(
                "() => [...document.querySelectorAll('script[type=\"application/ld+json\"]')]"
                ".some(s => s.textContent.includes('itemListElement'))",
                timeout=10000,
            )
        except Exception:
            pass  # continua mesmo se timeout — pode ser página vazia

        html = page.content()
        browser.close()

        if html and len(html) > 3000:
            return html
    except Exception as e:
        print(f"[CNM] Playwright erro: {e}")
        if _pw_instance:
            try:
                _pw_instance.stop()
            except Exception:
                pass
            _pw_instance = None
    return None


# ── cloudscraper ──────────────────────────────────────────────────────────────

def _get_cloudscraper(url):
    if not _scraper:
        return None
    try:
        r = _scraper.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200 and len(r.text) > 3000:
            return r.text
        print(f"[CNM] cloudscraper → {r.status_code} / {len(r.text)} bytes")
    except Exception as e:
        print(f"[CNM] cloudscraper erro: {e}")
    return None


# ── ScraperAPI ────────────────────────────────────────────────────────────────

def _get_scraperapi(url):
    if not SCRAPERAPI_KEY:
        return None
    try:
        # render=true para executar JS como um browser real
        payload = {
            "api_key": SCRAPERAPI_KEY,
            "url": url,
            "country_code": "br",
            "render": "true",
        }
        r = requests.get("https://api.scraperapi.com/", params=payload, timeout=90)
        if r.status_code == 200 and len(r.text) > 3000:
            return r.text
        print(f"[CNM] ScraperAPI → {r.status_code}")
    except Exception as e:
        print(f"[CNM] ScraperAPI erro: {e}")
    return None


# ── Dispatcher ────────────────────────────────────────────────────────────────

def _get_html(url):
    """
    Tenta obter o HTML renderizado em ordem de custo:
      1. Playwright (grátis, JS completo)
      2. cloudscraper (grátis, sem JS)
      3. ScraperAPI render=true (pago)
    Se cloudscraper retornar HTML mas sem itemListElement, descarta e tenta próximo.
    """
    # 1. Playwright
    if _playwright_ok:
        html = _get_playwright(url)
        if html and "itemListElement" in html:
            _stats["playwright"] += 1
            print("[CNM] ✅ GRÁTIS (Playwright)")
            return html
        if html:
            print("[CNM] Playwright: HTML sem itemListElement — tentando cloudscraper")

    # 2. cloudscraper
    html = _get_cloudscraper(url)
    if html and "itemListElement" in html:
        _stats["cloudscraper"] += 1
        print("[CNM] ✅ GRÁTIS (cloudscraper)")
        return html
    if html:
        print("[CNM] cloudscraper: HTML sem itemListElement — tentando ScraperAPI")
    else:
        print("[CNM] cloudscraper falhou — tentando ScraperAPI")

    # 3. ScraperAPI com render
    html = _get_scraperapi(url)
    if html:
        _stats["scraperapi"] += 1
        print("[CNM] ⚠️  PAGO (ScraperAPI render=true)")
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

        foto      = item.get("image", "")
        descricao = item.get("description", "")[:300]

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
            "foto":        foto,
            "descricao":   descricao,
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

        items = data if isinstance(data, list) else [data]
        for obj in items:
            tipo = obj.get("@type", "")

            # Offer direto
            if tipo == "Offer":
                a = parsear_offer(obj)
                if a:
                    offers.append(a)
                continue

            # Qualquer objeto com itemListElement ou offers
            raw_items = obj.get("itemListElement", [])
            if isinstance(raw_items, dict):
                raw_items = [raw_items]
            for sub in raw_items:
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

            raw_offers = obj.get("offers", [])
            if isinstance(raw_offers, dict):
                raw_offers = [raw_offers]
            for sub in raw_offers:
                if isinstance(sub, dict) and sub.get("@type") == "Offer":
                    a = parsear_offer(sub)
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
        print(f"\n[CNM] ── {nome_url} ──")

        for pagina in range(1, 11):
            url = f"{base_url}?pagina={pagina}" if pagina > 1 else base_url
            print(f"[CNM] Pagina {pagina}...")

            try:
                html = _get_html(url)
                if not html:
                    print("[CNM] Sem resposta — proxima cidade")
                    break

                soup = BeautifulSoup(html, "lxml")

                if pagina == 1:
                    total_pags = _total_paginas(soup)
                    print(f"[CNM] Total de paginas estimado: {total_pags}")

                novos_offers = extrair_offers_ldjson(soup)

                if not novos_offers:
                    print("[CNM] Sem offers — fim desta cidade")
                    break

                print(f"[CNM] {len(novos_offers)} offers encontrados")
                antes = len(anuncios)
                anuncios.extend(novos_offers)
                print(f"[CNM] +{len(anuncios) - antes} anuncios")

                if pagina >= total_pags:
                    break

                time.sleep(2.0 + (pagina % 3) * 0.5)

            except Exception as e:
                print(f"[CNM] Erro: {e}")
                break

    # Fecha Playwright se foi usado
    global _pw_instance
    if _pw_instance:
        try:
            _pw_instance.stop()
        except Exception:
            pass
        _pw_instance = None

    # Deduplica
    vistos = set()
    unicos = [a for a in anuncios if a["id"] not in vistos and not vistos.add(a["id"])]

    print(f"\n[CNM] ── Resumo ──")
    print(f"[CNM] ✅ Playwright:    {_stats['playwright']} paginas")
    print(f"[CNM] ✅ cloudscraper:  {_stats['cloudscraper']} paginas")
    print(f"[CNM] ⚠️  ScraperAPI:   {_stats['scraperapi']} paginas")
    print(f"[CNM] ❌ Falhou:        {_stats['falhou']} paginas")
    print(f"[CNM] Total: {len(unicos)} anuncios unicos")
    return unicos
