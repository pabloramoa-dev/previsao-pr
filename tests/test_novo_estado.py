"""Gerador de canais (só existe no repositório-modelo).

Gera todos os estados da rede e confere, em cada um, o que costuma quebrar:
cidades fora do cadastro do IBGE, fuso errado, crons de reserva fora da janela,
outro canal vazando para dentro, marca dessincronizada.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
novo = pytest.importorskip('scripts.novo_estado')

REDE = novo.carregar_rede()
FUSO_ESPERADO = {'AM': -4, 'RR': -4, 'RO': -4, 'MT': -4, 'MS': -4, 'AC': -5}


@pytest.fixture(scope='module')
def gerados(tmp_path_factory):
    base = tmp_path_factory.mktemp('rede')
    return {uf: novo.gerar(uf, base / novo.repo_de(uf, e), REDE, sincronizar=False)
            for uf, e in REDE['estados'].items()}


def test_rede_tem_os_24_estados_fora_rj_sp_df():
    assert len(REDE['estados']) == 24
    assert not {'RJ', 'SP', 'DF'} & set(REDE['estados'])


@pytest.mark.parametrize('uf', sorted(REDE['estados']))
def test_estado_gerado(gerados, uf):
    destino = gerados[uf]
    est = yaml.safe_load((destino / 'config/estado.yaml').read_text(encoding='utf-8'))
    locais = yaml.safe_load((destino / 'config/locais.yaml').read_text(encoding='utf-8'))
    assert est['uf'] == uf and est['fuso_utc'] == FUSO_ESPERADO.get(uf, -3)
    assert len(est['regioes']) == 6
    ancoras = [l for l in locais['locations'] if l['sample_tier'] == 1]
    assert len(ancoras) == 6
    for loc in locais['locations']:
        r = est['recorte']
        assert r['lat_min'] <= loc['latitude'] <= r['lat_max']
        assert r['lon_min'] <= loc['longitude'] <= r['lon_max']
    proibidos = yaml.safe_load((destino / 'config/isolamento.yaml').read_text())['proibidos']
    assert est['handle'] not in proibidos and 'previsaorj' in proibidos
    assert not (destino / 'scripts/rede').exists() and not (destino / 'scripts/novo_estado.py').exists()
    for turno, hora in (('manha', 6), ('noite', 18)):
        wf = yaml.safe_load((destino / f'.github/workflows/reel_{turno}.yml').read_text())
        assert wf['env']['FUSO_UTC'] == str(est['fuso_utc'])
        h, m = map(int, wf['env']['ALVO'].split(':'))
        assert h == hora and m in REDE['grupos'].values()
        for item in wf[True]['schedule']:
            mi, hu = map(int, item['cron'].split()[:2])
            local = (hu * 60 + mi + est['fuso_utc'] * 60) % 1440
            assert hora * 60 + m < local < int(wf['env']['PRAZO'][:2]) * 60


def test_estado_gerado_passa_na_propria_validacao(gerados):
    destino = gerados['AC']   # o fuso mais distante de Brasília
    for comando in (['-m', 'scripts.sincronizar_marca'], ['-m', 'scripts.validar_estado'],
                    ['scripts/isolation_guard.py'], ['-m', 'scripts.sincronizar_marca', '--check']):
        env = {k: v for k, v in os.environ.items() if k != 'PREVISAO_CONFIG_DIR'}
        r = subprocess.run([sys.executable, *comando], cwd=destino, env=env,
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


def test_destino_ocupado_e_recusado(tmp_path):
    (tmp_path / 'algo').write_text('x')
    with pytest.raises(SystemExit, match='vazio'):
        novo.gerar('PR', tmp_path, REDE)
