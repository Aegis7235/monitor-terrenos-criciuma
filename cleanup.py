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
    print(f"\n📦 Total de anúncios: {total}")

    print("\n📊 Por estado:")
    for row in con.execute("SELECT estado, COUNT(*) FROM anuncios GROUP BY estado ORDER BY COUNT(*) DESC"):
        print(f"   '{row[0] or ''}': {row[1]}")

    print("\n📊 Por fonte:")
    for row in con.execute("SELECT fonte, COUNT(*) FROM anuncios GROUP BY fonte ORDER BY COUNT(*) DESC"):
        print(f"   '{row[0] or ''}': {row[1]}")

    print("\n📊 Por estado+fonte:")
    for row in con.execute("SELECT estado, fonte, COUNT(*) FROM anuncios GROUP BY estado, fonte ORDER BY estado, fonte"):
        print(f"   estado='{row[0] or ''}' fonte='{row[1] or ''}': {row[2]}")

    print("\n🔍 Busca por cidades do RS:")
    for cidade in ["Torres", "Capão da Canoa", "Arroio do Sal", "Xangri", "Imbé"]:
        rows = con.execute(
            "SELECT id, cidade, estado, fonte FROM anuncios WHERE cidade LIKE ?",
            (f"%{cidade}%",)
        ).fetchall()
        if rows:
            print(f"   '{cidade}': {len(rows)} anúncios")
            for r in rows[:3]:
                print(f"      id={r[0]} cidade='{r[1]}' estado='{r[2]}' fonte='{r[3]}'")
        else:
            print(f"   '{cidade}': nenhum")

    print("\n" + "=" * 60)
    con.close()


if __name__ == "__main__":
    print("=== Cleanup — Monitor de Terrenos ===\n")

    # ── Edite abaixo conforme necessário ──────────────────────────────────────

    deletar_por_cidade_like("Torres")
    deletar_por_cidade_like("Capão da Canoa")
    deletar_por_cidade_like("Arroio do Sal")
    deletar_por_cidade_like("Xangri")
    deletar_por_cidade_like("Imbé")

    # deletar_por_estado("RS")
    # deletar_por_fonte("OLX")
    # diagnostico()

    # ─────────────────────────────────────────────────────────────────────────

    print("\n✅ Limpeza concluída!")
    listar_estados()
