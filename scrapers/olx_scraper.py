"""
Scraper OLX — extrai dados via __NEXT_DATA__ (Next.js JSON embutido no HTML).
"""
import json, time, re, requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# URLs de busca para Criciúma e cidades próximas no SC
OLX_URLS = [
    "https://sc.olx.com.br/regiao-de-criciuma/imoveis/terrenos",
    "https://sc.olx.com.br/criciuma/imoveis/terrenos",
]


def extrair_next_data(html):
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("script", {"id": "__NEXT_DATA__"})
    if tag:
        try:
            return json.loads(tag.string)
        except Exception:
            pass
    return None


def parsear_anuncio(item):
    try:
        preco_raw = item.get("price") or item.get("priceValue") or ""
        preco = int(re.sub(r"\D", "", str(preco_raw))) if preco_raw else None

        loc = item.get("location") or {}
        cidade = (loc.get("municipality") or loc.get("city") or {}).get("label", "")
        bairro = (loc.get("neighbourhood") or loc.get("neighborhood") or {}).get("label", "")

        titulo = item.get("subject") or item.get("title") or ""
        desc   = item.get("body") or item.get("description") or ""
        m = re.search(r"(\d[\d\.]*)\s*m[²2]", titulo + " " + desc, re.I)
        area = int(re.sub(r"\.", "", m.group(1))) if m else None

        anuncio_id = str(item.get("listId") or item.get("pk") or item.get("id") or "")
        url = item.get("url") or ""
        if anuncio_id and not url:
            url = f"https://www.olx.com.br/anuncio/{anuncio_id}"

        return {
            "id": f"olx_{anuncio_id}",
            "titulo": titulo[:120],
            "preco": preco,
            "area_m2": area,
            "cidade": cidade,
            "bairro": bairro,
            "estado": "SC",
            "url": url,
            "fonte": "OLX",
            "descricao": desc[:400],
            "data_coleta": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"[OLX] Erro ao parsear anúncio: {e}")
        return None


def scrape_olx():
    anuncios = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for base_url in OLX_URLS:
        for pagina in range(1, 11):
            url = f"{base_url}?o={pagina}" if pagina > 1 else base_url
            print(f"[OLX] Página {pagina}: {url}")
            try:
                r = session.get(url, timeout=15)
                if r.status_code != 200:
                    print(f"[OLX] HTTP {r.status_code} — encerrando este URL")
                    break

                data = extrair_next_data(r.text)
                if not data:
                    print("[OLX] __NEXT_DATA__ não encontrado")
                    break

                pp = data.get("props", {}).get("pageProps", {})
                listings = (
                    pp.get("listings")
                    or pp.get("ads")
                    or pp.get("searchData", {}).get("listings")
                    or []
                )
                if not listings:
                    print(f"[OLX] Sem listagens na página {pagina} — fim")
                    break

                for item in listings:
                    raw = item.get("listing") or item.get("ad") or item
                    a = parsear_anuncio(raw)
                    if a and a["id"] != "olx_":
                        anuncios.append(a)

                total_pags = (
                    pp.get("pageInfo", {}).get("totalPages")
                    or pp.get("totalPages")
                    or 1
                )
                if pagina >= int(total_pags):
                    break
                time.sleep(2)

            except Exception as e:
                print(f"[OLX] Erro: {e}")
                break

    # Remove duplicatas por ID
    vistos = set()
    unicos = []
    for a in anuncios:
        if a["id"] not in vistos:
            vistos.add(a["id"])
            unicos.append(a)

    print(f"[OLX] Total: {len(unicos)} anúncios únicos")
    return unicos