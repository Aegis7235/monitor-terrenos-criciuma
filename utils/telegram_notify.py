"""
Notificações Telegram para novos anúncios de terrenos.
"""
import os
import re
import time
import requests

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"

# Caracteres que precisam de escape no MarkdownV2
_ESCAPE_RE = re.compile(r'([_*\[\]()~`>#+\-=|{}.!\\])')


def _esc(text: str) -> str:
    """Escapa caracteres especiais para MarkdownV2."""
    return _ESCAPE_RE.sub(r'\\\1', str(text))


def _formatar_preco(preco) -> str:
    if not preco:
        return "Não informado"
    return "R$ {:,.0f}".format(preco).replace(",", ".")


def _log(icone: str, msg: str):
    """Print com timestamp para aparecer bem no log do GitHub Actions."""
    agora = time.strftime("%H:%M:%S")
    print(f"[Telegram {agora}] {icone} {msg}")


def enviar_anuncio(anuncio: dict, bot_token: str = None, chat_id: str = None) -> bool:
    """
    Envia um anúncio de terreno para o Telegram.
    Usa sendPhoto se tiver imagem; se a foto falhar, tenta novamente como texto.
    Retorna True se enviado com sucesso.
    """
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat  = chat_id   or os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat:
        _log("⚠️ ", "BOT_TOKEN ou CHAT_ID não configurados — abortando envios.")
        return False

    titulo     = (anuncio.get("titulo") or "Sem título")[:100]
    preco      = _formatar_preco(anuncio.get("preco"))
    area       = anuncio.get("area_m2")
    url        = anuncio.get("url", "")
    fonte      = anuncio.get("fonte", "")
    cidade     = anuncio.get("cidade", "")
    bairro     = anuncio.get("bairro", "")
    anuncio_id = anuncio.get("id", "?")
    local      = f"{bairro} — {cidade}" if bairro else cidade
    foto       = anuncio.get("foto") or ""

    linha_area = f"📐 {_esc(str(area))} m²\n" if area else ""

    caption = (
        f"🏡 *{_esc(titulo)}*\n\n"
        f"💰 {_esc(preco)}\n"
        f"{linha_area}"
        f"📍 {_esc(local)}\n"
        f"🔗 [Ver anúncio]({url})\n"
        f"_Fonte: {_esc(fonte)}_"
    )

    _log("📤", f"Enviando [{anuncio_id}] {titulo[:60]}")
    _log("   ", f"Área: {area} m² | Preço: {preco} | Foto: {'sim' if foto else 'não'}")

    # ── Tentativa 1: sendPhoto (se tiver foto) ────────────────────────────────
    if foto:
        try:
            resp = requests.post(
                TELEGRAM_API.format(token=token, method="sendPhoto"),
                json={
                    "chat_id":    chat,
                    "photo":      foto,
                    "caption":    caption,
                    "parse_mode": "MarkdownV2",
                },
                timeout=15,
            )
            if resp.ok:
                _log("✅", f"Enviado com foto [{anuncio_id}]")
                return True
            else:
                body = resp.json() if "application/json" in resp.headers.get("content-type", "") else {}
                _log("⚠️ ", f"sendPhoto falhou [{anuncio_id}] — HTTP {resp.status_code} "
                            f"| erro: {body.get('error_code')} — {body.get('description')} "
                            f"| URL foto: {foto[:80]}")
                _log("🔄 ", f"Tentando reenviar [{anuncio_id}] sem foto...")
        except requests.exceptions.Timeout:
            _log("⚠️ ", f"sendPhoto timeout [{anuncio_id}] — tentando sem foto...")
        except Exception as e:
            _log("⚠️ ", f"sendPhoto exceção [{anuncio_id}]: {type(e).__name__}: {e} — tentando sem foto...")

    # ── Tentativa 2: sendMessage (fallback sem foto) ──────────────────────────
    try:
        resp = requests.post(
            TELEGRAM_API.format(token=token, method="sendMessage"),
            json={
                "chat_id":                  chat,
                "text":                     caption,
                "parse_mode":               "MarkdownV2",
                "disable_web_page_preview": False,
            },
            timeout=15,
        )
        if resp.ok:
            sufixo = " (foto falhou, enviado como texto)" if foto else ""
            _log("✅", f"Enviado [{anuncio_id}]{sufixo}")
            return True
        else:
            body = resp.json() if "application/json" in resp.headers.get("content-type", "") else {}
            _log("❌", f"sendMessage falhou [{anuncio_id}] — HTTP {resp.status_code} "
                       f"| erro: {body.get('error_code')} — {body.get('description')}")
            _log("   ", f"Caption: {caption[:300]}")
            return False
    except requests.exceptions.Timeout:
        _log("❌", f"sendMessage timeout [{anuncio_id}] — sem resposta em 15s")
        return False
    except Exception as e:
        _log("❌", f"sendMessage exceção [{anuncio_id}]: {type(e).__name__}: {e}")
        return False


def enviar_resumo(enviados: int, filtrados: int, ignorados: int,
                  bot_token: str = None, chat_id: str = None) -> bool:
    """Envia mensagem de resumo ao final do monitoramento."""
    token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat  = chat_id   or os.environ.get("TELEGRAM_CHAT_ID", "")

    if not token or not chat:
        return False

    falhas = filtrados - enviados
    texto = (
        f"📊 *Resumo do monitoramento*\n\n"
        f"✅ Enviados: {enviados}\n"
        f"❌ Falhas no envio: {falhas}\n"
        f"⏭️ Ignorados \\(área \\< 5000 m²\\): {ignorados}"
    )

    try:
        resp = requests.post(
            TELEGRAM_API.format(token=token, method="sendMessage"),
            json={"chat_id": chat, "text": texto, "parse_mode": "MarkdownV2"},
            timeout=15,
        )
        if resp.ok:
            _log("✅", "Resumo enviado")
            return True
        else:
            _log("⚠️ ", f"Resumo falhou — HTTP {resp.status_code}: {resp.text[:100]}")
            return False
    except Exception as e:
        _log("⚠️ ", f"Resumo exceção: {type(e).__name__}: {e}")
        return False
