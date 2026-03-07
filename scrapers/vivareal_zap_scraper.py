"""
ZAP/VivaReal Scraper — sem ScraperAPI
Usa a API interna JSON do Grupo ZAP (mesma que o site usa).
100% gratuito, retorna dados estruturados, sem necessidade de render JS.
Fallback para ScraperAPI + JSON-LD se a API interna mudar.
"""
import json, re, time, requests, os
from datetime import datetime

SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")

# ─── API interna do Grupo ZAP (ZAP Imóveis + VivaReal) ────────────────────────
# Endpoint público usado pelo próprio site — não requer autenticação.
# portal: "ZAP" ou "VIVAREAL"
# categoryPage: "SALE" (venda)
# business: "SALE"
# listingType: "USED" (inclui novos e usados)

ZAP_API = "https://glue-api.zapimoveis.com.br/v2/listings"
VR_API  = "https://glue-api.vivareal.com.br/v2/listings"

HEADERS_API = {
    "User-Agent":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept":      "application/json, text/plain, */*",
    "Origin":      "https://www.zapimoveis.com.br",
    "Referer":     "https://www.zapimoveis.com.br/",
    "x-domain":    "www.zapimoveis.com.br",
}

HEADERS_VR = {**HEADERS_API,
    "Origin":  "https://www.vivareal.com.br",
    "Referer": "https://www.vivareal.com.br/",
    "x-domain": "www.vivareal.com.br",
}

# Cidades da região de Criciúma — adicione mais conforme precisar
CIDADES = [
    {"city": "Criciúma",          "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Içara",             "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Forquilhinha",      "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Nova Veneza",       "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Cocal do Sul",      "state": "Santa Catarina", "stateAcronym": "SC"},
    {"city": "Morro da Fumaça",   "state": "Santa Catarina", "stateAcronym": "SC"},
    # Expanda adicionando mais cidades abaixo:
    # {"city": "Siderópolis",     "state": "Santa Catarina", "stateAcronym": "SC"},
    # {"city": "Maracajá",        "state": "Santa Catarina", "stateAcronym": "SC"},
    # {"city": "Sangão",          "state": "Santa Catarina", "stateAcronym": "SC"},
    # {"city": "Urussanga",       "state": "Santa Catarina", "stateAcronym": "SC"},
    # {"city": "Lauro Muller",    "state": "Santa Catarina", "stateAcronym": "SC"},
]

POR_PAGINA = 36  # máximo aceito pela API


def _params_api(cidade, pagina, portal):
    return {
        "portal":            portal,
        "business":          "SALE",
        "categoryPage":      "SALE",
        "listingType":       "USED",
        "unitTypes[]":       "LandLot",   # terrenos/lotes
        "size":              POR_PAGINA,
        "from":              (pagina - 1) * POR_PAGINA,
        "addressCity":       cidade["city"],
        "addressState":      cidade["state"],
        "addressCountry":    "Brasil",
        "includeFields":     "search(result(listings(listing(displayAddressType,amenities,usableAreas,constructionStatus,listingType,description,title,stamps,createdAt,floors,unitTypes,nonActivationReason,providerId,propertyType,unitSubTypes,unitsOnTheFloor,legacyId,id,portal,unitFloor,parkingSpaces,updatedAt,address,suites,publicationType,externalId,bathrooms,usableAreas,bedrooms,pricingInfos,showPrice,resale,buildings,capacityLimit,status),account(id,name,logoUrl,licenseNumber,showAddress,legacyVivarealId,legacyZapId,minisite),medias,accountLink,link)),totalCount)",
    }


def _buscar_pagina_api(cidade, pagina, portal, api_url, headers):
    params = _params_api(cidade, pagina, portal)
    try:
        r = requests.get(api_url, params=params, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        print(f"[{portal}] HTTP {r.status_code} para {cidade['city']} pág {pagina}")
    except Exception as e:
        print(f"[{portal}] Erro API: {e}")
    return None


def _parsear_listing(item, fonte):
    try:
        listing = item.get("listing", {})
        account = item.get("account", {})
        link    = item.get("link", {})

        lid    = listing.get("id") or listing.get("legacyId", "")
        titulo = listing.get("title", "")

        addr   = listing.get("address", {})
        cidade = addr.get("city", "")
        bairro = addr.get("neighborhood", "")
        estado = addr.get("stateAcronym", "SC")
        # Coordenadas diretas — quando disponíveis evita geocodificação!
        lat = addr.get("point", {}).get("lat")
        lon = addr.get("point", {}).get("lon")

        areas  = listing.get("usableAreas", [])
        area   = int(areas[0]) if areas and areas[0] else None

        preco  = None
        for pi in listing.get("pricingInfos", []):
            if pi.get("businessType") == "SALE":
                raw = pi.get("price", "")
                nums = re.sub(r"\D", "", str(raw))
                preco = int(nums) if nums else None
                break

        url = ""
        if link:
            slug = link.get("href", "")
            base = "https://www.vivareal.com.br" if fonte == "VivaReal" else "https://www.zapimoveis.com.br"
            url  = base + slug if slug.startswith("/") else slug

        foto = None
        medias = item.get("medias", [])
        if medias:
            foto = medias[0].get("url", "")

        if not lid:
            return None

        result = {
            "id":          f"zap_{lid}",
            "titulo":      titulo[:120],
            "preco":       preco,
            "area_m2":     area,
            "cidade":      cidade,
            "bairro":      bairro,
            "estado":      estado,
            "url":         url,
            "fonte":       fonte,
            "foto":        foto,
            "descricao":   listing.get("description", "")[:300],
            "data_coleta": datetime.now().isoformat(),
        }

        # Bônus: salva coordenadas direto se disponíveis (economiza geocodificação)
        if lat and lon:
            result["lat"] = lat
            result["lon"] = lon

        return result
    except Exception as e:
        print(f"[ZAP/VR] Erro ao parsear: {e}")
        return None


def _scrape_portal(cidade, portal, api_url, headers, max_paginas=10):
    anuncios = []
    total_items = None

    for pagina in range(1, max_paginas + 1):
        print(f"[{portal}] {cidade['city']} — pág {pagina}")
        data = _buscar_pagina_api(cidade, pagina, portal, api_url, headers)
        if not data:
            break

        result = data.get("search", {}).get("result", {})
        listings = result.get("listings", [])

        if total_items is None:
            total_items = result.get("totalCount", 0)
            total_pags  = max(1, (total_items + POR_PAGINA - 1) // POR_PAGINA)
            print(f"[{portal}] {cidade['city']}: {total_items} anúncios ({total_pags} páginas)")
            max_paginas = min(total_pags, max_paginas)

        if not listings:
            print(f"[{portal}] Sem listagens — fim")
            break

        for item in listings:
            a = _parsear_listing(item, portal)
            if a:
                anuncios.append(a)

        print(f"[{portal}] Pág {pagina}: {len(listings)} anúncios coletados")

        if pagina >= max_paginas:
            break

        time.sleep(1.5)

    return anuncios


def scrape_vivareal_zap():
    anuncios = []

    for cidade in CIDADES:
        # ZAP Imóveis
        zap = _scrape_portal(cidade, "ZAP", ZAP_API, HEADERS_API)
        anuncios.extend(zap)
        time.sleep(2)

        # VivaReal
        vr = _scrape_portal(cidade, "VivaReal", VR_API, HEADERS_VR)
        anuncios.extend(vr)
        time.sleep(2)

    vistos = set()
    unicos = [a for a in anuncios if a["id"] not in vistos and not vistos.add(a["id"])]
    print(f"[ZAP/VR] Total: {len(unicos)} anúncios únicos")
    return unicos


# ─── Fallback: JSON-LD via ScraperAPI (método antigo) ─────────────────────────
# Usado automaticamente se a API interna retornar erro persistente.

def _scrape_jsonld_fallback(base_url, nome):
    """Método original com ScraperAPI — mantido como fallback."""
    if not SCRAPERAPI_KEY:
        return []
    print(f"[{nome}] ⚠️  Usando fallback ScraperAPI para {base_url}")
    anuncios = []

    def _get_paid(url):
        payload = {"api_key": SCRAPERAPI_KEY, "url": url, "country_code": "br", "render": "false"}
        return requests.get("https://api.scraperapi.com/", params=payload, timeout=60)

    for pagina in range(1, 6):
        url = f"{base_url}?pagina={pagina}" if pagina > 1 else base_url
        try:
            r = _get_paid(url)
            if r.status_code != 200:
                break
            for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', r.text, re.S):
                try:
                    data = json.loads(m.group(1))
                    if data.get("@type") != "ItemList":
                        continue
                    for item in data.get("itemListElement", []):
                        listing = item.get("item", {})
                        lid = str(listing.get("@id", ""))
                        if not lid:
                            continue
                        addr   = listing.get("address", {})
                        area   = int((listing.get("floorSize") or {}).get("value", 0)) or None
                        preco_raw = (listing.get("offers") or {}).get("price")
                        preco  = int(re.sub(r"\D", "", str(preco_raw))) if preco_raw else None
                        anuncios.append({
                            "id": f"zap_{lid}", "titulo": listing.get("name","")[:120],
                            "preco": preco, "area_m2": area,
                            "cidade": addr.get("addressLocality",""),
                            "bairro": addr.get("neighborhood",""), "estado": "SC",
                            "url": listing.get("url",""), "fonte": nome,
                            "foto": (listing.get("image") or [None])[0],
                            "descricao": "", "data_coleta": datetime.now().isoformat(),
                        })
                except Exception:
                    pass
            time.sleep(2)
        except Exception as e:
            print(f"[{nome}] Fallback erro: {e}")
            break

    return anuncios
