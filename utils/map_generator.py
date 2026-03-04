"""
Gera mapa HTML interativo com Leaflet + filtros dinâmicos.
- Filtro de área mínima (slider)
- Filtro de apenas novos anúncios (toggle)
- Painel fixo no canto inferior esquerdo
"""
import os, json
from datetime import datetime

CRICIUMA = (-28.6808, -49.3697)

def _cor_hex(preco):
    if preco is None:   return "#95a5a6"  # cinza
    if preco < 100_000: return "#27ae60"  # verde
    if preco < 300_000: return "#2980b9"  # azul
    if preco < 600_000: return "#e67e22"  # laranja
    return "#e74c3c"                      # vermelho

def _fmt(preco):
    if preco is None: return "Preço não informado"
    return "R$ {:,.0f}".format(preco).replace(",", ".")

def _historico_html(hist_json):
    if not hist_json:
        return ""
    try:
        hist = json.loads(hist_json) if isinstance(hist_json, str) else hist_json
        if len(hist) <= 1:
            return ""
        linhas = "".join(
            f"<tr><td>{h['data'][:10]}</td><td>{_fmt(h['preco'])}</td></tr>"
            for h in sorted(hist, key=lambda x: x["data"])
        )
        return f"""
        <details>
          <summary style="cursor:pointer;color:#3498db;font-size:12px">📈 Histórico de preço</summary>
          <table style="font-size:11px;width:100%;margin-top:4px">
            <tr><th>Data</th><th>Preço</th></tr>{linhas}
          </table>
        </details>"""
    except Exception:
        return ""


def gerar_mapa(anuncios, novos_ids=None, output="docs/mapa.html"):
    os.makedirs(os.path.dirname(output), exist_ok=True)
    novos_ids = set(novos_ids or [])

    # Serializa anúncios para JS — apenas os que têm coordenadas
    dados_js = []
    area_max = 0
    for a in anuncios:
        if not a.get("lat") or not a.get("lon"):
            continue
        area = a.get("area_m2") or 0
        if area > area_max:
            area_max = area
        eh_novo = a["id"] in novos_ids
        hist_html = _historico_html(a.get("historico"))
        badge = '<span style="background:#e74c3c;color:#fff;padding:2px 7px;border-radius:3px;font-size:11px;font-weight:bold">🆕 NOVO</span><br><br>' if eh_novo else ""
        bairro_cidade = (a.get("bairro") or "") + (" — " if a.get("bairro") else "") + (a.get("cidade") or "")
        popup = f"""<div style="font-family:Arial,sans-serif;min-width:230px;max-width:280px">
          {badge}
          <b style="font-size:14px">{(a.get('titulo') or 'Terreno à venda')[:70]}</b>
          <hr style="margin:6px 0">
          💰 <b>{_fmt(a.get('preco'))}</b><br>
          📐 {a.get('area_m2') or '?'} m²<br>
          📍 {bairro_cidade}<br>
          🏢 <small style="color:#666">{a.get('fonte','')}</small><br>
          📅 <small>Detectado: {(a.get('primeira_vez') or '')[:10]}</small><br>
          {hist_html}
          <a href="{a.get('url','#')}" target="_blank"
             style="display:block;margin-top:8px;padding:6px;background:#2980b9;color:#fff;
                    text-align:center;border-radius:5px;text-decoration:none;font-size:13px">
            Ver anúncio ↗
          </a>
        </div>"""

        dados_js.append({
            "lat":    a["lat"],
            "lon":    a["lon"],
            "area":   area,
            "preco":  a.get("preco"),
            "novo":   eh_novo,
            "cor":    "#c0392b" if eh_novo else _cor_hex(a.get("preco")),
            "icone":  "★" if eh_novo else "⌂",
            "tooltip": f"{'🆕 ' if eh_novo else ''}{_fmt(a.get('preco'))} | {a.get('cidade','')}",
            "popup":  popup,
        })

    area_max = min(area_max or 1000, 5000)  # cap razoável para o slider
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    dados_json = json.dumps(dados_js, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Monitor de Terrenos — Criciúma/SC</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css"/>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.1.0/MarkerCluster.css"/>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.1.0/MarkerCluster.Default.css"/>
  <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.1.0/leaflet.markercluster.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body, #map {{ width: 100%; height: 100%; }}

    /* Painel de filtros — canto inferior esquerdo */
    #painel {{
      position: fixed;
      bottom: 30px;
      left: 10px;
      z-index: 9999;
      background: white;
      padding: 14px 16px;
      border-radius: 12px;
      box-shadow: 0 2px 14px rgba(0,0,0,.22);
      font-family: Arial, sans-serif;
      font-size: 13px;
      min-width: 220px;
      max-width: 260px;
    }}
    #painel h4 {{
      font-size: 14px;
      margin-bottom: 10px;
      color: #2c3e50;
    }}
    .filtro-bloco {{
      margin-bottom: 12px;
    }}
    .filtro-bloco label {{
      display: block;
      font-weight: bold;
      margin-bottom: 4px;
      color: #34495e;
    }}
    #area-slider {{
      width: 100%;
      accent-color: #2980b9;
    }}
    #area-valor {{
      display: inline-block;
      margin-top: 3px;
      color: #2980b9;
      font-weight: bold;
    }}
    .toggle-row {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    /* Toggle switch */
    .switch {{
      position: relative;
      display: inline-block;
      width: 38px;
      height: 22px;
      flex-shrink: 0;
    }}
    .switch input {{ opacity: 0; width: 0; height: 0; }}
    .slider-sw {{
      position: absolute;
      cursor: pointer;
      top: 0; left: 0; right: 0; bottom: 0;
      background: #ccc;
      border-radius: 22px;
      transition: .3s;
    }}
    .slider-sw:before {{
      position: absolute;
      content: "";
      height: 16px; width: 16px;
      left: 3px; bottom: 3px;
      background: white;
      border-radius: 50%;
      transition: .3s;
    }}
    input:checked + .slider-sw {{ background: #e74c3c; }}
    input:checked + .slider-sw:before {{ transform: translateX(16px); }}

    /* Legenda */
    #legenda {{
      margin-top: 10px;
      padding-top: 10px;
      border-top: 1px solid #eee;
      font-size: 12px;
      color: #555;
    }}
    #legenda b {{ color: #2c3e50; }}
    .leg-item {{ margin: 2px 0; }}

    #contador {{
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid #eee;
      font-size: 12px;
      color: #666;
      text-align: center;
    }}
    #contador b {{ color: #2980b9; }}
  </style>
