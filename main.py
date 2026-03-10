"""
Monitor de Terrenos — Sul Catarinense
Roda no GitHub Actions a cada 6h. Salva mapa + log em /docs (GitHub Pages).
"""
import os
from datetime import datetime
from scrapers.olx_scraper        import scrape_olx
from scrapers.chavesnamao_scraper import scrape_chavesnamao
from utils.database import (
    init_db, salvar_anuncios, carregar_todos,
    carregar_sem_coordenadas, atualizar_coordenadas, total_no_banco
)
from utils.geocoder      import geocodificar_anuncios
from utils.map_generator import gerar_mapa
from utils.telegram_notify import enviar_anuncio, enviar_resumo

LOG = "docs/log_novidades.md"

# ── Configurações ─────────────────────────────────────────────────────────────
LIMITE_PENDENTES = 50    # Se houver mais pendentes que isso, pula o scraping
GEO_POR_RODADA   = 1000  # Quantos anúncios geocodificar por execução
FORCAR_SCRAPING  = False # True = ignora o limite de pendentes e força scraping
APENAS_MAPA      = False # True = pula scraping e geocodificação, só gera o mapa

# Fontes ativas — comente a linha ou mude para False para desativar
FONTES = {
    "olx":         True,
    "chavesnamao": True,
}
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


def notificar_telegram(novos, area_minima_m2=5000):
    """Envia para o Telegram apenas anúncios com área >= area_minima_m2."""
    if not novos:
        print("\n▶ Telegram: nenhum anúncio novo para enviar.")
        return

    filtrados = [a for a in novos if (a.get("area_m2") or 0) >= area_minima_m2]
    ignorados = len(novos) - len(filtrados)

    print(f"\n▶ Telegram: {len(filtrados)} anúncio(s) acima de {area_minima_m2} m² "
          f"| {ignorados} ignorados (área < {area_minima_m2} m² ou não informada)")

    if not filtrados:
        print("  Nenhum anúncio passou pelo filtro de área — nada será enviado.")
        return

    enviados = 0
    for anuncio in filtrados:
        ok = enviar_anuncio(anuncio)
        if ok:
            enviados += 1

    enviar_resumo(enviados=enviados, filtrados=len(filtrados), ignorados=ignorados)

    print(f"  Telegram: {enviados}/{len(filtrados)} enviados com sucesso "
          f"| {len(filtrados) - enviados} falhas")


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
            todos_coletados = []

            # 3. Coleta OLX
            if FONTES.get("olx"):
                print("\n▶ Coletando OLX...")
                olx = scrape_olx()
                print(f"  OLX: {len(olx)} anúncios")
                todos_coletados.extend(olx)

            # 4. Coleta Chaves na Mão
            if FONTES.get("chavesnamao"):
                print("\n▶ Coletando Chaves na Mão...")
                cnm = scrape_chavesnamao()
                print(f"  ChavesNaMão: {len(cnm)} anúncios")
                todos_coletados.extend(cnm)

            print(f"\n  Total coletado: {len(todos_coletados)} anúncios")

            # 5. Salva / detecta novos
            novos = salvar_anuncios(todos_coletados)
            print(f"  🆕 Novos: {len(novos)}")

        # 6. Geocodifica pendentes
        pendentes = carregar_sem_coordenadas(GEO_POR_RODADA)
        if pendentes:
            print(f"\n▶ Geocodificando {len(pendentes)} anúncios...")
            geocodificar_anuncios(pendentes, atualizar_coordenadas)

    # 7. Mapa
    print("\n▶ Gerando mapa...")
    todos_coords = carregar_todos()
    novos_ids = [a["id"] for a in novos]
    gerar_mapa(todos_coords, novos_ids=novos_ids)

    # 8. Log
    escrever_log(novos)

    # 9. Notificações Telegram
    notificar_telegram(novos)

    print(f"\n{sep}")
    print(f"  ✅ Concluído!")
    print(f"  📦 Total no banco: {total_no_banco()}")
    print(f"  🗺️  Com coords no mapa: {len(todos_coords)}")
    print(f"  🆕 Novos esta rodada: {len(novos)}")
    print(sep)


if __name__ == "__main__":
    main()
