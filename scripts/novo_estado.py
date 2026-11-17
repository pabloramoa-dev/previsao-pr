"""Gera o repositório do canal de um estado a partir deste modelo.

    python -m scripts.novo_estado PR                 # cria ../previsao-pr
    python -m scripts.novo_estado PR --destino /tmp/pr
    python -m scripts.novo_estado --todos --destino ../rede

Tudo que muda de um estado para outro sai de scripts/rede/estados.yaml e do
cadastro de municípios do IBGE (scripts/rede/municipios.csv). O motor, os
personagens, as vozes e os testes são copiados sem alteração. O resultado:

  config/estado.yaml     identidade, fuso, recorte, títulos, seis regiões
  config/locais.yaml     municípios, zonas e pontos (âncoras e reservas)
  config/isolamento.yaml os outros canais da rede, proibidos neste
  .github/workflows      alvo, fuso e crons de reserva do canal
  README.md              o passo a passo de colocar o canal no ar
  card, avatar e brand   regravados com a marca do canal

O destino precisa estar vazio (ou não existir). Nada aqui toca a rede.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
REDE = RAIZ / 'scripts' / 'rede'
DONO = 'pabloramoa-dev'

# O que NÃO vai para o repositório do estado.
IGNORAR = {'.git', 'node_modules', '__pycache__', '.pytest_cache', 'output', 'build',
           'renders', 'snapshots'}
IGNORAR_CAMINHOS = {Path('scripts/rede'), Path('scripts/novo_estado.py'),
                    Path('tests/test_novo_estado.py'), Path('README.md')}

# Canais que já existem fora da rede gerada aqui.
CANAIS_EXISTENTES = ['previsaorj', 'previsao-rj', 'otemposp', 'previsaobsb', 'previsao-bsb',
                     '@previsaosulflu', 'previsaovr', 'previsao-sul-fluminense',
                     '27148485038175', 'reels/previsao_lib']

FUSOS = {  # zona IANA do canal; o desvio sai do cadastro (fuso_horario)
    'AM': 'America/Manaus', 'RR': 'America/Boa_Vista', 'RO': 'America/Porto_Velho',
    'MT': 'America/Cuiaba', 'MS': 'America/Campo_Grande', 'AC': 'America/Rio_Branco',
    'PA': 'America/Belem', 'AP': 'America/Belem', 'TO': 'America/Araguaina',
    'MA': 'America/Fortaleza', 'PI': 'America/Fortaleza', 'CE': 'America/Fortaleza',
    'RN': 'America/Fortaleza', 'PB': 'America/Fortaleza', 'PE': 'America/Recife',
    'AL': 'America/Maceio', 'SE': 'America/Maceio', 'BA': 'America/Bahia',
}
DESVIO = {'America/Sao_Paulo': -3, 'America/Porto_Velho': -4, 'America/Rio_Branco': -5,
          'America/Manaus': -4, 'America/Boa_Vista': -4, 'America/Cuiaba': -4,
          'America/Campo_Grande': -4}
_EM = {'o': 'no', 'a': 'na', 'os': 'nos', 'as': 'nas', '': 'em'}
_DE = {'o': 'do', 'a': 'da', 'os': 'dos', 'as': 'das', '': 'de'}


# ------------------------------------------------------------ utilidades ---
def slug(texto: str) -> str:
    base = unicodedata.normalize('NFD', texto.casefold())
    base = ''.join(c for c in base if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]+', '_', base).strip('_')


def sem_acento(texto: str) -> str:
    return slug(texto).replace('_', ' ')


def carregar_rede() -> dict:
    return yaml.safe_load((REDE / 'estados.yaml').read_text(encoding='utf-8'))


def municipios(uf: str) -> dict[str, dict]:
    with (REDE / 'ufs.csv').open(encoding='utf-8-sig') as f:
        codigo = next(r['codigo_uf'] for r in csv.DictReader(f) if r['uf'] == uf)
    with (REDE / 'municipios.csv').open(encoding='utf-8') as f:
        return {r['nome']: r for r in csv.DictReader(f) if r['codigo_uf'] == codigo}


def handle_de(uf: str, e: dict) -> str:
    return e.get('handle') or f'previsao{uf.casefold()}'


def repo_de(uf: str, e: dict) -> str:
    return e.get('repo') or f'previsao-{uf.casefold()}'


def horario(rede: dict, e: dict) -> int:
    return int(rede['grupos'][e['grupo']])


# ------------------------------------------------------------- arquivos ---
def montar_estado(uf: str, e: dict, rede: dict, cad: dict[str, dict]) -> dict:
    todos = [cad[n] for n in cad]
    lats = [float(m['latitude']) for m in todos]
    lons = [float(m['longitude']) for m in todos]
    zona = FUSOS.get(uf, 'America/Sao_Paulo')
    desvios = {DESVIO.get(cad[r['ancora']]['fuso_horario'], -3) for r in e['regioes']}
    if len(desvios) != 1:
        raise SystemExit(f'{uf}: âncoras em fusos diferentes {desvios}; separe o canal')
    fuso = desvios.pop()
    em = f"{_EM[e['artigo']]} {e['curto']}"
    de = f"{_DE[e['artigo']]} {e['curto']}"
    handle, repo = handle_de(uf, e), repo_de(uf, e)
    sem = sem_acento(e['nome']).title().replace(' ', '')
    tag = f'#Previsao{uf}'
    titulo = e.get('titulo') or e['curto'].upper()
    preps = {k: list(e.get(k) or []) for k in ('na', 'no', 'nas', 'nos')}
    preps['no'] = sorted(set(preps['no']) | {e['curto'], e['nome']}) if e['artigo'] == 'o' else preps['no']
    preps['na'] = sorted(set(preps['na']) | {e['curto'], e['nome']}) if e['artigo'] == 'a' else preps['na']
    regioes = []
    for r in e['regioes']:
        ids = [slug(r['ancora'])] + [slug(n) for n in r['reservas']]
        regioes.append({'rotulo': r['rotulo'], 'ids': ids, 'zonas': [f"z_{slug(r['rotulo'])}"]})
    return {
        'versao': 1,
        'uf': uf,
        'nome': e['nome'],
        'curto': e['curto'],
        'artigo': e['artigo'],
        'regiao_id': f'estado_{uf.casefold()}',
        'marca': f'PREVISÃO {uf}',
        'marca_falada': f'Previsão {uf}',
        'handle': handle,
        'slogan': f"O tempo {de} para decidir seu dia.",
        'repo': f'{DONO}/{repo}',
        'fuso_utc': fuso,
        'timezone': zona,
        'recorte': {'lat_min': round(min(lats) - 0.3, 2), 'lat_max': round(max(lats) + 0.3, 2),
                    'lon_min': round(min(lons) - 0.3, 2), 'lon_max': round(max(lons) + 0.3, 2)},
        'litoral': bool(e['litoral']),
        'cenario': e['cenario'],
        'ticker': uf if len(e['curto']) > 8 else e['curto'].upper(),
        'titulos': {'antes_de_sair': f'{titulo} ANTES DE SAIR',
                    'amanha_no_estado': f'AMANHÃ {em.upper()}'},
        'apresentadores': {'bira': {'cargo': f'TEMPO {em.upper()}' if len(em) <= 16 else f'TEMPO EM {uf}'},
                           'bia': {'cargo': f'O TEMPO DE AMANHÃ {em.upper()}' if len(em) <= 12
                                   else f'O TEMPO DE AMANHÃ · {uf}'}},
        'hashtags': {
            'padrao': f'{tag} #{sem} #Tempo{uf}',
            'antes_de_sair': f'{tag} #{sem} #Tempo{uf}',
            'chove_onde': f'{tag} #Chuva{uf} #Tempo{uf}',
            'fim_de_semana': f'{tag} #FimDeSemana #{sem}',
            'vai_dar_praia': f'{tag} #Praia #{sem}',
            'vai_ao_jogo': f'{tag} #{sem} #Tempo{uf}',
            'amanha_no_estado': f'{tag} #TempoAmanha #{sem}',
        },
        'legenda': {'abrangencia': em, 'unidade': 'cidade'},
        'formatos_desligados': ['vai_ao_jogo'],
        'regioes': regioes,
        'falado': {},
        'preposicoes': preps,
        'destaques_semana': [],
    }


def montar_locais(uf: str, e: dict, cad: dict[str, dict], est: dict) -> dict:
    municipalities, zones, locations, vistos = {}, {}, [], set()
    nomes = {}
    for r in e['regioes']:
        zid = f"z_{slug(r['rotulo'])}"
        zones[zid] = {'name': r['rotulo'], 'municipality': None,
                      'coastal': bool(e['litoral'] and r['rotulo'].lower().startswith(('litoral',))),
                      'decisions': ['calor', 'chuva', 'deslocamento']}
        for tier, nome in [(1, r['ancora'])] + [(2, n) for n in r['reservas']]:
            m = cad[nome]
            mid = slug(nome)
            if mid in vistos:
                raise SystemExit(f'{uf}: {nome} aparece em duas regiões')
            vistos.add(mid)
            municipalities[mid] = {'name': nome, 'uf': uf}
            nomes.setdefault(sem_acento(nome), []).append(mid)
            locations.append({
                'id': mid, 'name': nome, 'zone': zid, 'municipality': mid, 'type': 'city',
                'latitude': round(float(m['latitude']), 4), 'longitude': round(float(m['longitude']), 4),
                'aliases': sorted({nome.casefold(), sem_acento(nome)}),
                'sample_tier': tier, 'spatial_fit': 'alto' if tier == 1 else 'medio',
                'ibge': int(m['codigo_ibge']),
            })
    # Nomes que também são de cidades conhecidas de outros estados.
    ambiguos = {a: ids for a, ids in nomes.items() if a in {
        'caxias', 'campo grande', 'santana', 'bonito', 'serra', 'vitoria', 'juazeiro',
        'sao jose', 'santa cruz', 'alegre', 'castro', 'jardim', 'bonfim', 'altos'}}
    return {
        'meta': {'version': 1, 'region': est['regiao_id'], 'timezone': est['timezone'],
                 'updated_at': None,
                 'source_note': ('Sedes municipais do cadastro do IBGE '
                                 '(github.com/kelvins/municipios-brasileiros, MIT). '
                                 'Previsao por ponto; nunca afirmar diferenca dentro do municipio.')},
        'municipalities': municipalities,
        'zones': zones,
        'locations': locations,
        'points_of_interest': {},
        'ambiguous': ambiguos,
    }


def isolamento(uf: str, rede: dict) -> dict:
    outros = []
    for outra, e in rede['estados'].items():
        if outra != uf:
            outros += [handle_de(outra, e), repo_de(outra, e)]
    return {'proibidos': sorted(set(CANAIS_EXISTENTES + outros))}


def ajustar_workflows(destino: Path, fuso: int, minuto: int) -> None:
    for turno, hora in (('manha', 6), ('noite', 18)):
        caminho = destino / '.github' / 'workflows' / f'reel_{turno}.yml'
        texto = caminho.read_text(encoding='utf-8')
        alvo_utc = (hora - fuso) * 60 + minuto
        r1, r2 = alvo_utc + 25, alvo_utc + 85
        trocas = [
            (r'    - cron: "\d+ \d+ \* \* \*"   # gerado: reserva 1 \(ALVO\+25 em UTC\)',
             f'    - cron: "{r1 % 60} {(r1 // 60) % 24} * * *"   # gerado: reserva 1 (ALVO+25 em UTC)'),
            (r'    - cron: "\d+ \d+ \* \* \*"   # gerado: reserva 2 \(ALVO\+85 em UTC\)',
             f'    - cron: "{r2 % 60} {(r2 // 60) % 24} * * *"   # gerado: reserva 2 (ALVO+85 em UTC)'),
            (r'  ALVO: "\d\d:\d\d"        # gerado: alvo do turno',
             f'  ALVO: "{hora:02d}:{minuto:02d}"        # gerado: alvo do turno'),
            (r'  FUSO_UTC: "-?\d+"       # gerado: igual a fuso_utc de config/estado.yaml',
             f'  FUSO_UTC: "{fuso}"       # gerado: igual a fuso_utc de config/estado.yaml'),
        ]
        for padrao, novo in trocas:
            texto, n = re.subn(padrao, novo, texto)
            if n != 1:
                raise SystemExit(f'{caminho.name}: linha gerada não encontrada ({padrao})')
        caminho.write_text(texto, encoding='utf-8')


def readme(uf: str, e: dict, est: dict, minuto: int) -> str:
    linhas = '\n'.join(f"| {r['rotulo']} | {r['ancora']} | {', '.join(r['reservas']) or '—'} |"
                       for r in e['regioes'])
    fuso = est['fuso_utc']
    brasilia = lambda h: f'{(h - 3 - fuso) % 24:02d}:{minuto:02d}'  # noqa: E731
    disparo = lambda h: f'{(h * 60 + minuto - 25) // 60:02d}:{(h * 60 + minuto - 25) % 60:02d}'  # noqa: E731
    return f'''# {est['marca_falada']} — @{est['handle']}

Reels automáticos de previsão do tempo {_EM[e['artigo']]} {e['curto']}: **Bira do Tempo** às
{6:02d}:{minuto:02d} com a previsão de hoje e **Bia da Orla** às {18:02d}:{minuto:02d} com a de
amanhã (hora local, UTC{fuso:+d}; {brasilia(6)} e {brasilia(18)} em Brasília).

Gerado de `{DONO}/previsao-modelo` por `scripts/novo_estado.py`. Motor, personagens,
vozes e testes são os do modelo; o que é deste canal está em `config/estado.yaml` e
`config/locais.yaml`. Correção no motor se faz no modelo e se propaga.

Dados: [MET Norway](https://api.met.no) (licença CC BY 4.0, crédito em toda legenda).

## Quadro das seis regiões

| Região | Âncora (todo Reel) | Reservas |
| --- | --- | --- |
{linhas}

## Colocar no ar

1. Settings → Actions → General → Workflow permissions: **Read and write**.
2. Settings → Secrets and variables → Actions → **Variables**:
   `AUTOMATION_ENABLED=false`, `EXPECTED_IG_USERNAME={est['handle']}`.
3. Rodar **CI**, **Coletar dados (sem publicação)** e **Validar estúdio HyperFrames**;
   assistir aos dois MP4 (nomes, preposições, cenário, sigla).
4. Conta @{est['handle']} profissional + app da Meta ("API do Instagram com login do
   Instagram", escopos `instagram_business_basic`, `instagram_business_content_publish`,
   `instagram_business_manage_insights`).
5. **Secrets**: `IG_USER_ID`, `IG_ACCESS_TOKEN`, `GH_PAT_SECRETS` (fine-grained, só este
   repo, Secrets: write).
6. **Health — conexão com a Meta** → `verified` com @{est['handle']}.
7. **Reel manual** sem publicar → revisar → com publicar → conferir no perfil.
8. **Token — renovar IG** uma vez à mão; depois roda sozinho nos dias 1 e 15.
9. `AUTOMATION_ENABLED=true`.
10. cron-job.org, fuso `{est['timezone']}`, POST
    `https://api.github.com/repos/{est['repo']}/dispatches`:
    `{{"event_type":"reel_manha"}}` às {disparo(6)} e `{{"event_type":"reel_noite"}}` às {disparo(18)}.
'''


# ----------------------------------------------------------------- gerar ---
def copiar_modelo(destino: Path) -> None:
    def ignorar(pasta, nomes):
        rel = Path(pasta).resolve().relative_to(RAIZ)
        return [n for n in nomes if n in IGNORAR or (rel / n) in IGNORAR_CAMINHOS]
    shutil.copytree(RAIZ, destino, ignore=ignorar)


def gerar(uf: str, destino: Path, rede: dict | None = None, sincronizar: bool = True) -> Path:
    rede = rede or carregar_rede()
    uf = uf.upper()
    if uf not in rede['estados']:
        raise SystemExit(f'{uf} não está em scripts/rede/estados.yaml')
    if destino.exists() and any(destino.iterdir()):
        raise SystemExit(f'destino não está vazio: {destino}')
    if destino.exists():
        destino.rmdir()
    e = rede['estados'][uf]
    cad = municipios(uf)
    faltam = [n for r in e['regioes'] for n in [r['ancora'], *r['reservas']] if n not in cad]
    if faltam:
        raise SystemExit(f'{uf}: municípios fora do cadastro do IBGE: {faltam}')

    copiar_modelo(destino)
    est = montar_estado(uf, e, rede, cad)
    minuto = horario(rede, e)
    dump = lambda d: yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=110)  # noqa: E731
    cfg = destino / 'config'
    (cfg / 'estado.yaml').write_text(
        '# Identidade do canal. Gerado por scripts/novo_estado.py no repositorio-modelo.\n'
        '# Pode ser editado a mao; rode `python -m scripts.validar_estado` depois.\n'
        + dump(est), encoding='utf-8')
    (cfg / 'locais.yaml').write_text(
        '# Pontos do canal: sedes municipais (IBGE). sample_tier 1 = ancora de\n'
        '# todo Reel; 2 = reserva da mesma regiao. Gerado por scripts/novo_estado.py.\n'
        + dump(montar_locais(uf, e, cad, est)), encoding='utf-8')
    (cfg / 'isolamento.yaml').write_text(
        '# Outros canais da rede: nao podem aparecer neste repositorio.\n'
        + dump(isolamento(uf, rede)), encoding='utf-8')
    (cfg / 'eventos_manuais.yaml').write_text('events: []\n', encoding='utf-8')
    ajustar_workflows(destino, est['fuso_utc'], minuto)
    dados = destino / 'data'
    (dados / 'editorial_queue.json').write_text('[]\n', encoding='utf-8')
    (dados / 'channel_metrics.json').write_text(
        '{"measurements": [], "status": "empty", "errors": [], "updated_at": null, "account": null}\n',
        encoding='utf-8')
    (dados / 'snapshots').mkdir(exist_ok=True)
    (dados / 'snapshots' / '.gitkeep').write_text('', encoding='utf-8')
    (destino / 'README.md').write_text(readme(uf, e, est, minuto), encoding='utf-8')
    if sincronizar:
        subprocess.run([sys.executable, '-m', 'scripts.sincronizar_marca'], cwd=destino,
                       check=True, capture_output=True)
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('uf', nargs='?')
    parser.add_argument('--todos', action='store_true')
    parser.add_argument('--destino', type=Path)
    args = parser.parse_args()
    rede = carregar_rede()
    if args.todos:
        base = args.destino or RAIZ.parent
        for uf, e in rede['estados'].items():
            print('gerado:', gerar(uf, base / repo_de(uf, e), rede))
        return
    if not args.uf:
        parser.error('informe a UF ou --todos')
    e = rede['estados'].get(args.uf.upper())
    destino = args.destino or RAIZ.parent / repo_de(args.uf.upper(), e or {})
    print('gerado:', gerar(args.uf, destino, rede))


if __name__ == '__main__':
    main()
