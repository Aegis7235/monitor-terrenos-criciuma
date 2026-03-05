"""
Gera mapa HTML interativo — dark mode, foto no popup,
painel de filtros, sidebar retrátil com listagens.
"""
import os, json, re
from datetime import datetime

CRICIUMA = (-28.6808, -49.3697)

def _cor_hex(preco):
    if preco is None:   return "#64748b"
    if preco < 100_000: return "#22c55e"
    if preco < 300_000: return "#3b82f6"
    if preco < 600_000: return "#f97316"
    return "#ef4444"

def _fmt(preco):
    if preco is None: return "Não informado"
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
        return f"""<details class="hist-details">
          <summary>📈 Histórico de preço</summary>
          <table class="hist-table">
            <tr><th>Data</th><th>Preço</th></tr>{linhas}
          </table>
        </details>"""
    except Exception:
        return ""


def gerar_mapa(anuncios, novos_ids=None, output="docs/mapa.html"):
    os.makedirs(os.path.dirname(output), exist_ok=True)
    novos_ids = set(novos_ids or [])

    dados_js = []
    area_max = 0
    preco_max = 0

    for a in anuncios:
        if not a.get("lat") or not a.get("lon"):
            continue
        area  = a.get("area_m2") or 0
        preco = a.get("preco") or 0
        if area  > area_max:  area_max  = area
        if preco > preco_max: preco_max = preco

        eh_novo  = a["id"] in novos_ids
        hist_html = _historico_html(a.get("historico"))
        bairro_cidade = (a.get("bairro") or "") + (" · " if a.get("bairro") else "") + (a.get("cidade") or "")
        foto = a.get("foto") or ""

        dados_js.append({
            "lat":    a["lat"],
            "lon":    a["lon"],
            "area":   area,
            "preco":  preco,
            "novo":   eh_novo,
            "cor":    "#f43f5e" if eh_novo else _cor_hex(a.get("preco")),
            "titulo": (a.get("titulo") or "Terreno à venda")[:70],
            "preco_fmt": _fmt(a.get("preco")),
            "area_fmt":  f"{area} m²" if area else "? m²",
            "loc":    bairro_cidade,
            "fonte":  a.get("fonte") or "",
            "url":    a.get("url") or "#",
            "foto":   foto,
            "data":   (a.get("primeira_vez") or "")[:10],
            "hist":   hist_html,
        })

    area_max  = min(area_max or 2000, 5000)
    preco_max = min(preco_max or 1_000_000, 5_000_000)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    dados_json = json.dumps(dados_js, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Monitor de Terrenos — Criciúma/SC</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css"/>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.1.0/MarkerCluster.css"/>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.1.0/MarkerCluster.Default.css"/>
  <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.1.0/leaflet.markercluster.js"></script>
  <style>
    :root {{
      --bg:        #0f1117;
      --surface:   #1a1d27;
      --surface2:  #22263a;
      --border:    #2e3248;
      --text:      #e2e8f0;
      --muted:     #64748b;
      --accent:    #6366f1;
      --accent2:   #818cf8;
      --green:     #22c55e;
      --blue:      #3b82f6;
      --orange:    #f97316;
      --red:       #ef4444;
      --new:       #f43f5e;
      --radius:    12px;
      --sidebar-w: 360px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'DM Sans', sans-serif; background: var(--bg); color: var(--text); overflow: hidden; }}
    html, body {{ width: 100%; height: 100%; }}

    /* ── MAP ── */
    #map {{ position: fixed; inset: 0; z-index: 1; }}

    /* dark tiles override */
    .leaflet-tile {{ filter: brightness(0.85) saturate(0.7); }}

    /* cluster */
    .marker-cluster-small,
    .marker-cluster-medium,
    .marker-cluster-large {{ background: rgba(99,102,241,.25) !important; }}
    .marker-cluster-small div,
    .marker-cluster-medium div,
    .marker-cluster-large div {{
      background: rgba(99,102,241,.7) !important;
      color: #fff !important;
      font-family: 'DM Mono', monospace;
      font-size: 11px;
      font-weight: 500;
    }}

    /* ── PAINEL FILTROS (esquerda) ── */
    #painel {{
      position: fixed;
      bottom: 24px;
      left: 16px;
      z-index: 900;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 16px;
      width: 240px;
      box-shadow: 0 8px 32px rgba(0,0,0,.5);
      backdrop-filter: blur(10px);
    }}
    #painel h4 {{
      font-size: 12px;
      font-weight: 600;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: var(--accent2);
      margin-bottom: 14px;
    }}
    .f-block {{ margin-bottom: 14px; }}
    .f-label {{
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .f-label span {{ color: var(--text); font-family: 'DM Mono', monospace; font-size: 11px; }}
    input[type=range] {{
      -webkit-appearance: none;
      width: 100%;
      height: 4px;
      border-radius: 2px;
      background: var(--border);
      outline: none;
    }}
    input[type=range]::-webkit-slider-thumb {{
      -webkit-appearance: none;
      width: 14px; height: 14px;
      border-radius: 50%;
      background: var(--accent);
      cursor: pointer;
      transition: transform .15s;
    }}
    input[type=range]::-webkit-slider-thumb:hover {{ transform: scale(1.3); }}

    /* toggle */
    .toggle-row {{ display: flex; align-items: center; gap: 10px; font-size: 12px; color: var(--muted); }}
    .sw {{ position: relative; width: 36px; height: 20px; flex-shrink: 0; }}
    .sw input {{ opacity: 0; width: 0; height: 0; }}
    .sw-track {{
      position: absolute; inset: 0;
      background: var(--border);
      border-radius: 20px;
      cursor: pointer;
      transition: background .2s;
    }}
    .sw-track:before {{
      content: "";
      position: absolute;
      width: 14px; height: 14px;
      left: 3px; top: 3px;
      background: white;
      border-radius: 50%;
      transition: transform .2s;
    }}
    .sw input:checked + .sw-track {{ background: var(--new); }}
    .sw input:checked + .sw-track:before {{ transform: translateX(16px); }}

    /* legenda */
    .legenda {{ margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border); }}
    .leg-title {{ font-size: 11px; font-weight: 600; color: var(--muted); letter-spacing:.06em; text-transform:uppercase; margin-bottom: 8px; }}
    .leg-item {{ display: flex; align-items: center; gap: 8px; font-size: 11px; color: var(--muted); margin: 4px 0; }}
    .leg-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}

    /* contador */
    #contador {{
      margin-top: 12px;
      padding-top: 10px;
      border-top: 1px solid var(--border);
      font-size: 11px;
      color: var(--muted);
      text-align: center;
    }}
    #contador b {{ color: var(--accent2); font-family: 'DM Mono', monospace; }}
    #atualizado {{ font-size: 10px; color: #3a3f58; margin-top: 3px; }}

    /* ── SIDEBAR (direita) ── */
    #sidebar {{
      position: fixed;
      top: 0; right: 0;
      width: var(--sidebar-w);
      height: 100%;
      z-index: 800;
      background: var(--surface);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      transform: translateX(100%);
      transition: transform .3s cubic-bezier(.4,0,.2,1);
      box-shadow: -8px 0 32px rgba(0,0,0,.4);
    }}
    #sidebar.open {{ transform: translateX(0); }}

    #sidebar-header {{
      padding: 16px;
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
    }}
    #sidebar-header h3 {{ font-size: 13px; font-weight: 600; color: var(--text); }}
    #sidebar-count {{ font-size: 11px; color: var(--muted); font-family: 'DM Mono', monospace; }}

    #sidebar-search {{
      margin: 12px 16px;
      padding: 8px 12px;
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text);
      font-family: 'DM Sans', sans-serif;
      font-size: 12px;
      outline: none;
      width: calc(100% - 32px);
      flex-shrink: 0;
    }}
    #sidebar-search::placeholder {{ color: var(--muted); }}
    #sidebar-search:focus {{ border-color: var(--accent); }}

    #sidebar-list {{
      flex: 1;
      overflow-y: auto;
      padding: 0 12px 12px;
    }}
    #sidebar-list::-webkit-scrollbar {{ width: 4px; }}
    #sidebar-list::-webkit-scrollbar-track {{ background: transparent; }}
    #sidebar-list::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 2px; }}

    .listing-card {{
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 10px;
      margin-bottom: 8px;
      overflow: hidden;
      cursor: pointer;
      transition: border-color .15s, transform .15s;
    }}
    .listing-card:hover {{ border-color: var(--accent); transform: translateX(-2px); }}
    .listing-card.novo {{ border-color: var(--new); }}

    .card-img {{
      width: 100%;
      height: 120px;
      object-fit: cover;
      display: block;
      background: var(--border);
    }}
    .card-no-img {{
      width: 100%;
      height: 60px;
      background: var(--surface2);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      color: var(--border);
    }}
    .card-body {{ padding: 10px 12px; }}
    .card-novo-badge {{
      display: inline-block;
      background: var(--new);
      color: white;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: .06em;
      padding: 2px 6px;
      border-radius: 4px;
      margin-bottom: 5px;
      text-transform: uppercase;
    }}
    .card-titulo {{
      font-size: 12px;
      font-weight: 500;
      color: var(--text);
      line-height: 1.4;
      margin-bottom: 6px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    .card-preco {{
      font-size: 14px;
      font-weight: 600;
      color: var(--accent2);
      font-family: 'DM Mono', monospace;
      margin-bottom: 4px;
    }}
    .card-meta {{
      display: flex;
      gap: 10px;
      font-size: 11px;
      color: var(--muted);
      flex-wrap: wrap;
    }}
    .card-fonte {{
      font-size: 10px;
      color: var(--muted);
      margin-top: 4px;
      text-align: right;
    }}

    /* botão tema */
    #btn-theme {{
      position: fixed;
      top: 16px;
      left: 16px;
      z-index: 900;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      width: 36px; height: 36px;
      font-size: 16px;
      cursor: pointer;
      box-shadow: 0 2px 8px rgba(0,0,0,.3);
      transition: background .2s;
      display: flex; align-items: center; justify-content: center;
    }}
    #btn-theme:hover {{ background: var(--surface2); }}

    /* botão abrir sidebar */
    #btn-sidebar {{
      position: fixed;
      top: 50%;
      right: 0;
      transform: translateY(-50%);
      z-index: 850;
      background: var(--surface);
      border: 1px solid var(--border);
      border-right: none;
      border-radius: 10px 0 0 10px;
      padding: 12px 8px;
      cursor: pointer;
      color: var(--accent2);
      font-size: 18px;
      writing-mode: vertical-rl;
      letter-spacing: .05em;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      display: flex;
      align-items: center;
      gap: 8px;
      transition: background .2s, right .3s cubic-bezier(.4,0,.2,1);
      box-shadow: -4px 0 16px rgba(0,0,0,.3);
    }}
    #btn-sidebar.shifted {{ right: var(--sidebar-w); }}
    #btn-sidebar:hover {{ background: var(--surface2); }}
    #btn-icon {{ font-size: 14px; writing-mode: horizontal-tb; }}

    /* ── POPUP ── */
    .leaflet-popup-content-wrapper {{
      background: var(--surface) !important;
      border: 1px solid var(--border) !important;
      border-radius: var(--radius) !important;
      box-shadow: 0 8px 32px rgba(0,0,0,.6) !important;
      padding: 0 !important;
      overflow: hidden;
    }}
    .leaflet-popup-tip-container {{ display: none; }}
    .leaflet-popup-content {{ margin: 0 !important; width: 280px !important; }}
    .leaflet-popup-close-button {{
      color: var(--muted) !important;
      top: 8px !important;
      right: 8px !important;
      font-size: 18px !important;
      z-index: 10;
    }}

    .popup-img {{
      width: 100%;
      height: 150px;
      object-fit: cover;
      display: block;
    }}
    .popup-no-img {{
      width: 100%;
      height: 60px;
      background: var(--surface2);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
    }}
    .popup-body {{ padding: 12px 14px; }}
    .popup-novo {{
      display: inline-block;
      background: var(--new);
      color: white;
      font-size: 10px;
      font-weight: 700;
      padding: 2px 8px;
      border-radius: 4px;
      margin-bottom: 8px;
      letter-spacing: .05em;
    }}
    .popup-titulo {{
      font-size: 13px;
      font-weight: 600;
      color: var(--text);
      margin-bottom: 8px;
      line-height: 1.4;
    }}
    .popup-preco {{
      font-size: 18px;
      font-weight: 700;
      color: var(--accent2);
      font-family: 'DM Mono', monospace;
      margin-bottom: 8px;
    }}
    .popup-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      margin-bottom: 10px;
    }}
    .popup-pill {{
      background: var(--surface2);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 5px 8px;
      font-size: 11px;
      color: var(--muted);
    }}
    .popup-pill b {{ color: var(--text); display: block; font-size: 12px; }}
    .popup-link {{
      display: block;
      width: 100%;
      padding: 9px;
      background: #4f46e5 !important;
      color: #ffffff !important;
      text-align: center;
      border-radius: 8px;
      text-decoration: none !important;
      font-size: 12px;
      font-weight: 700;
      margin-top: 8px;
      transition: background .15s;
      letter-spacing: .02em;
    }}
    .popup-link:hover {{ background: #4338ca !important; color: #ffffff !important; }}
    .leaflet-popup-content a.popup-link,
    .leaflet-popup-content a.popup-link:visited,
    .leaflet-popup-content a.popup-link:hover {{
      color: #ffffff !important;
    }}
    .hist-details {{
      margin-top: 8px;
      font-size: 11px;
    }}
    .hist-details summary {{
      cursor: pointer;
      color: var(--accent2);
      font-size: 11px;
      padding: 4px 0;
    }}
    .hist-table {{
      width: 100%;
      font-size: 11px;
      margin-top: 4px;
      border-collapse: collapse;
      color: var(--muted);
    }}
    .hist-table th, .hist-table td {{
      text-align: left;
      padding: 3px 4px;
      border-bottom: 1px solid var(--border);
    }}
  </style>
</head>
<body>

<div id="map"></div>

<!-- Painel de filtros -->
<div id="painel">
  <h4>⬡ Filtros</h4>

  <div class="f-block">
    <div class="f-label">Área mínima <span id="lbl-area">0 m²</span></div>
    <input type="range" id="sl-area" min="0" max="{area_max}" step="50" value="0">
  </div>

  <div class="f-block">
    <div class="f-label">Preço máximo <span id="lbl-preco">Todos</span></div>
    <input type="range" id="sl-preco" min="0" max="{preco_max}" step="10000" value="{preco_max}">
  </div>

  <div class="f-block">
    <div class="toggle-row">
      <label class="sw">
        <input type="checkbox" id="tog-novos">
        <span class="sw-track"></span>
      </label>
      <span>Apenas novos anúncios</span>
    </div>
  </div>

  <div class="legenda">
    <div class="leg-title">Preço</div>
    <div class="leg-item"><div class="leg-dot" style="background:var(--green)"></div> Até R$ 100k</div>
    <div class="leg-item"><div class="leg-dot" style="background:var(--blue)"></div> R$ 100k – R$ 300k</div>
    <div class="leg-item"><div class="leg-dot" style="background:var(--orange)"></div> R$ 300k – R$ 600k</div>
    <div class="leg-item"><div class="leg-dot" style="background:var(--red)"></div> Acima de R$ 600k</div>
    <div class="leg-item"><div class="leg-dot" style="background:var(--muted)"></div> Não informado</div>
    <div class="leg-item"><div class="leg-dot" style="background:var(--new)"></div> <b style="color:var(--text)">Novo</b></div>
  </div>

  <div id="contador">
    <b id="n-vis">0</b> de <b>{len(dados_js)}</b> anúncios visíveis
    <div id="atualizado">Atualizado: {agora}</div>
  </div>
</div>

<!-- Toggle dark/light -->
<button id="btn-theme" onclick="toggleTheme()" title="Alternar tema">🌙</button>

<!-- Botão sidebar -->
<div id="btn-sidebar" onclick="toggleSidebar()">
  <span id="btn-icon">☰</span>
  Listagens
</div>

<!-- Sidebar -->
<div id="sidebar">
  <div id="sidebar-header">
    <h3>📋 Listagens visíveis</h3>
    <span id="sidebar-count">0 anúncios</span>
  </div>
  <input type="text" id="sidebar-search" placeholder="Buscar por título ou localização...">
  <div id="sidebar-list"></div>
</div>

<script>
const DADOS = {dados_json};
const PRECO_MAX = {preco_max};

// ── Tema ──
let isDark = true;
function toggleTheme() {{
  isDark = !isDark;
  const r = document.documentElement;
  if (!isDark) {{
    r.style.setProperty('--bg',       '#f1f5f9');
    r.style.setProperty('--surface',  '#ffffff');
    r.style.setProperty('--surface2', '#f8fafc');
    r.style.setProperty('--border',   '#e2e8f0');
    r.style.setProperty('--text',     '#1e293b');
    r.style.setProperty('--muted',    '#64748b');
    document.getElementById('btn-theme').textContent = '☀️';
    // tiles claros
    tileLayer.setUrl('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png');
    document.querySelectorAll('.leaflet-tile').forEach(t => t.style.filter = '');
  }} else {{
    r.style.setProperty('--bg',       '#0f1117');
    r.style.setProperty('--surface',  '#1a1d27');
    r.style.setProperty('--surface2', '#22263a');
    r.style.setProperty('--border',   '#2e3248');
    r.style.setProperty('--text',     '#e2e8f0');
    r.style.setProperty('--muted',    '#64748b');
    document.getElementById('btn-theme').textContent = '🌙';
    tileLayer.setUrl('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png');
    document.querySelectorAll('.leaflet-tile').forEach(t => t.style.filter = 'brightness(0.85) saturate(0.7)');
  }}
}}

// ── Mapa ──
const map = L.map('map', {{ zoomControl: false }}).setView([{CRICIUMA[0]}, {CRICIUMA[1]}], 12);
L.control.zoom({{ position: 'topleft' }}).addTo(map);

const tileLayer = L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution: '© OpenStreetMap © CARTO',
  maxZoom: 20
}});
tileLayer.addTo(map);

