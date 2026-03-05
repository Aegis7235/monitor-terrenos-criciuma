import json, re, time, requests, os
from datetime import datetime

SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")

URLS = [
    ("https://www.zapimoveis.com.br/venda/terrenos-lotes-condominios/sc+criciuma/",         "ZAP"),
    ("https://www.zapimoveis.com.br/venda/terrenos-lotes-condominios/sc+icara/",            "ZAP"),
    ("https://www.zapimoveis.com.br/venda/terrenos-lotes-condominios/sc+forquilhinha/",     "ZAP"),
    ("https://www.zapimoveis.com.br/venda/terrenos-lotes-condominios/sc+nova-veneza/",      "ZAP"),
    ("https://www.zapimoveis.com.br/venda/terrenos-lotes-condominios/sc+cocal-do-sul/",     "ZAP"),
    ("https://www.zapimoveis.com.br/venda/terrenos-lotes-condominios/sc+morro-da-fumaca/",  "ZAP"),
    ("https://www.vivareal.com.br/venda/santa-catarina/criciuma/lote-terreno_residencial/",        "VivaReal"),
    ("https://www.vivareal.com.br/venda/santa-catarina/icara/lote-terreno_residencial/",           "VivaReal"),
    ("https://www.vivareal.com.br/venda/santa-catarina/forquilhinha/lote-terreno_residencial/",    "VivaReal"),
    ("https://www.vivareal.com.br/venda/santa-catarina/nova-veneza/lote-terreno_residencial/",     "VivaReal"),
    ("https://www.vivareal.com.br/venda/santa-catarina/cocal-do-sul/lote-terreno_residencial/",    "VivaReal"),
    ("https://www.vivareal.com.br/venda/santa-catarina/morro-da-fumaca/lote-terreno_residencial/", "VivaReal"),
]

CIDADES_REGIAO = {
    "criciúma","criciuma","içara","icara","forquilhinha",
    "nova veneza","cocal do sul","morro da fumaça","morro da fumaca",
    "siderópolis","sideropolis","maracajá","maracaja",
    "sangão","sangao","balneário rincão","balneario rincao",
}


def _get(url):
    payload = {
        "api_key":      SCRAPERAPI_KEY,
        "url":          url,
        "country_code": "br",
        "render":       "false",
    }
    return requests.get("https://api.scraperapi.com/", params=payload, timeout=60)


def _cidade_ok(cidade):
    if not cidade:
        return True
    return any(c in cidade.lower() for c in CIDADES_REGIAO)


def _total_paginas(html, por_pagina=30):
    m = re.search(r'"numberOfItems"\s*:\s*(\d+)', html)
    if m:
        total = int(m.group(1))
        return max(1, (total + por_pagina - 1) // por_pagina)
    return 5


def parsear_jsonld(html, fonte):
    anuncios = []

    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ):
        try:
            data = json.loads(m.group(1))
        except Exception:
            continue

        if data.get("@type") != "ItemList":
            continue

        for item in data.get("itemListElement", []):
            listing = item.get("item", {})
            try:
                lid    = str(listing.get("@id", ""))
                titulo = listing.get("name", "")
                url    = listing.get("url", "")

                addr   = listing.get("address", {})
                cidade = addr.get("addressLocality", "")
                bairro = addr.get("neighborhood", "")

                if not _cidade_ok(cidade):
                    continue

                area_obj = listing.get("floorSize", {})
                area     = int(area_obj.get("value", 0)) or None

                preco = None
                offers = listing.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                preco_raw = offers.get("price")
                if preco_raw:
                    preco = int(re.sub(r"\D", "", str(preco_raw))) or None

                # Foto — primeiro item de "image"
                foto = None
                imagens = listing.get("image", [])
                if isinstance(imagens, list) and imagens:
                    foto = imagens[0]
                elif isinstance(imagens, str):
                    foto = imagens

                if not lid:
                    continue

                anuncios.append({
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
                    "descricao":   "",
                    "data_coleta": datetime.now().isoformat(),
                })
            except Exception as e:
                print(f"[{fonte}] Erro ao parsear item: {e}")

    return anuncios


def scrape_vivareal_zap():
    anuncios = []

    for base_url, nome in URLS:
        print(f"[{nome}] Coletando: {base_url}")
        total_pags = None

        for pagina in range(1, 6):
            url = f"{base_url}?pagina={pagina}" if pagina > 1 else base_url
            try:
                r = _get(url)
                if r.status_code != 200:
                    print(f"[{nome}] HTTP {r.status_code} — pulando")
                    break

                if total_pags is None:
                    total_pags = _total_paginas(r.text)
                    print(f"[{nome}] Total estimado de páginas: {total_pags}")

                novos = parsear_jsonld(r.text, nome)
                if not novos:
                    print(f"[{nome}] Sem itens na página {pagina} — fim")
                    break

                print(f"[{nome}] Página {pagina}: {len(novos)} anúncios")
                anuncios.extend(novos)

                if pagina >= total_pags:
                    break

                time.sleep(2)

            except Exception as e:
                print(f"[{nome}] Erro: {e}")
                break

    vistos = set()
    unicos = [a for a in anuncios if a["id"] not in vistos and not vistos.add(a["id"])]
    print(f"[ZAP/VR] Total: {len(unicos)} anúncios únicos")
    return unicos
