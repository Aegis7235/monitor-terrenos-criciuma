"""
Monitor de Terrenos — Sul Catarinense
Roda no GitHub Actions a cada 6h. Salva mapa + log em /docs (GitHub Pages).
"""
import os
from datetime import datetime
from scrapers.olx_scraper import scrape_olx
from utils.database import (
    init_db, salvar_anuncios, carregar_todos,
    carregar_sem_coordenadas, atualizar_coordenadas, total_no_banco
)
from utils.geocoder import geocodificar_anuncios
from utils.map_generator import gerar_mapa

LOG = "docs/log_novidades.md"

# ── Configurações ─────────────────────────────────────────────────────────────
LIMITE_PENDENTES = 50    # Se houver mais pendentes que isso, pula o scraping
GEO_POR_RODADA   = 200  # Quantos anúncios geocodificar por execução
FORCAR_SCRAPING  = False # True = ignora o limite de pendentes e força scraping
APENAS_MAPA      = False # True = pula scraping e geocodificação, só gera o mapa
# ─────────────────────────────────────────────────────────────────────────────


def escrever_log(novos):
    os.makedirs("docs", exist_ok=True)
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    with open(LOG, "a", encoding="utf-8") as f:
        if novos:
            f.write(f"\n## 🆕 {len(novos)} novos anúncios — {agora}\n\n")
            for a in novos:
                f.write(f"- **{a.get('titulo','')[:70]}**\n")
                f.write(f"  - 💰 {a.get('preco') and 'R$ {:,.0f}'.format(a['preco']).replace(',','.') or 'Não informado'}"
                        f" | 📐 {a.get('area_m2') or '?'} m²\n")
                f.write(f"  - 📍 {a.get('bairro','')} — {a.get('cidade','')}\n")
                f.write(f"  - 🔗 {a.get('url','')}\n\n")
        else:
            f.write(f"\n## ✅ Sem novidades — {agora}\n\n")


def main():
    sep = "=" * 55
    print(sep)
    print("  Monitor de Terrenos | Sul Catarinense")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(sep)

    # 1. Banco
    init_db()

    if APENAS_MAPA:
        print("\n🗺️  Modo APENAS_MAPA — pulando scraping e geocodificação...")
        novos = []
    else:
        # 2. Verifica pendentes
        pendentes = carregar_sem_coordenadas(LIMITE_PENDENTES + 1)
        novos = []

        if len(pendentes) > LIMITE_PENDENTES and not FORCAR_SCRAPING:
            print(f"\n⏭️  {len(pendentes)} anúncios pendentes de geocodificação.")
            print(f"   Scraping pulado — geocodificando primeiro.")
        else:
            print(f"\n  Pendentes: {len(pendentes)} — iniciando scraping...")

            # 3. Coleta OLX
            print("\n▶ Coletando OLX...")
            olx = scrape_olx()
            print(f"\n  Total coletado: {len(olx)} anúncios")

            # 4. Salva / detecta novos
            novos = salvar_anuncios(olx)
            print(f"  🆕 Novos: {len(novos)}")

        # 5. Geocodifica pendentes
        pendentes = carregar_sem_coordenadas(GEO_POR_RODADA)
        if pendentes:
            print(f"\n▶ Geocodificando {len(pendentes)} anúncios...")
            geocodificar_anuncios(pendentes, atualizar_coordenadas)

    # 6. Mapa
    print("\n▶ Gerando mapa...")
    todos_coords = carregar_todos()
    novos_ids = [a["id"] for a in novos]
    gerar_mapa(todos_coords, novos_ids=novos_ids)

    # 7. Log
    escrever_log(novos)

    print(f"\n{sep}")
    print(f"  ✅ Concluído!")
    print(f"  📦 Total no banco: {total_no_banco()}")
    print(f"  🗺️  Com coords no mapa: {len(todos_coords)}")
    print(f"  🆕 Novos esta rodada: {len(novos)}")
    print(sep)


if __name__ == "__main__":
    main()