L.circle([{CRICIUMA[0]}, {CRICIUMA[1]}], {{
  radius: 30000,
  color: '#6366f1',
  fill: true,
  fillOpacity: 0.04,
  weight: 1,
  dashArray: '6 4'
}}).bindTooltip('Raio de 30km').addTo(map);

// ── Marcadores ──
let cluster = L.markerClusterGroup({{ chunkedLoading: true, maxClusterRadius: 50 }});
map.addLayer(cluster);

function criarIcone(d) {{
  return L.divIcon({{
    className: '',
    html: `<div style="
      background:${{d.cor}};
      border-radius:50%;
      width:26px;height:26px;
      display:flex;align-items:center;justify-content:center;
      font-size:12px;
      box-shadow:0 2px 8px rgba(0,0,0,.5);
      border:2px solid rgba(255,255,255,.15);
      transition:transform .15s;
    ">${{d.novo ? '★' : '⌂'}}</div>`,
    iconSize: [26,26],
    iconAnchor: [13,13],
    popupAnchor: [0,-16],
  }});
}}

function buildPopup(d) {{
  const img = d.foto
    ? `<img class="popup-img" src="${{d.foto}}" alt="" onerror="this.style.display='none'">`
    : `<div class="popup-no-img">🏡</div>`;
  const badge = d.novo ? `<div class="popup-novo">🆕 NOVO</div>` : '';
  return `<div>
    ${{img}}
    <div class="popup-body">
      ${{badge}}
      <div class="popup-titulo">${{d.titulo}}</div>
      <div class="popup-preco">${{d.preco_fmt}}</div>
      <div class="popup-grid">
        <div class="popup-pill"><b>${{d.area_fmt}}</b>Área</div>
        <div class="popup-pill"><b>${{d.loc || '—'}}</b>Local</div>
        <div class="popup-pill"><b>${{d.fonte}}</b>Fonte</div>
        <div class="popup-pill"><b>${{d.data || '—'}}</b>Detectado</div>
      </div>
      ${{d.hist}}
      <a class="popup-link" href="${{d.url}}" target="_blank">Ver anúncio ↗</a>
    </div>
  </div>`;
}}

