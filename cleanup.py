"""
Utilitário de limpeza do banco de dados.
Execute manualmente quando precisar remover anúncios por estado ou cidade.
"""
import sqlite3

DB = "anuncios.db"


def deletar_por_estado(estado):
    con = sqlite3.connect(DB)
    cur = con.execute("DELETE FROM anuncios WHERE estado = ?", (estado,))
    con.commit()
    print(f"🗑️  Removidos {cur.rowcount} anúncios do estado '{estado}'")
    con.close()


def deletar_por_cidade(cidade):
    con = sqlite3.connect(DB)
    cur = con.execute("DELETE FROM anuncios WHERE cidade = ?", (cidade,))
    con.commit()
    print(f"🗑️  Removidos {cur.rowcount} anúncios da cidade '{cidade}'")
    con.close()


def deletar_por_cidade_like(cidade):
    con = sqlite3.connect(DB)
    cur = con.execute("DELETE FROM anuncios WHERE cidade LIKE ?", (f"%{cidade}%",))
    con.commit()
    print(f"🗑️  Removidos {cur.rowcount} anúncios com cidade contendo '{cidade}'")
    con.close()


def deletar_por_fonte(fonte):
    con = sqlite3.connect(DB)
    cur = con.execute("DELETE FROM anuncios WHERE fonte = ?", (fonte,))
    con.commit()
    print(f"🗑️  Removidos {cur.rowcount} anúncios da fonte '{fonte}'")
    con.close()


def listar_estados():
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT estado, COUNT(*) FROM anuncios GROUP BY estado").fetchall()
    con.close()
    print("\n📊 Anúncios por estado:")
    for estado, total in rows:
        print(f"   {estado or '(vazio)'}: {total}")


def listar_cidades(estado=None):
    con = sqlite3.connect(DB)
    if estado:
        rows = con.execute(
            "SELECT cidade, COUNT(*) FROM anuncios WHERE estado = ? GROUP BY cidade ORDER BY COUNT(*) DESC",
            (estado,)
        ).fetchall()
    else:
        rows = con.execute(
            "SELECT cidade, estado, COUNT(*) FROM anuncios GROUP BY cidade, estado ORDER BY COUNT(*) DESC"
        ).fetchall()
    con.close()
    print(f"\n📊 Anúncios por cidade{f' ({estado})' if estado else ''}:")
    for row in rows:
        if estado:
            print(f"   {row[0] or '(vazio)'}: {row[1]}")
        else:
            print(f"   {row[0] or '(vazio)'} ({row[1] or '?'}): {row[2]}")


def diagnostico():
    con = sqlite3.connect(DB)
    print("\n" + "=" * 60)
    print("📋 DIAGNÓSTICO COMPLETO DO BANCO")
    print("=" * 60)

    total = con.execute("SELECT COUNT(*) FROM anuncios").fetchone()[0]
    ativos = con.execute("SELECT COUNT(*) FROM anuncios WHERE ativo = 1").fetchone()[0]
    inativos = con.execute("SELECT COUNT(*) FROM anuncios WHERE ativo = 0").fetchone()[0]
    print(f"\n📦 Total: {total} | ✅ Ativos: {ativos} | ❌ Inativos: {inativos}")

    print("\n📊 Por estado:")
    for row in con.execute("SELECT estado, COUNT(*) FROM anuncios GROUP BY estado ORDER BY COUNT(*) DESC"):
        print(f"   '{row[0] or ''}': {row[1]}")

    print("\n📊 Por fonte:")
    for row in con.execute("SELECT fonte, COUNT(*) FROM anuncios GROUP BY fonte ORDER BY COUNT(*) DESC"):
        print(f"   '{row[0] or ''}': {row[1]}")

    print("\n📊 Todas as cidades (ordem por quantidade):")
    for row in con.execute("""
        SELECT cidade, estado, fonte, COUNT(*) as total
        FROM anuncios
        GROUP BY cidade, estado, fonte
        ORDER BY total DESC
    """):
        print(f"   {row[0] or '(vazio)'} ({row[1] or '?'}) [{row[2]}]: {row[3]}")

    print("\n" + "=" * 60)
    con.close()


CIDADES_RS = [
    # Vale do Paranhana / Encosta da Serra / Litoral Norte / Vale do Rio Pardo
    "Maquiné", "Osório", "Santa Cruz do Sul", "São José do Hortêncio", "Três Coroas",
    # Litoral / Planície Costeira
    "Balneário Pinhal", "Caraá", "Cidreira", "Curumim", "Mampituba",
    "Morrinhos do Sul", "Mostardas", "Palmares do Sul", "Sentinela do Sul",
    "Tavares", "Tramandaí", "Três Forquilhas",
    # Interior
    "Arvorezinha", "Barão", "Barra do Ribeiro", "Bom Princípio", "Bom Retiro do Sul",
    "Brochier", "Cachoeira do Sul", "Camaquã", "Colinas", "Dom Feliciano",
    "Encruzilhada do Sul", "Estrela", "Feliz", "General Câmara", "Harmonia",
    "Igrejinha", "Lajeado", "Linha Nova", "Mariana Pimentel", "Marques de Souza",
    "Passo do Sobrado", "Paverama", "Presidente Lucena", "Putinga", "Rio Pardo",
    "Riozinho", "Roca Sales", "Santa Clara do Sul", "São Sebastião do Caí",
    "Sinimbu", "Tapes", "Taquari", "Venâncio Aires", "Vera Cruz",
]


def deletar_cidades_rs():
    con = sqlite3.connect(DB)
    total = 0
    for cidade in CIDADES_RS:
        cur = con.execute("DELETE FROM anuncios WHERE cidade = ?", (cidade,))
        if cur.rowcount > 0:
            print(f"🗑️  {cidade}: {cur.rowcount} removidos")
            total += cur.rowcount
    con.commit()
    con.close()
    print(f"\n✅ Total removido: {total} anúncios do RS")


if __name__ == "__main__":
    print("=== Cleanup — Monitor de Terrenos ===\n")

    # ── Edite abaixo conforme necessário ──────────────────────────────────────

    deletar_cidades_rs()

    # diagnostico()
    # deletar_por_estado("RS")
    # deletar_por_cidade("Torres")
    # deletar_por_cidade_like("Torres")
    # deletar_por_fonte("OLX")

    # ─────────────────────────────────────────────────────────────────────────

    print("\n✅ Concluído!")
    listar_estados()
