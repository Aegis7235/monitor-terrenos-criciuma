"""
Geocodificação gratuita com Nominatim (OpenStreetMap).
Sem filtro de raio — geocodifica qualquer cidade do sul catarinense.
Aproveita coordenadas diretas quando já vierem do ZAP/VivaReal.
"""
import time, requests
from geopy.distance import geodesic

NOMINATIM = "https://nominatim.openstreetmap.org/search"
UA        = "monitor-terrenos-criciuma/1.0"

# Cache em memória para evitar chamadas repetidas na mesma execução
_cache = {}


def geocodificar(cidade, bairro="", estado="SC"):
    chave = f"{bairro}|{cidade}|{estado}".lower()
    if chave in _cache:
        return _cache[chave]

    queries = []
    if bairro:
        queries.append(f"{bairro}, {cidade}, {estado}, Brasil")
    queries.append(f"{cidade}, {estado}, Brasil")

    for q in queries:
        try:
            r = requests.get(
                NOMINATIM,
                params={"q": q, "format": "json", "limit": 1, "countrycodes": "br"},
                headers={"User-Agent": UA},
                timeout=10,
            )
            results = r.json()
            if results:
                lat = float(results[0]["lat"])
                lon = float(results[0]["lon"])
                _cache[chave] = (lat, lon)
                return lat, lon
            time.sleep(1.1)
        except Exception as e:
            print(f"[Geo] Erro: {e}")
            time.sleep(1)

    _cache[chave] = (None, None)
    return None, None


def geocodificar_anuncios(lista, salvar_fn):
    print(f"[Geo] Geocodificando {len(lista)} anúncios...")
    ok = 0
    pulados = 0

    for a in lista:
        # Aproveita coordenadas diretas do ZAP/VivaReal — evita chamada ao Nominatim
        if a.get("lat") and a.get("lon"):
            salvar_fn(a["id"], a["lat"], a["lon"])
            ok += 1
            pulados += 1
            continue

        lat, lon = geocodificar(a.get("cidade", ""), a.get("bairro", ""))
        if lat:
            salvar_fn(a["id"], lat, lon)
            a["lat"], a["lon"] = lat, lon
            ok += 1
        time.sleep(1.1)

    print(f"[Geo] {ok}/{len(lista)} geocodificados ({pulados} vieram com coords diretas do ZAP)")