</head>
<body>
  <div id="map"></div>

  <!-- Painel de filtros -->
  <div id="painel">
    <h4>🔍 Filtros</h4>

    <div class="filtro-bloco">
      <label>📐 Área mínima</label>
      <input type="range" id="area-slider" min="0" max="{area_max}" step="50" value="0">
      <div>A partir de <span id="area-valor">0</span> m²</div>
    </div>

    <div class="filtro-bloco">
      <div class="toggle-row">
        <label class="switch">
          <input type="checkbox" id="toggle-novos">
          <span class="slider-sw"></span>
        </label>
        <span>Apenas novos anúncios</span>
      </div>
    </div>

    <div id="legenda">
      <b>🏡 Legenda — Preço</b><br>
      <div class="leg-item"><span style="color:#27ae60">●</span> Até R$ 100k</div>
      <div class="leg-item"><span style="color:#2980b9">●</span> R$ 100k – R$ 300k</div>
      <div class="leg-item"><span style="color:#e67e22">●</span> R$ 300k – R$ 600k</div>
      <div class="leg-item"><span style="color:#e74c3c">●</span> Acima de R$ 600k</div>
      <div class="leg-item"><span style="color:#95a5a6">●</span> Preço não informado</div>
      <div class="leg-item"><span style="color:#c0392b">★</span> <b>Novo anúncio</b></div>
    </div>

    <div id="contador">
      Exibindo <b id="n-visiveis">0</b> de <b>{len(dados_js)}</b> anúncios<br>
      <small style="color:#aaa">Atualizado: {agora}</small>
    </div>
  </div>

<script>
const DADOS = {dados_json};

// Mapa
const map = L.map('map').setView([{CRICIUMA[0]}, {CRICIUMA[1]}], 12);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution: '© OpenStreetMap © CARTO',
  maxZoom: 20
}}).addTo(map);

// Raio 30km
L.circle([{CRICIUMA[0]}, {CRICIUMA[1]}], {{
  radius: 30000,
  color: '#2980b9',
  fill: true,
  fillOpacity: 0.06,
  weight: 1.5
}}).bindTooltip('Raio de 30km').addTo(map);

// Marcador central
L.marker([{CRICIUMA[0]}, {CRICIUMA[1]}])
  .bindTooltip('Criciúma (centro)')
  .addTo(map);

// Cluster
let cluster = L.markerClusterGroup({{ chunkedLoading: true }});
map.addLayer(cluster);

// Cria marcadores com ícone colorido
function criarIcone(d) {{
  const bg = d.novo ? '#c0392b' : d.cor;
  return L.divIcon({{
    className: '',
    html: `<div style="
      background:${{bg}};
      color:white;
      border-radius:50%;
      width:28px;height:28px;
      display:flex;align-items:center;justify-content:center;
      font-size:14px;
      box-shadow:0 1px 4px rgba(0,0,0,.4);
      border:2px solid rgba(255,255,255,.8);
    ">${{d.icone}}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
    popupAnchor: [0, -16],
  }});
}}

const marcadores = DADOS.map(d => {{
  const m = L.marker([d.lat, d.lon], {{ icon: criarIcone(d) }});
  m.bindPopup(d.popup, {{ maxWidth: 300 }});
  m.bindTooltip(d.tooltip);
  m._dados = d;
  return m;
}});

// Aplica filtros
function aplicarFiltros() {{
  const areaMin  = parseInt(document.getElementById('area-slider').value) || 0;
  const soNovos  = document.getElementById('toggle-novos').checked;

  cluster.clearLayers();
  let visiveis = 0;

  marcadores.forEach(m => {{
    const d = m._dados;
    const areaOk = areaMin === 0 || (d.area && d.area >= areaMin);
    const novoOk = !soNovos || d.novo;
    if (areaOk && novoOk) {{
      cluster.addLayer(m);
      visiveis++;
    }}
  }});

  document.getElementById('n-visiveis').textContent = visiveis;
}}

// Eventos dos filtros
document.getElementById('area-slider').addEventListener('input', function() {{
  document.getElementById('area-valor').textContent = this.value;
  aplicarFiltros();
}});
document.getElementById('toggle-novos').addEventListener('change', aplicarFiltros);

// Inicializa
aplicarFiltros();
</script>
</body>
</html>"""

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[Mapa] Salvo em {output} ({len(dados_js)} marcadores)")
