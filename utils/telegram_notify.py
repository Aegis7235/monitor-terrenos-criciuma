"""
Notificações Telegram para novos anúncios de terrenos.
"""
import os
import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _formatar_preco(preco):
    if not preco:
        return "Não informado"
    return "R$ {:,.0f}".format(preco).replace(",", ".")


def _formatar_area(area):
    if not area:
        return ""
    return f"📐 {area} m²\n"


def enviar_anuncio(anuncio: dict, bot_token: str = None, chat_id: str = None):
    """
    Envia um anúncio de terreno para o Telegram.
    Usa sendPhoto se tiver imagem, senão sendMessage.
    """
    token   = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat    = chat_id   or os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat:
        print("[Telegram] ⚠️  BOT_TOKEN ou CHAT_ID não configurados — pulando.")
        return False

    preco  = _formatar_preco(anuncio.get("preco"))
    area   = _formatar_area(anuncio.get("area_m2"))
    titulo = (anuncio.get("titulo") or "Sem título")[:100]
    url    = anuncio.get("url", "")
    fonte  = anuncio.get("fonte", "")
    cidade = anuncio.get("cidade", "")
    bairro = anuncio.get("bairro", "")
    local  = f"{bairro} — {cidade}" if bairro else cidade

    caption = (
        f"🏡 *{titulo}*\n\n"
        f"💰 {preco}\n"
        f"{area}"
        f"📍 {local}\n"
        f"🔗 [Ver anúncio]({url})\n"
        f"_Fonte: {fonte}_"
    )

    foto = anuncio.get("foto")

    try:
        if foto:
            resp = requests.post(
                TELEGRAM_API.format(token=token, method="sendPhoto"),
                json={
                    "chat_id":    chat,
                    "photo":      foto,
                    "caption":    caption,
                    "parse_mode": "Markdown",
                },
                timeout=15,
            )
        else:
            resp = requests.post(
                TELEGRAM_API.format(token=token, method="sendMessage"),
                json={
                    "chat_id":              chat,
                    "text":                 caption,
                    "parse_mode":           "Markdown",
                    "disable_web_page_preview": False,
                },
                timeout=15,
            )

        if resp.ok:
            print(f"[Telegram] ✅ Enviado: {titulo[:50]}")
            return True
        else:
            print(f"[Telegram] ❌ Erro {resp.status_code}: {resp.text[:200]}")
            return False

    except Exception as e:
        print(f"[Telegram] ❌ Exceção: {e}")
        return False


def enviar_resumo(total_novos: int, bot_token: str = None, chat_id: str = None):
    """Envia mensagem de resumo quando há novos anúncios."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat  = chat_id   or os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat:
        return False

    texto = f"✅ Monitoramento concluído — *{total_novos} novo(s) anúncio(s)* encontrado(s) hoje!"

    try:
        resp = requests.post(
            TELEGRAM_API.format(token=token, method="sendMessage"),
            json={"chat_id": chat, "text": texto, "parse_mode": "Markdown"},
            timeout=15,
        )
        return resp.ok
    except Exception:
        return False
