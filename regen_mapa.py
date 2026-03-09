from utils.database import init_db, carregar_todos
from utils.map_generator import gerar_mapa

init_db()
todos = carregar_todos()
gerar_mapa(todos, novos_ids=[])
print(f"Mapa gerado com {len(todos)} anúncios")
