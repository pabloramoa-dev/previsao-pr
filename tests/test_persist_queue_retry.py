import subprocess
from types import SimpleNamespace

import pytest

from src.previsao.publish import cli


def _fake(resultados_push, chamadas):
    def run(cmd, check=False, **kw):
        chamadas.append(cmd)
        if cmd[:2] == ['git', 'push']:
            rc = resultados_push.pop(0) if resultados_push else 0
            if check and rc:
                raise subprocess.CalledProcessError(rc, cmd)
            return SimpleNamespace(returncode=rc)
        return SimpleNamespace(returncode=0)
    return run


def test_push_rejeitado_faz_rebase_e_tenta_de_novo(monkeypatch):
    chamadas = []
    monkeypatch.setattr(cli.subprocess, 'run', _fake([1, 0], chamadas))
    monkeypatch.setattr(cli.time, 'sleep', lambda s: None)
    cli.persist_queue('data/editorial_queue.json', 'Reservar turno')
    assert ['git', 'pull', '--rebase', 'origin', 'main'] in chamadas
    assert sum(c[:2] == ['git', 'push'] for c in chamadas) == 2


def test_push_sempre_rejeitado_falha_fechado(monkeypatch):
    monkeypatch.setattr(cli.subprocess, 'run', _fake([1] * 9, []))
    monkeypatch.setattr(cli.time, 'sleep', lambda s: None)
    with pytest.raises(subprocess.CalledProcessError):
        cli.persist_queue('data/editorial_queue.json', 'Reservar turno')
