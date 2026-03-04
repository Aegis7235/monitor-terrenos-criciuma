"""
Geocodificação gratuita com Nominatim (OpenStreetMap).
Filtra anúncios fora do raio de 30km de Criciúma.
"""
import time, requests
from geopy.distance import geodesic

CRICIUMA   = (-28.6808, -49.3697)
RAIO_KM    = 30
NOMINATIM  = "https://nominatim.openstreetmap.org/search"
UA         = "monitor-terrenos-criciuma/1.0"

# Cache em memória para evitar chamadas repetidas
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
                dist = geodesic(CRICIUMA, (lat, lon)).km
                if dist <= RAIO_KM:
                    _cache[chave] = (lat, lon)
                    return lat, lon
                else:
                    print(f"[Geo] Fora do raio: {q} ({dist:.1f}km)")
                    _cache[chave] = (None, None)
                    return None, None
            time.sleep(1.1)
        except Exception as e:
            print(f"[Geo] Erro: {e}")
            time.sleep(1)

    _cache[chave] = (None, None)
    return None, None


def geocodificar_anuncios(lista, salvar_fn):
    print(f"[Geo] Geocodificando {len(lista)} anúncios...")
    ok = 0
    for a in lista:
        lat, lon = geocodificar(a.get("cidade",""), a.get("bairro",""))
        if lat:
            salvar_fn(a["id"], lat, lon)
            a["lat"], a["lon"] = lat, lon
            ok += 1
        time.sleep(1.1)
    print(f"[Geo] {ok}/{len(lista)} geocodificados")