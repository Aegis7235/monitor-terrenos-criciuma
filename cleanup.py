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


if __name__ == "__main__":
    print("=== Cleanup — Monitor de Terrenos ===\n")
    listar_estados()

    # ── Edite abaixo conforme necessário ──────────────────────────────────────

    deletar_por_estado("RS")

    # deletar_por_cidade("Torres")
    # deletar_por_cidade("Capão da Canoa")
    # deletar_por_fonte("OLX")

    # ─────────────────────────────────────────────────────────────────────────

    print("\n✅ Limpeza concluída!")
    listar_estados()
    # Diagnóstico — remover depois
con = sqlite3.connect("anuncios.db")
rows = con.execute("SELECT id, cidade, estado, fonte FROM anuncios WHERE cidade IN ('Torres','Capão da Canoa','Arroio do Sal','Xangri-lá','Imbé') LIMIT 20").fetchall()
for r in rows:
    print(r)
con.close()
