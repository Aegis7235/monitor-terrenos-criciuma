"""
Gera mapa HTML interativo com Folium.
- Todos os anúncios são exibidos
- Novos (detectados na última execução) têm ícone de estrela e cor diferente
- Anúncios antigos têm ícone de casa, coloridos por faixa de preço
- Histórico de preço aparece no popup quando disponível
"""
import os, json, folium
from folium.plugins import MarkerCluster
from datetime import datetime

CRICIUMA = (-28.6808, -49.3697)

def _cor(preco):
    if preco is None:   return "gray"
    if preco < 100_000: return "green"
    if preco < 300_000: return "blue"
    if preco < 600_000: return "orange"
    return "red"

def _fmt(preco):
    if preco is None: return "Preço não informado"
    return "R$ {:,.0f}".format(preco).replace(",", ".")

def _historico_html(hist_json):
    if not hist_json:
        return ""
    try:
        hist = json.loads(hist_json)
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

    m = folium.Map(location=CRICIUMA, zoom_start=12, tiles="CartoDB positron")

    # Círculo de raio
    folium.Circle(
        CRICIUMA, radius=30_000,
        color="#2980b9", fill=True, fill_opacity=0.06, weight=1.5,
        tooltip="Raio de 30km"
    ).add_to(m)

    folium.Marker(
        CRICIUMA, tooltip="Criciúma (centro)",
        icon=folium.Icon(color="black", icon="map-marker", prefix="fa")
    ).add_to(m)

    # Dois clusters: novos e existentes
    cluster_novos     = MarkerCluster(name="🆕 Novos anúncios").add_to(m)
    cluster_existentes = MarkerCluster(name="🏡 Anúncios existentes").add_to(m)

    for a in anuncios:
        if not a.get("lat") or not a.get("lon"):
            continue

        eh_novo = a["id"] in novos_ids
        cor     = "darkred"  if eh_novo else _cor(a.get("preco"))
        icone   = "star"     if eh_novo else "home"
        cluster = cluster_novos if eh_novo else cluster_existentes

        badge = ('<span style="background:#e74c3c;color:#fff;padding:2px 7px;'
                 'border-radius:3px;font-size:11px;font-weight:bold">🆕 NOVO</span><br><br>'
                 if eh_novo else "")

        hist_html = _historico_html(a.get("historico"))

        popup_html = f"""
        <div style="font-family:Arial,sans-serif;min-width:230px;max-width:280px">
          {badge}
          <b style="font-size:14px">{a.get('titulo','Terreno à venda')[:70]}</b>
          <hr style="margin:6px 0">
          💰 <b>{_fmt(a.get('preco'))}</b><br>
          📐 {a.get('area_m2') or '?'} m²<br>
          📍 {a.get('bairro') or ''}{' — ' if a.get('bairro') else ''}{a.get('cidade','')}<br>
          🏢 <small style="color:#666">{a.get('fonte','')}</small><br>
          📅 <small>Detectado: {(a.get('primeira_vez') or '')[:10]}</small><br>
          📅 <small>Última coleta: {(a.get('ultima_coleta') or '')[:10]}</small><br>
          {hist_html}
          <a href="{a.get('url','#')}" target="_blank"
             style="display:block;margin-top:8px;padding:6px;background:#2980b9;color:#fff;
                    text-align:center;border-radius:5px;text-decoration:none;font-size:13px">
            Ver anúncio ↗
          </a>
        </div>"""

        folium.Marker(
            location=[a["lat"], a["lon"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{'🆕 ' if eh_novo else ''}{_fmt(a.get('preco'))} | {a.get('cidade','')}",
            icon=folium.Icon(color=cor, icon=icone, prefix="fa")
        ).add_to(cluster)

    # Legenda
    legenda = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:9999;
                background:white;padding:14px 16px;border-radius:10px;
                box-shadow:0 2px 10px rgba(0,0,0,.25);font-family:Arial;font-size:13px">
      <b>🏡 Legenda — Preço</b><br>
      <span style="color:green">●</span> Até R$ 100k<br>
      <span style="color:blue">●</span> R$ 100k – R$ 300k<br>
      <span style="color:orange">●</span> R$ 300k – R$ 600k<br>
      <span style="color:red">●</span> Acima de R$ 600k<br>
      <span style="color:gray">●</span> Preço não informado<br>
      <span style="color:darkred">★</span> <b>Novo anúncio</b><br>
      <hr style="margin:6px 0">
      <small>Atualizado: {}</small>
    </div>""".format(datetime.now().strftime("%d/%m/%Y %H:%M"))

    m.get_root().html.add_child(folium.Element(legenda))
    folium.LayerControl(collapsed=False).add_to(m)

    m.save(output)
    print(f"[Mapa] Salvo em {output} ({len(anuncios)} marcadores)")