"""
Chaves na Mão Scraper — Sul Catarinense
cloudscraper com fallback ScraperAPI.
Extrai dados via <script type="application/ld+json"> (Schema.org Offer),
estratégia muito mais robusta que parsear HTML/Next.js.
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

BASE_TERRENOS = "https://www.chavesnamao.com.br/terrenos-a-venda"
BASE_CHACARAS = "https://www.chavesnamao.com.br/chacaras-a-venda"

_CIDADES = [
    # ── Núcleo ────────────────────────────────────────────────────────────────
    "sc-criciuma", "sc-icara", "sc-forquilhinha", "sc-ararangua",

    # ── Extremo Sul SC ────────────────────────────────────────────────────────
    "sc-sombrio", "sc-santa-rosa-do-sul", "sc-sao-joao-do-sul",
    "sc-passo-de-torres", "sc-balneario-gaivota", "sc-praia-grande",
    "sc-timbe-do-sul", "sc-jacinto-machado",

    # ── Região de Turvo ───────────────────────────────────────────────────────
    "sc-turvo", "sc-meleiro", "sc-ermo", "sc-morro-grande",

    # ── Serra / Transição ─────────────────────────────────────────────────────
    "sc-lauro-muller", "sc-sideropolis", "sc-urussanga",
    "sc-nova-veneza", "sc-cocal-do-sul", "sc-morro-da-fumaca",

    # ── Litoral Sul ───────────────────────────────────────────────────────────
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

_stats = {"cloudscraper": 0, "scraperapi": 0, "falhou": 0}


# ── HTTP ──────────────────────────────────────────────────────────────────────

def _get_cloudscraper(url):
    if not _scraper:
        return None
    try:
        r = _scraper.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200 and len(r.text) > 3000:
            return r
        print(f"[CNM] cloudscraper → {r.status_code} / {len(r.text)} bytes")
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
            return r
        print(f"[CNM] ScraperAPI → {r.status_code}")
    except Exception as e:
        print(f"[CNM] ScraperAPI erro: {e}")
    return None


def _get(url):
    r = _get_cloudscraper(url)
    if r:
        _stats["cloudscraper"] += 1
        print(f"[CNM] ✅ GRÁTIS (cloudscraper)")
        return r
    print(f"[CNM] cloudscraper falhou → tentando ScraperAPI...")
    r = _get_scraperapi(url)
    if r:
        _stats["scraperapi"] += 1
        print(f"[CNM] ⚠️  PAGO (ScraperAPI)")
        return r
    _stats["falhou"] += 1
    return None


# ── Paginação ─────────────────────────────────────────────────────────────────

def _total_paginas(soup):
    """Detecta número total de páginas via links ?pagina=N ou contagem de imóveis."""
    try:
        pags = soup.find_all("a", href=re.compile(r'pagina=\d+'))
        if pags:
            nums = [int(re.search(r'pagina=(\d+)', p["href"]).group(1))
                    for p in pags if re.search(r'pagina=(\d+)', p.get("href", ""))]
            if nums:
                return max(nums)

        total_tag = soup.find(string=re.compile(r'\d+\s+im[oó]ve[li]s?', re.I))
        if total_tag:
            m = re.search(r'(\d+)', total_tag)
            if m:
                return max(1, (int(m.group(1)) + 19) // 20)
    except Exception:
        pass
    return 5  # fallback conservador


# ── Extração principal via ld+json ────────────────────────────────────────────

def _extrair_area_url(url: str) -> int | None:
    """Tenta extrair área em m² diretamente da URL do anúncio.
    Ex: ...criciuma-sao-simao-3162m2-RS590000/...  →  3162
    """
    m = re.search(r'-(\d+(?:[.,]\d+)?)m2-', url, re.I)
    if m:
        return int(re.sub(r'[.,]', '', m.group(1)))
    return None


def _extrair_area_floorsize(item_offered: dict) -> int | None:
    """Extrai área do campo floorSize.unitText  ex: '3.162m²' ou '200m²'."""
    fs = item_offered.get("floorSize", {})
    texto = fs.get("unitText", "")
    if texto:
        m = re.search(r'([\d.,]+)', texto)
        if m:
            return int(re.sub(r'[.,]', '', m.group(1)))
    return None


def _extrair_id(url: str) -> str | None:
    m = re.search(r'/id-(\d+)/', url)
    return m.group(1) if m else None


def parsear_offer(offer: dict) -> dict | None:
    """Parseia um objeto @type:Offer do ld+json do Chaves na Mão."""
    try:
        url      = offer.get("url", "")
        titulo   = offer.get("name", "").strip()
        preco_s  = offer.get("price", "0")

        if not url or not titulo:
            return None

        anuncio_id = _extrair_id(url)
        if not anuncio_id:
            return None

        # Preço
        try:
            preco = int(float(str(preco_s))) if preco_s else None
            if preco == 0:
                preco = None
        except (ValueError, TypeError):
            preco = None

        # Item ofertado (dados do imóvel)
        item = offer.get("itemOffered", {})

        # Área: tenta floorSize → URL → descrição
        area = _extrair_area_floorsize(item)
        if not area:
            area = _extrair_area_url(url)
        if not area:
            desc = item.get("description", "")
            m = re.search(r'([\d.,]+)\s*m[²2]', desc, re.I)
            if m:
                area = int(re.sub(r'[.,]', '', m.group(1)))

        # Endereço
        addr   = item.get("address", {})
        bairro = addr.get("addressLocality", "").strip()
        regiao = addr.get("addressRegion", "")   # ex: "Criciúma, SC"
        cidade = regiao.split(",")[0].strip() if regiao else ""
        estado = regiao.split(",")[-1].strip() if "," in regiao else "SC"
        rua    = addr.get("streetAddress", "").strip()
        if rua in ("não disponível", ""):
            rua = ""

        # Coordenadas
        geo  = item.get("geo", {})
        lat  = float(geo.get("latitude",  0) or 0)
        lon  = float(geo.get("longitude", 0) or 0)

        # Foto
        foto = item.get("image", "")

        # Descrição curta
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
            "fonte":       "ChavesNaMão",
            "foto":        foto,
            "descricao":   descricao,
            "data_coleta": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"[CNM] Erro ao parsear offer: {e}")
        return None


def extrair_offers_ldjson(soup: BeautifulSoup) -> list[dict]:
    """
    Varre todos os <script type="application/ld+json"> da página
    e coleta objetos @type:Offer (diretos ou dentro de ItemList/Product).
    """
    offers = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        # Pode ser lista no topo
        items = data if isinstance(data, list) else [data]

        for obj in items:
            tipo = obj.get("@type", "")

            # Offer direto
            if tipo == "Offer":
                a = parsear_offer(obj)
                if a:
                    offers.append(a)

            # ItemList ou AggregateOffer com lista de offers
            elif tipo in ("ItemList", "Product", "RealEstateListing"):
                raw_offers = obj.get("offers", [])
                raw_items  = obj.get("itemListElement", [])
                # Garante que ambos são listas
                if isinstance(raw_offers, dict): raw_offers = [raw_offers]
                if isinstance(raw_items,  dict): raw_items  = [raw_items]
                for sub in (raw_offers + raw_items):
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

            # Bloco com "offers" no topo (ex: Product com offers:[...])
            elif "offers" in obj:
                raw = obj["offers"]
                lista = raw if isinstance(raw, list) else [raw]
                for sub in lista:
                    if isinstance(sub, dict) and sub.get("@type") == "Offer":
                        a = parsear_offer(sub)
                        if a:
                            offers.append(a)

    return offers


# ── Scraper principal ─────────────────────────────────────────────────────────

def scrape_chavesnamao():
    anuncios = []
    _stats["cloudscraper"] = 0
    _stats["scraperapi"]   = 0
    _stats["falhou"]       = 0

    for base_url in CNM_URLS:
        total_pags = None
        nome_url = base_url.rstrip("/").split("/")[-1] or "sc"
        print(f"\n[CNM] ── {nome_url} ──")

        for pagina in range(1, 11):  # máx 10 páginas por cidade
            url = f"{base_url}?pagina={pagina}" if pagina > 1 else base_url
            print(f"[CNM] Página {pagina}...")

            try:
                r = _get(url)
                if not r:
                    print(f"[CNM] Sem resposta — próxima cidade")
                    break

                soup = BeautifulSoup(r.text, "lxml")

                # Detecta total de páginas na 1ª requisição
                if pagina == 1:
                    total_pags = _total_paginas(soup)
                    print(f"[CNM] Total de páginas estimado: {total_pags}")

                    # DEBUG: salva HTML apenas para primeira cidade de cada tipo
                    if "criciuma" in base_url:
                        os.makedirs("docs", exist_ok=True)
                        with open("docs/debug_cnm.html", "w", encoding="utf-8") as f:
                            f.write(r.text)
                        print("[CNM] DEBUG: HTML salvo em docs/debug_cnm.html")

                novos_offers = extrair_offers_ldjson(soup)

                if not novos_offers:
                    print(f"[CNM] Sem offers no ld+json — fim desta cidade")
                    break

                print(f"[CNM] {len(novos_offers)} offers encontrados")
                antes = len(anuncios)
                anuncios.extend(novos_offers)
                print(f"[CNM] {len(anuncios) - antes} anúncios adicionados")

                if pagina >= total_pags:
                    break

                time.sleep(2.0 + (pagina % 3) * 0.5)

            except Exception as e:
                print(f"[CNM] Erro: {e}")
                break

    # Deduplica por ID
    vistos = set()
    unicos = [a for a in anuncios if a["id"] not in vistos and not vistos.add(a["id"])]

    print(f"\n[CNM] ── Resumo ──")
    print(f"[CNM] ✅ Grátis (cloudscraper): {_stats['cloudscraper']} páginas")
    print(f"[CNM] ⚠️  Pago  (ScraperAPI):   {_stats['scraperapi']} páginas")
    print(f"[CNM] ❌ Falhou:                {_stats['falhou']} páginas")
    print(f"[CNM] Total: {len(unicos)} anúncios únicos")
    return unicos
