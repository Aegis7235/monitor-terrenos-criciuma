"""
SQLite — persiste anúncios, detecta novos, rastreia histórico de preços.
"""
import sqlite3, json
from datetime import datetime

DB = "anuncios.db"


def init_db():
    con = sqlite3.connect(DB)
    c = con.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS anuncios (
            id            TEXT PRIMARY KEY,
            titulo        TEXT,
            preco         INTEGER,
            area_m2       INTEGER,
            cidade        TEXT,
            bairro        TEXT,
            estado        TEXT,
            url           TEXT,
            fonte         TEXT,
            descricao     TEXT,
            lat           REAL,
            lon           REAL,
            primeira_vez  TEXT,
            ultima_coleta TEXT,
            ativo         INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS historico_preco (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            anuncio_id TEXT,
            preco      INTEGER,
            data       TEXT
        );
    """)
    con.commit()
    con.close()


def salvar_anuncios(anuncios):
    """Salva/atualiza anúncios. Retorna lista dos novos."""
    con = sqlite3.connect(DB)
    c   = con.cursor()
    novos = []
    agora = datetime.now().isoformat()

    for a in anuncios:
        c.execute("SELECT id, preco FROM anuncios WHERE id = ?", (a["id"],))
        row = c.fetchone()

        if not row:
            novos.append(a)
            c.execute("""
                INSERT INTO anuncios
                  (id,titulo,preco,area_m2,cidade,bairro,estado,url,fonte,
                   descricao,lat,lon,primeira_vez,ultima_coleta,ativo)
                VALUES (?,?,?,?,?,?,?,?,?,?,NULL,NULL,?,?,1)
            """, (a["id"], a.get("titulo"), a.get("preco"), a.get("area_m2"),
                  a.get("cidade"), a.get("bairro"), a.get("estado"),
                  a.get("url"), a.get("fonte"), a.get("descricao"), agora, agora))
            if a.get("preco"):
                c.execute("INSERT INTO historico_preco (anuncio_id,preco,data) VALUES (?,?,?)",
                          (a["id"], a["preco"], agora))
        else:
            # Detecta mudança de preço
            preco_anterior = row[1]
            if a.get("preco") and a["preco"] != preco_anterior:
                c.execute("INSERT INTO historico_preco (anuncio_id,preco,data) VALUES (?,?,?)",
                          (a["id"], a["preco"], agora))
            c.execute("""
                UPDATE anuncios SET ultima_coleta=?, preco=?, ativo=1
                WHERE id=?
            """, (agora, a.get("preco"), a["id"]))

    con.commit()
    con.close()
    return novos


def carregar_todos():
    """Retorna todos os anúncios com coordenadas."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    c = con.cursor()
    c.execute("""
        SELECT a.*, h.historico
        FROM anuncios a
        LEFT JOIN (
            SELECT anuncio_id,
                   json_group_array(json_object('preco', preco, 'data', data)) as historico
            FROM historico_preco
            GROUP BY anuncio_id
        ) h ON a.id = h.anuncio_id
        WHERE a.lat IS NOT NULL AND a.lon IS NOT NULL
        ORDER BY a.primeira_vez DESC
    """)
    rows = [dict(r) for r in c.fetchall()]
    con.close()
    return rows


def carregar_sem_coordenadas(limite=50):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    c = con.cursor()
    c.execute("""
        SELECT * FROM anuncios WHERE (lat IS NULL OR lon IS NULL) LIMIT ?
    """, (limite,))
    rows = [dict(r) for r in c.fetchall()]
    con.close()
    return rows


def atualizar_coordenadas(anuncio_id, lat, lon):
    con = sqlite3.connect(DB)
    con.cursor().execute(
        "UPDATE anuncios SET lat=?, lon=? WHERE id=?", (lat, lon, anuncio_id)
    )
    con.commit()
    con.close()


def total_no_banco():
    con = sqlite3.connect(DB)
    n = con.cursor().execute("SELECT COUNT(*) FROM anuncios").fetchone()[0]
    con.close()
    return n