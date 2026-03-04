"""
Scraper VivaReal / ZAP Imóveis — usa cloudscraper para bypass Cloudflare.
Ambos os portais pertencem ao Grupo OLX e têm estrutura Next.js similar.
"""
import json, re, time
from datetime import datetime
from bs4 import BeautifulSoup

try:
    import cloudscraper
    _OK = True
except ImportError:
    _OK = False
    print("[ZAP/VR] cloudscraper não instalado — portais desativados")

CIDADES_REGIAO = {
    "criciúma","criciuma","içara","icara","forquilhinha",
    "nova veneza","cocal do sul","morro da fumaça","morro da fumaca",
    "siderópolis","sideropolis","maracajá","maracaja",
    "sangão","sangao","balneário rincão","balneario rincao",
}

URLS = [
    ("https://www.zapimoveis.com.br/venda/terrenos-lotes-condominios/sc+criciuma/", "ZAP"),
    ("https://www.vivareal.com.br/venda/santa-catarina/criciuma/lote-terreno_residencial/", "VivaReal"),
]


def _cidade_ok(cidade):
    if not cidade:
        return True
    return cidade.lower() in CIDADES_REGIAO or any(c in cidade.lower() for c in CIDADES_REGIAO)


def _parsear(listing, fonte):
    try:
        ld = listing.get("listing") or listing
        precos = ld.get("pricingInfos") or []
        preco = None
        for p in precos:
            raw = p.get("price") or p.get("businessPrice") or ""
            if raw:
                preco = int(re.sub(r"\D", "", str(raw)))
                break

        addr   = ld.get("address") or {}
        cidade = addr.get("city") or addr.get("cityName") or ""
        bairro = addr.get("neighborhood") or addr.get("neighborhoodName") or ""

        if not _cidade_ok(cidade):
            return None

        areas = ld.get("usableAreas") or ld.get("totalAreas") or []
        area  = int(areas[0]) if areas else None

        lid   = ld.get("id") or ld.get("listingId") or ""
        titulo = ld.get("title") or f"Terreno em {cidade}"
        desc   = ld.get("description") or ""
        url    = f"https://www.zapimoveis.com.br/imovel/{lid}/" if fonte == "ZAP" \
                 else f"https://www.vivareal.com.br/imovel/{lid}/"

        return {
            "id": f"zap_{lid}",
            "titulo": titulo[:120],
            "preco": preco,
            "area_m2": area,
            "cidade": cidade,
            "bairro": bairro,
            "estado": "SC",
            "url": url,
            "fonte": fonte,
            "descricao": desc[:400],
            "data_coleta": datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"[{fonte}] Erro ao parsear: {e}")
        return None


def scrape_vivareal_zap():
    if not _OK:
        return []

    anuncios = []
    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )

    for base_url, nome in URLS:
        print(f"[{nome}] Iniciando...")
        for pagina in range(1, 6):
            url = f"{base_url}?pagina={pagina}" if pagina > 1 else base_url
            try:
                r = scraper.get(url, timeout=20)
                if r.status_code != 200:
                    print(f"[{nome}] HTTP {r.status_code} — pulando")
                    break

                soup = BeautifulSoup(r.text, "lxml")
                tag  = soup.find("script", {"id": "__NEXT_DATA__"})
                if not tag:
                    print(f"[{nome}] __NEXT_DATA__ ausente — pulando")
                    break

                data = json.loads(tag.string)
                pp   = data.get("props", {}).get("pageProps", {})
                listings = (
                    pp.get("listings")
                    or pp.get("search", {}).get("result", {}).get("listings")
                    or []
                )
                if not listings:
                    break

                for item in listings:
                    a = _parsear(item, nome)
                    if a and a["id"] != "zap_":
                        anuncios.append(a)

                print(f"[{nome}] Página {pagina}: {len(listings)} itens")
                time.sleep(3)

            except Exception as e:
                print(f"[{nome}] Erro: {e}")
                break

    vistos = set()
    unicos = [a for a in anuncios if a["id"] not in vistos and not vistos.add(a["id"])]
    print(f"[ZAP/VR] Total: {len(unicos)} anúncios únicos")
    return unicos