const marcadores = DADOS.map(d => {{
  const m = L.marker([d.lat, d.lon], {{ icon: criarIcone(d) }});
  m.bindPopup(buildPopup(d), {{ maxWidth: 300, minWidth: 280 }});
  m.bindTooltip(`${{d.novo ? '🆕 ' : ''}}${{d.preco_fmt}} · ${{d.area_fmt}}`);
  m._d = d;
  return m;
}});

// ── Sidebar ──
let sidebarOpen = false;

function toggleSidebar() {{
  sidebarOpen = !sidebarOpen;
  document.getElementById('sidebar').classList.toggle('open', sidebarOpen);
  document.getElementById('btn-sidebar').classList.toggle('shifted', sidebarOpen);
  document.getElementById('btn-icon').textContent = sidebarOpen ? '✕' : '☰';
}}

let visiveis = [];

function buildSidebar(lista) {{
  const q = document.getElementById('sidebar-search').value.toLowerCase();
  const filtrados = q ? lista.filter(d =>
    d.titulo.toLowerCase().includes(q) || d.loc.toLowerCase().includes(q)
  ) : lista;

  document.getElementById('sidebar-count').textContent = filtrados.length + ' anúncios';
  const el = document.getElementById('sidebar-list');
  el.innerHTML = '';

  filtrados.forEach((d, i) => {{
    const card = document.createElement('div');
    card.className = 'listing-card' + (d.novo ? ' novo' : '');
    const img = d.foto
      ? `<img class="card-img" src="${{d.foto}}" alt="" loading="lazy" onerror="this.style.display='none'">`
      : `<div class="card-no-img">🏡</div>`;
    const badge = d.novo ? `<div class="card-novo-badge">🆕 novo</div>` : '';
    card.innerHTML = `
      ${{img}}
      <div class="card-body">
        ${{badge}}
        <div class="card-titulo">${{d.titulo}}</div>
        <div class="card-preco">${{d.preco_fmt}}</div>
        <div class="card-meta">
          <span>📐 ${{d.area_fmt}}</span>
          <span>📍 ${{d.loc}}</span>
        </div>
        <div class="card-fonte">${{d.fonte}}</div>
      </div>`;
    card.addEventListener('click', () => {{
      map.setView([d.lat, d.lon], 16);
      // encontra o marcador e abre o popup
      marcadores.forEach(m => {{
        if (m._d === d) {{
          cluster.zoomToShowLayer(m, () => m.openPopup());
        }}
      }});
    }});
    el.appendChild(card);
  }});
}}

