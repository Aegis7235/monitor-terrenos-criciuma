"""
ZAP/VivaReal Scraper — API interna JSON + fallback ScraperAPI
Corrigido para funcionar no GitHub Actions com headers completos.
"""
import json, re, time, requests, os
from datetime import datetime

SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")

# APIs internas do Grupo ZAP
ZAP_API = "https://glue-api.zapimoveis.com.br/v2/listings"
VR_API  = "https://glue-api.vivareal.com.br/v2/listings"

# Headers completos simulando o browser real — essencial para não tomar 403
HEADERS_ZAP = {
    "User-Agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":           "application/json, text/plain, */*",
    "Accept-Language":  "pt-BR,pt;q=0.9",
    "Accept-Encoding":  "gzip, deflate, br",
    "Origin":           "https://www.zapimoveis.com.br",
    "Referer":          "https://www.zapimoveis.com.br/",
    "x-domain":         "www.zapimoveis.com.br",
    "x-ab-test":        "0",
    "sec-fetch-dest":   "empty",
    "sec-fetch-mode":   "cors",
    "sec-fetch-site":   "same-site",
}

HEADERS_VR = {
    **HEADERS_ZAP,
    "Origin":   "https://www.vivareal.com.br",
    "Referer":  "https://www.vivareal.com.br/",
    "x-domain": "www.vivareal.com.br",
}

CIDADES = [
    # ── Região de Criciúma ────────────────────────────────────────────────────
    {"city": "Criciúma",              "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Içara",                 "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Forquilhinha",          "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Nova Veneza",           "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Cocal do Sul",          "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Morro da Fumaça",       "state": "Santa Catarina", "stateAcronym": "SC"},
    # ── Sul catarinense ───────────────────────────────────────────────────────
    {"city": "Siderópolis",           "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Treviso",               "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Urussanga",             "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Orleans",               "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Lauro Müller",          "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Sangão",                "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Maracajá",              "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Tubarão",               "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Jaguaruna",             "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Balneário Rincão",      "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Araranguá",             "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Turvo",                 "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Jacinto Machado",       "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Sombrio",               "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Santa Rosa do Sul",     "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Praia Grande",          "state": "Santa Catarina", "stateAcronym": "SC"},
]

POR_PAGINA = 36

# Contadores para resumo
_stats = {"direto": 0, "scraperapi": 0, "falhou": 0}


def _params(cidade, pagina, portal):
    return {
        "portal":         portal,
        "business":       "SALE",
        "categoryPage":   "SALE",
        "listingType":    "USED",
        "unitTypes[]":    "LandLot",
        "size":           POR_PAGINA,
        "from":           (pagina - 1) * POR_PAGINA,
        "addressCity":    cidade["city"],
        "addressState":   cidade["state"],
        "addressCountry": "Brasil",
        "includeFields":  "search(result(listings(listing(id,legacyId,title,description,address,usableAreas,pricingInfos,propertyType,unitTypes),account(id,name),medias,link),totalCount))",
    }


def _buscar_direto(cidade, pagina, portal, api_url, headers):
    """Requisição direta à API interna do ZAP/VivaReal."""
    try:
        r = requests.get(
            api_url,
            params=_params(cidade, pagina, portal),
            headers=headers,
            timeout=20,
        )
        if r.status_code == 200:
            return r.json(), "direto"
        print(f"[{portal}] HTTP {r.status_code} direto para {cidade['city']}")
    except Exception as e:
        print(f"[{portal}] Erro direto: {e}")
    return None, None


def _buscar_scraperapi(cidade, pagina, portal, api_url, headers):
    """Fallback via ScraperAPI quando requisição direta é bloqueada."""
    if not SCRAPERAPI_KEY:
        return None, None
    try:
        # Monta a URL completa com parâmetros
        req = requests.Request("GET", api_url, params=_params(cidade, pagina, portal))
        url_completa = req.prepare().url

        payload = {
            "api_key":      SCRAPERAPI_KEY,
            "url":          url_completa,
            "country_code": "br",
            "render":       "false",
        }
        r = requests.get("https://api.scraperapi.com/", params=payload,
                         headers={"Accept": "application/json"}, timeout=60)
        if r.status_code == 200:
            return r.json(), "scraperapi"
        print(f"[{portal}] ScraperAPI HTTP {r.status_code}")
    except Exception as e:
        print(f"[{portal}] ScraperAPI erro: {e}")
    return None, None


