# 🏡 Monitor de Terrenos — Criciúma/SC (raio 30km)

Monitora automaticamente anúncios de terrenos à venda na região de Criciúma, SC.  
Roda 4x/dia no GitHub Actions. Gera mapa interativo publicado via GitHub Pages.

## Fontes monitoradas
- **OLX** — via `__NEXT_DATA__` (JSON embutido, sem Selenium)
- **ZAP Imóveis / VivaReal** — via `cloudscraper` (bypass Cloudflare)

## Cidades cobertas (≤ 30km de Criciúma)
Criciúma • Içara • Forquilhinha • Nova Veneza • Cocal do Sul  
Morro da Fumaça • Siderópolis • Maracajá • Sangão • Balneário Rincão

## Como usar

### 1. Fork do repositório
Clique em **Fork** no GitHub.

### 2. Ative o GitHub Pages
Settings → Pages → Source: **Deploy from branch** → Branch: `main` → Pasta: `/docs`

### 3. Ative o GitHub Actions
Vá em **Actions** → habilite os workflows.

### 4. Primeira execução manual
Actions → "Monitor de Terrenos" → **Run workflow**

### 5. Acesse o mapa
```
https://SEU_USUARIO.github.io/monitor-terrenos-criciuma/mapa.html
```

## Legenda do mapa

| Ícone | Significado |
|-------|-------------|
| 🟢 Verde | Até R$ 100.000 |
| 🔵 Azul | R$ 100k – R$ 300k |
| 🟠 Laranja | R$ 300k – R$ 600k |
| 🔴 Vermelho | Acima de R$ 600k |
| ⚫ Cinza | Preço não informado |
| ⭐ Estrela vermelha | **Anúncio novo** (detectado nesta execução) |

O mapa tem **duas camadas**:
- 🆕 Novos anúncios (destacados)
- 🏡 Anúncios existentes (todos os demais)

Você pode ligar/desligar cada camada pelo controle no canto superior direito do mapa.

## Estrutura do projeto
```
├── scrapers/
│   ├── olx_scraper.py
│   └── vivareal_zap_scraper.py
├── utils/
│   ├── database.py        # SQLite + histórico de preços
│   ├── geocoder.py        # Nominatim (gratuito)
│   └── map_generator.py   # Folium → HTML
├── docs/
│   ├── mapa.html          # Mapa (GitHub Pages)
│   └── log_novidades.md   # Log de novos anúncios
├── anuncios.db            # Banco (persiste entre execuções)
├── main.py
├── requirements.txt
└── .github/workflows/monitor.yml
```

## Observações
- **OLX**: funciona de forma confiável
- **ZAP/VivaReal**: podem ser bloqueados ocasionalmente pelo Cloudflare
- **Facebook Marketplace**: não suportado (exige login). Use os alertas nativos do app
- O `anuncios.db` é commitado junto ao repositório para persistir o histórico
- Histórico de preço de cada anúncio aparece no popup do mapa