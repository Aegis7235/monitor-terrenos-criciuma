"""
Chaves na Mão Scraper — Sul Catarinense
cloudscraper com fallback ScraperAPI. Mesma estrutura do OLX scraper.
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

BASE_TERRENOS = "https://www.chavesnamao.com.br/terrenos-a-venda"
BASE_CHACARAS = "https://www.chavesnamao.com.br/chacaras-a-venda"

# Cidades do sul catarinense — padrão: /sc-{cidade}/
# Coleta terrenos + chácaras (ambas categorias relevantes para o projeto)
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


def _total_paginas(soup):
    """Detecta número total de páginas na listagem do Chaves na Mão."""
    try:
        # Chaves na Mão usa paginação com links ?pagina=N
        pags = soup.find_all("a", href=re.compile(r'pagina=\d+'))
        if pags:
            nums = []
            for p in pags:
                m = re.search(r'pagina=(\d+)', p.get("href", ""))
                if m:
                    nums.append(int(m.group(1)))
            if nums:
                return max(nums)

        # Fallback: busca span/div com total de imóveis
        total_tag = soup.find(string=re.compile(r'\d+\s+im[oó]ve[li]s?', re.I))
        if total_tag:
            m = re.search(r'(\d+)', total_tag)
            if m:
                total = int(m.group(1))
                return max(1, (total + 19) // 20)  # ~20 por página
    except Exception:
        pass
    return 5  # fallback conservador


def _extrair_id(url):
    """Extrai ID único do anúncio pela URL."""
    # Padrão: /imovel/12345678/ ou /terreno-a-venda/slug-12345678/
    m = re.search(r'/(\d{6,})(?:/|$)', url)
    return m.group(1) if m else None


def parsear_card(card):
    """
    Parseia um card de anúncio do Chaves na Mão.
    O site usa classes como 'property-card', 'listing-card', ou similar.
    Tenta múltiplas estratégias para máxima robustez.
    """
    try:
        # ── URL e ID ──
        link = card.find("a", href=re.compile(r'/imovel/|/terreno'))
        if not link:
            link = card.find("a", href=True)
        if not link:
            return None

        url = link.get("href", "")
        if not url.startswith("http"):
            url = "https://www.chavesnamao.com.br" + url

        anuncio_id = _extrair_id(url)
        if not anuncio_id:
            return None

        # ── Título ──
        titulo = ""
        for sel in [
            card.find("h2"),
            card.find("h3"),
            card.find(class_=re.compile(r'title|titulo|heading', re.I)),
        ]:
            if sel and sel.get_text(strip=True):
                titulo = sel.get_text(strip=True)
                break

        # ── Preço ──
        preco = None
        for sel in [
            card.find(class_=re.compile(r'price|preco|valor', re.I)),
            card.find("span", string=re.compile(r'R\$')),
            card.find(string=re.compile(r'R\$\s*[\d\.]+')),
        ]:
            if sel:
                texto = sel.get_text(strip=True) if hasattr(sel, 'get_text') else str(sel)
                nums = re.sub(r"\D", "", re.sub(r'R\$', '', texto))
                if nums and int(nums) > 1000:
                    preco = int(nums)
                    break

        # ── Área ──
        area = None
        texto_card = card.get_text(" ", strip=True)
        for pattern in [
            r'(\d[\d\.]*)\s*m[²2]',
            r'(\d[\d\.]*)\s*metros?\s*quadrados?',
            r'[Áá]rea[:\s]+(\d[\d\.]*)',
        ]:
            m = re.search(pattern, texto_card, re.I)
            if m:
                area = int(re.sub(r"\.", "", m.group(1)))
                if area > 0:
                    break

        # ── Localização ──
        cidade, bairro = "", ""
        for sel in [
            card.find(class_=re.compile(r'location|localiza|endereco|address', re.I)),
            card.find(class_=re.compile(r'city|cidade', re.I)),
        ]:
            if sel:
                partes = [p.strip() for p in re.split(r'[,\-–]', sel.get_text(strip=True)) if p.strip()]
                cidade  = partes[0] if partes else ""
                bairro  = partes[1] if len(partes) > 1 else ""
                break

        # Se não achou cidade, tenta extrair do título ou URL
        if not cidade:
            m = re.search(r'em\s+([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)*)', titulo)
            if m:
                cidade = m.group(1)

        # ── Foto ──
        foto = None
        for img_tag in [
            card.find("img", src=re.compile(r'https?://')),
            card.find("img", attrs={"data-src": True}),
            card.find("img", attrs={"data-lazy": True}),
        ]:
            if img_tag:
                foto = (
                    img_tag.get("src") or
                    img_tag.get("data-src") or
                    img_tag.get("data-lazy") or
                    ""
                )
                if foto and "placeholder" not in foto and "blank" not in foto:
                    break
                foto = None

        return {
            "id":          f"cnm_{anuncio_id}",
            "titulo":      titulo[:120] or "Terreno à venda",
            "preco":       preco,
            "area_m2":     area,
            "cidade":      cidade,
            "bairro":      bairro,
            "estado":      "SC",
            "url":         url,
            "fonte":       "ChavesNaMão",
            "foto":        foto,
            "descricao":   "",
            "data_coleta": datetime.now().isoformat(),
        }

    except Exception as e:
        print(f"[CNM] Erro ao parsear card: {e}")
        return None


def _encontrar_cards(soup):
    """
    Tenta múltiplas estratégias para encontrar os cards de anúncios.
    O Chaves na Mão pode mudar classes com o tempo.
    """
    estrategias = [
        # Estratégia 1: classes conhecidas
        lambda: soup.find_all(class_=re.compile(r'property-card|listing-card|imovel-card|card-imovel', re.I)),
        # Estratégia 2: artigos com link para imóvel
        lambda: [a.parent for a in soup.find_all("a", href=re.compile(r'/imovel/')) if a.parent],
        # Estratégia 3: divs com preço dentro
        lambda: [d for d in soup.find_all("div", recursive=False) if d.find(string=re.compile(r'R\$'))],
        # Estratégia 4: li dentro de ul de listagem
        lambda: soup.find("ul", class_=re.compile(r'list|listing|results', re.I)) and
                soup.find("ul", class_=re.compile(r'list|listing|results', re.I)).find_all("li") or [],
    ]

    for estrategia in estrategias:
        try:
            cards = estrategia()
            if cards and len(cards) > 0:
                return cards
        except Exception:
            continue

    return []


def scrape_chavesnamao():
    anuncios = []
    _stats["cloudscraper"] = 0
    _stats["scraperapi"] = 0
    _stats["falhou"] = 0

    for base_url in CNM_URLS:
        total_pags = None
        nome_url = base_url.rstrip("/").split("/")[-1] or "sc"
        print(f"\n[CNM] ── {nome_url} ──")

        for pagina in range(1, 11):  # máx 10 páginas por cidade
            # Chaves na Mão usa ?pagina=N para paginação
            url = f"{base_url}?pagina={pagina}" if pagina > 1 else base_url
            print(f"[CNM] Página {pagina}...")

            try:
                r = _get(url)
                if not r:
                    print(f"[CNM] Sem resposta — próxima cidade")
                    break

                soup = BeautifulSoup(r.text, "lxml")

                # DEBUG — remove após corrigir o parser
                if pagina == 1 and "criciuma" in base_url:
                    import os as _os
                    _os.makedirs("docs", exist_ok=True)
                    with open("docs/debug_cnm.html", "w", encoding="utf-8") as _f:
                        _f.write(r.text)
                    print("[CNM] DEBUG: HTML salvo em docs/debug_cnm.html")
                    total_pags = _total_paginas(soup)
                    print(f"[CNM] Total de páginas: {total_pags}")

                cards = _encontrar_cards(soup)
                if not cards:
                    print(f"[CNM] Sem cards — fim desta cidade")
                    break

                print(f"[CNM] {len(cards)} cards encontrados")
                antes = len(anuncios)
                for card in cards:
                    a = parsear_card(card)
                    if a and a.get("titulo") and a.get("url"):
                        anuncios.append(a)

                novos = len(anuncios) - antes
                print(f"[CNM] {novos} anúncios válidos desta página")

                if not novos or pagina >= total_pags:
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