def _buscar(cidade, pagina, portal, api_url, headers):
    data, metodo = _buscar_direto(cidade, pagina, portal, api_url, headers)
    if data:
        _stats["direto"] += 1
        print(f"[{portal}] ✅ GRÁTIS (direto)")
        return data
    print(f"[{portal}] direto falhou → tentando ScraperAPI...")
    data, metodo = _buscar_scraperapi(cidade, pagina, portal, api_url, headers)
    if data:
        _stats["scraperapi"] += 1
        print(f"[{portal}] ⚠️  PAGO (ScraperAPI)")
        return data
    _stats["falhou"] += 1
    return None


def _parsear(item, fonte):
    try:
        listing = item.get("listing", {})
        link    = item.get("link", {})

        lid    = listing.get("id") or listing.get("legacyId", "")
        titulo = listing.get("title", "")

        addr   = listing.get("address", {})
        cidade = addr.get("city", "")
        bairro = addr.get("neighborhood", "")
        lat    = addr.get("point", {}).get("lat")
        lon    = addr.get("point", {}).get("lon")

        areas  = listing.get("usableAreas", [])
        area   = int(areas[0]) if areas and areas[0] else None

        preco = None
        for pi in listing.get("pricingInfos", []):
            if pi.get("businessType") == "SALE":
                nums = re.sub(r"\D", "", str(pi.get("price", "")))
                preco = int(nums) if nums else None
                break

        slug = (link or {}).get("href", "")
        base = "https://www.vivareal.com.br" if fonte == "VivaReal" else "https://www.zapimoveis.com.br"
        url  = base + slug if slug.startswith("/") else slug

        medias = item.get("medias", [])
        foto   = medias[0].get("url", "") if medias else None

        if not lid:
            return None

        result = {
            "id":          f"zap_{lid}",
            "titulo":      titulo[:120],
            "preco":       preco,
            "area_m2":     area,
            "cidade":      cidade,
            "bairro":      bairro,
            "estado":      "SC",
            "url":         url,
            "fonte":       fonte,
            "foto":        foto,
            "descricao":   listing.get("description", "")[:300],
            "data_coleta": datetime.now().isoformat(),
        }
        # Coordenadas diretas — economiza geocodificação
        if lat and lon:
            result["lat"] = lat
            result["lon"] = lon
        return result
    except Exception as e:
        print(f"[ZAP/VR] Erro parsear: {e}")
        return None


def _scrape_portal(cidade, portal, api_url, headers, max_paginas=10):
    anuncios = []
    total_items = None

    for pagina in range(1, max_paginas + 1):
        print(f"[{portal}] {cidade['city']} — pág {pagina}")
        data = _buscar(cidade, pagina, portal, api_url, headers)
        if not data:
            break

        result   = data.get("search", {}).get("result", {})
        listings = result.get("listings", [])

        if total_items is None:
            total_items = result.get("totalCount", 0)
            total_pags  = max(1, (total_items + POR_PAGINA - 1) // POR_PAGINA)
            print(f"[{portal}] {cidade['city']}: {total_items} anúncios ({total_pags} págs)")
            max_paginas = min(total_pags, max_paginas)

        if not listings:
            break

        for item in listings:
            a = _parsear(item, portal)
            if a:
                anuncios.append(a)

        if pagina >= max_paginas:
            break

        time.sleep(1.5)

    return anuncios


def scrape_vivareal_zap():
    _stats["direto"] = 0
    _stats["scraperapi"] = 0
    _stats["falhou"] = 0

    anuncios = []

    for cidade in CIDADES:
        zap = _scrape_portal(cidade, "ZAP",      ZAP_API, HEADERS_ZAP)
        anuncios.extend(zap)
        time.sleep(1)

        vr  = _scrape_portal(cidade, "VivaReal", VR_API,  HEADERS_VR)
        anuncios.extend(vr)
        time.sleep(1)

    vistos = set()
    unicos = [a for a in anuncios if a["id"] not in vistos and not vistos.add(a["id"])]

    print(f"\n[ZAP/VR] ── Resumo de requisições ──")
    print(f"[ZAP/VR] ✅ Grátis (direto):      {_stats['direto']} requisições")
    print(f"[ZAP/VR] ⚠️  Pago  (ScraperAPI):   {_stats['scraperapi']} requisições")
    print(f"[ZAP/VR] ❌ Falhou:                {_stats['falhou']} requisições")
    print(f"[ZAP/VR] Total: {len(unicos)} anúncios únicos")
    return unicos
