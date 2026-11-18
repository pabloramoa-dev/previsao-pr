from __future__ import annotations
import hashlib
import os
import re
import time

import requests

from .. import estado


def _cfg():
    user = os.environ.get("IG_USER_ID")
    token = os.environ.get("IG_ACCESS_TOKEN")
    # `or`, nao default do get: o workflow injeta a variavel mesmo quando ela
    # nao existe no repositorio, e ai o valor chega vazio em vez de ausente.
    version = os.environ.get("META_GRAPH_VERSION") or "v26.0"
    # `or`: o workflow injeta a variavel vazia quando ela nao existe no repositorio.
    expected = estado.handle()
    configured = os.environ.get("EXPECTED_IG_USERNAME") or expected
    if configured != expected:
        raise RuntimeError("EXPECTED_IG_USERNAME diverge da conta do canal")
    if not user or not token:
        raise RuntimeError("IG_USER_ID/IG_ACCESS_TOKEN ausentes")
    if not user.isascii() or not user.isdigit() or not re.fullmatch(r"v[0-9]+[.][0-9]+", version):
        raise RuntimeError("ID de usuário ou versão da Meta inválidos")
    return user, token, version, expected


def _check_response(response):
    if response.status_code >= 300:
        raise RuntimeError(f"Meta HTTP {response.status_code}")


def _get(url, **kwargs):
    for attempt in range(3):
        try:
            response = requests.get(url, allow_redirects=False, **kwargs)
        except requests.RequestException:
            if attempt == 2:
                raise RuntimeError("Falha de transporte na consulta à Meta") from None
        else:
            if response.status_code not in {429, 500, 502, 503, 504} or attempt == 2:
                return response
        time.sleep(2 ** attempt)


def _post(url, **kwargs):
    try:
        return requests.post(url, allow_redirects=False, **kwargs)
    except requests.RequestException:
        raise RuntimeError("Resposta da Meta indisponível após envio") from None


def base_url(version: str) -> str:
    # Centralizado para permitir regressão controlada de versão/host.
    return f"https://graph.instagram.com/{version}"


def verify_destination() -> dict:
    user, token, version, expected = _cfg()
    r = _get(f"{base_url(version)}/{user}", params={"fields":"id,username"}, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    _check_response(r)
    data = r.json()
    got = data.get("username") or ""
    if got != expected:
        raise RuntimeError(f"DESTINO BLOQUEADO: username retornado={got!r}, esperado={expected!r}")
    if str(data.get("id")) != user:
        raise RuntimeError("O ID retornado pela Meta diverge de IG_USER_ID")
    return data


def create_reel(video_url: str, caption: str) -> str:
    user, token, version, _ = _cfg()
    corpo = {
        "media_type":"REELS", "video_url":video_url, "caption":caption,
        "share_to_feed":"true"}
    # Capa da grade (o frame 0 do HyperFrames é só o cenário). Vem por variável
    # de ambiente para não mudar a assinatura usada pelo cli e pelos testes.
    capa_url = os.environ.get("PREVISAO_CAPA_URL", "").strip()
    capa_ms = os.environ.get("PREVISAO_CAPA_MS", "").strip()
    if capa_ms.isdigit() and int(capa_ms) > 0:
        corpo["thumb_offset"] = capa_ms
    if capa_url:
        corpo["cover_url"] = capa_url
    r = _post(f"{base_url(version)}/{user}/media", data=corpo, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    _check_response(r)
    return r.json()["id"]


def wait_ready(container_id: str, timeout_s: int = 300) -> None:
    _, token, version, _ = _cfg()
    end = time.time() + timeout_s
    while time.time() < end:
        r = _get(f"{base_url(version)}/{container_id}", params={"fields":"status_code"}, headers={"Authorization": f"Bearer {token}"}, timeout=30)
        _check_response(r)
        state = r.json().get("status_code")
        if state == "FINISHED": return
        if state in {"ERROR","EXPIRED"}: raise RuntimeError(f"container {state}")
        time.sleep(10)
    raise TimeoutError("Instagram container não concluiu")


def publish(container_id: str) -> str:
    user, token, version, _ = _cfg()
    r = _post(f"{base_url(version)}/{user}/media_publish", data={"creation_id":container_id}, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    _check_response(r)
    return r.json()["id"]


def caption_hash(caption: str) -> str:
    return hashlib.sha256(" ".join(caption.split()).encode()).hexdigest()[:16]

def find_published_caption(caption: str, limit: int = 25) -> dict | None:
    """Consulta mídias recentes e bloqueia legenda equivalente em retry/reexecução."""
    user, token, version, _ = _cfg()
    r = _get(f"{base_url(version)}/{user}/media", params={
        "fields":"id,caption,timestamp,permalink", "limit":str(limit)}, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    _check_response(r)
    target = " ".join((caption or "").split()).casefold()
    for item in r.json().get("data", []):
        current = " ".join((item.get("caption") or "").split()).casefold()
        if current and current == target:
            return item
    return None


def already_published_caption(caption: str, limit: int = 25) -> bool:
    return find_published_caption(caption, limit) is not None