// ── Filtros ──
function aplicar() {{
  const areaMin  = parseInt(document.getElementById('sl-area').value) || 0;
  const precoMax = parseInt(document.getElementById('sl-preco').value) || PRECO_MAX;
  const soNovos  = document.getElementById('tog-novos').checked;

  cluster.clearLayers();
  visiveis = [];

  marcadores.forEach(m => {{
    const d = m._d;
    const areaOk  = areaMin === 0 || (d.area && d.area >= areaMin);
    const precoOk = d.preco === 0 || d.preco <= precoMax;
    const novoOk  = !soNovos || d.novo;
    if (areaOk && precoOk && novoOk) {{
      cluster.addLayer(m);
      visiveis.push(d);
    }}
  }});

  document.getElementById('n-vis').textContent = visiveis.length;
  buildSidebar(visiveis);
}}

// Labels dos sliders
document.getElementById('sl-area').addEventListener('input', function() {{
  document.getElementById('lbl-area').textContent = (+this.value).toLocaleString('pt-BR') + ' m²';
  aplicar();
}});
document.getElementById('sl-preco').addEventListener('input', function() {{
  const v = +this.value;
  document.getElementById('lbl-preco').textContent =
    v >= PRECO_MAX ? 'Todos' : 'R$ ' + v.toLocaleString('pt-BR');
  aplicar();
}});
document.getElementById('tog-novos').addEventListener('change', aplicar);
document.getElementById('sidebar-search').addEventListener('input', () => buildSidebar(visiveis));

// Init
aplicar();
</script>
</body>
</html>"""

    with open(output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[Mapa] Salvo em {output} ({len(dados_js)} marcadores)")
