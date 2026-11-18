"""CLI de publicacao — Plano Mestre v1.1, secoes 13.4 e 18.

Com `--queue`, o publicador deixa de ser cego: reivindica o item na fila antes
de falar com a Meta e grava o resultado nela depois. E isso que arma os vetos
de duplicata e de gancho repetido do motor editorial, que leem `status`
'published' e `published_at`.

Sem `--queue` o comportamento antigo continua valendo, para nao quebrar o
workflow manual que ja roda.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import time
from pathlib import Path

from ..collectors.base import now
from ..editorial.turnos import turno_do_formato

from . import state
from .. import estado
from .instagram import (already_published_caption, caption_hash, create_reel,
                        find_published_caption, publish, verify_destination, wait_ready)


def persist_queue(queue: str, message: str) -> None:
    subprocess.run(['git', 'add', '--', queue], check=True)
    subprocess.run(['git', '-c', 'user.name=github-actions[bot]', '-c',
                    'user.email=41898282+github-actions[bot]@users.noreply.github.com',
                    'commit', '-m', message, '--', queue], check=True)
    subprocess.run(['git', 'push', 'origin', 'HEAD:refs/heads/main'], check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--video-url')
    source.add_argument('--video-file', type=Path)
    parser.add_argument('--validate-upload', action='store_true')
    parser.add_argument('--caption-file', required=True)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--queue', help='fila do motor editorial (JSON) a atualizar')
    parser.add_argument('--dedupe-key', help='item da fila a publicar; sem isso, o melhor pronto')
    parser.add_argument('--persist-queue', action='store_true')
    args = parser.parse_args()
    if args.validate_upload and (args.publish or not args.video_file):
        parser.error('--validate-upload exige --video-file e não aceita --publish')
    if args.persist_queue and (not args.queue or os.environ.get('GITHUB_REF') != 'refs/heads/main'):
        parser.error('--persist-queue exige fila e branch main')

    caption = open(args.caption_file, encoding='utf-8').read().strip()
    if estado.arroba() not in caption.casefold():
        raise SystemExit(f'marca {estado.arroba()} ausente: publicação bloqueada')
    print('caption_hash=', caption_hash(caption))

    key = args.dedupe_key
    if args.queue and not key:
        candidate = state.next_ready(args.queue)
        if candidate is None:
            raise SystemExit('fila sem item pronto e dentro da validade: nada a publicar')
        key = candidate['dedupe_key']
        print('item_escolhido=', key, candidate.get('format'), candidate.get('topic'))

    destination = verify_destination()
    print('destino_verificado=', destination.get('username'))

    if args.validate_upload:
        container = create_reel(None, caption, video_file=args.video_file)
        wait_ready(container)
        print('Upload processado pela Meta. Nenhuma publicação foi realizada.')
        return

    if not args.publish:
        print('DRY-RUN: nenhum container foi criado; fila intacta')
        return

    if already_published_caption(caption):
        raise SystemExit('DUPLICATA BLOQUEADA: legenda equivalente já publicada')

    if args.queue:
        candidate = state.find(state.load(args.queue), key)
        if candidate is None:
            raise SystemExit('Pauta ausente na fila')
        turno = turno_do_formato(candidate.get('format'))
        today = now().date().isoformat()
        for item in state.load(args.queue):
            timestamp = item.get('published_at') or item.get('claimed_at') or ''
            if (item.get('dedupe_key') != key and timestamp[:10] == today and turno_do_formato(item.get('format')) == turno
                    and item.get('status') in {'published', 'publishing', 'unknown'}):
                raise SystemExit('Turno já publicado ou aguardando confirmação')
        state.claim(args.queue, key)
        print('item_reivindicado=', key)

    # Antes de media_publish nada foi ao ar: falha aqui devolve o item para a fila.
    try:
        if args.video_file:
            container = create_reel(None, caption, video_file=args.video_file)
        else:
            container = create_reel(args.video_url, caption)
        wait_ready(container)
        if args.queue and state.stamp(candidate['expires_at']) <= now():
            raise RuntimeError('Validade da previsão encerrada durante o processamento')
        if os.environ.get('CHECK_PUBLICATION_DEADLINE') == 'true':
            from scripts.aguardar_horario import dentro_do_prazo
            if not dentro_do_prazo(os.environ['PRAZO']):
                raise RuntimeError('Prazo do turno encerrado durante o processamento')
    except BaseException as exc:
        if args.queue:
            state.release(args.queue, key, f'falha antes de publicar: {type(exc).__name__}')
        raise

    if args.persist_queue:
        persist_queue(args.queue, 'Reservar turno antes de publicar na Meta')

    # Daqui em diante a midia pode existir: falha vira 'unknown', nunca 'ready'.
    try:
        media_id = publish(container)
    except BaseException as exc:
        if args.queue:
            state.mark_unknown(args.queue, key,
                               f'falha durante media_publish: {type(exc).__name__}')
        recovered = None
        if isinstance(exc, Exception):
            for delay in (0, 5, 15):
                time.sleep(delay)
                try:
                    recovered = find_published_caption(caption)
                except Exception:
                    continue
                if recovered and recovered.get('id'):
                    break
        if not recovered or not recovered.get('id'):
            raise
        media_id = recovered['id']

    print('media_id=', media_id)
    if args.queue:
        state.commit(args.queue, key, media_id)
        if args.persist_queue:
            persist_queue(args.queue, 'Confirmar ID de mídia publicado na Meta')
        print('fila_atualizada=', key, '-> published')
    try:
        result = find_published_caption(caption)
    except Exception:
        result = None
    if result and str(result.get('id')) == str(media_id) and result.get('permalink'):
        print('permalink=', result['permalink'])



if __name__ == '__main__':
    main()
