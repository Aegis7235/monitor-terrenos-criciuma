import json, time, re, requests, os
from bs4 import BeautifulSoup
from datetime import datetime

SCRAPERAPI_KEY = os.environ.get("SCRAPERAPI_KEY", "")

OLX_URLS = [
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/criciuma",
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/icara",
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/forquilhinha",
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/nova-veneza",
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/cocal-do-sul",
    "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao/outras-cidades/morro-da-fumaca",
]


def _get(url):
    payload = {
        "api_key": SCRAPERAPI_KEY,
        "url": url,
        "country_code": "br",
        "render": "false",
    }
    r = requests.get("https://api.scraperapi.com/", params=payload, timeout=60)
    return r


def _total_paginas(soup):
    try:
        dl = soup.find("script", {"id": "datalayer"})
        if dl:
            m = re.search(r'"totalOfAds"\s*:\s*(\d+)', dl.string or "")
            if m:
                total = int(m.group(1))
                return max(1, (total + 24) // 25)
    except Exception:
        pass
    return 10


def parsear_card(section):
    try:
        # URL e ID
        link = section.find("a", attrs={"data-testid": "adcard-link"})
        if not link:
            return None
        url = link.get("href", "")
        id_match = re.search(r'-(\d{7,})$', url.rstrip("/"))
        anuncio_id = id_match.group(1) if id_match else ""
        if not anuncio_id:
            return None

        # Título
        titulo = ""
        titulo_tag = section.find("h2", class_=re.compile(r"olx-adcard__title"))
        if titulo_tag:
            titulo = titulo_tag.get_text(strip=True)

        # Preço
        preco = None
        preco_tag = section.find("h3", class_=re.compile(r"olx-adcard__price"))
        if preco_tag:
            nums = re.sub(r"\D", "", preco_tag.get_text(strip=True))
            preco = int(nums) if nums else None

        # Localização
        cidade, bairro = "", ""
        loc_tag = section.find("p", class_=re.compile(r"olx-adcard__location"))
        if loc_tag:
            partes = [p.strip() for p in loc_tag.get_text(strip=True).split(",")]
            cidade = partes[0] if partes else ""
            bairro = partes[1] if len(partes) > 1 else ""

        # Área
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

        # Foto — primeiro <source srcSet="...webp"> dentro de olx-adcard__media
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

                time.sleep(2)

            except Exception as e:
                print(f"[OLX] Erro: {e}")
                break

    vistos = set()
    unicos = [a for a in anuncios if a["id"] not in vistos and not vistos.add(a["id"])]
    print(f"[OLX] Total: {len(unicos)} anúncios únicos")
    return unicos
