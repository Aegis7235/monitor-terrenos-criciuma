"""
Regiões e cidades raspadas na OLX.

Cada região tem sua própria URL base (porque o estado e a região mudam o
caminho da URL na OLX) e a lista de cidades dela.

Pra parar de raspar uma cidade, comente a linha (coloque # na frente) ou apague.
Pra adicionar uma cidade nova numa região que JÁ existe aqui, é só adicionar
o slug dela na lista "cidades" daquela região.
Pra adicionar uma cidade de OUTRO estado/região, crie um novo bloco em REGIOES:
navegue na OLX até a listagem da cidade e copie a parte da URL que vem ANTES de
"/outras-cidades/NOME-DA-CIDADE" — isso é a "base".
"""

REGIOES = [
    # ── Sul Catarinense (SC) ──────────────────────────────────────────────────
    {
        "estado": "SC",
        "base": "https://www.olx.com.br/imoveis/terrenos/estado-sc/florianopolis-e-regiao",
        "cidades": [
            # Criciúma e região da Carbonífera
            "criciuma",
            "icara",
            "urussanga",
            "cocal-do-sul",
            "morro-da-fumaca",
            "treviso",
            "lauro-muller",
            "sideropolis",
            "nova-veneza",
            "forquilhinha",

            # Litoral Sul
            "ararangua",
            "balneario-rincao",
            "jaguaruna",
            "sangao",
            "maracaja",

            # Região de Turvo e entorno
            "turvo",
            "meleiro",
            "ermo",
            "morro-grande",

            # Extremo Sul SC (até a divisa com Torres/RS)
            "sombrio",
            "santa-rosa-do-sul",
            "sao-joao-do-sul",
            "passo-de-torres",
            "balneario-gaivota",
            "praia-grande",
            "timbe-do-sul",
            "jacinto-machado",
        ],
    },

    # ── Litoral Norte do Rio Grande do Sul (RS) ───────────────────────────────
    {
        "estado": "RS",
        "base": "https://www.olx.com.br/imoveis/terrenos/lotes/estado-rs/regioes-de-porto-alegre-torres-e-santa-cruz-do-sul",
        "cidades": [
            "torres",
        ],
    },
]

# Lista achatada de todos os slugs — usada pelo filtro de segurança do scraper.
# (mantida pra não quebrar quem importa CIDADES)
CIDADES = [cidade for regiao in REGIOES for cidade in regiao["cidades"]]
