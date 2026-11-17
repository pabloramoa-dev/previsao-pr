# previsao-modelo

Modelo dos canais de previsão do tempo por estado. É o motor do @previsaorj
(Bira às 6h com a previsão de hoje, Bia às 18h com a de amanhã, vozes Kokoro,
estúdio HyperFrames, publicação automática no Instagram), com tudo que é próprio
de um canal tirado do código e posto em dois arquivos:

- `config/estado.yaml` — nome, @, fuso, títulos, hashtags, cenário e as seis
  regiões do quadro;
- `config/locais.yaml` — municípios e pontos de coleta.

Este repositório não publica nada: serve de origem para os repositórios dos estados.
A configuração dele é a do estado de referência, e os testes rodam sobre ela.

## Gerar um estado

```bash
pip install -r requirements/test.txt
python -m scripts.novo_estado PR --destino ../previsao-pr
cd ../previsao-pr && python -m pytest -q
```

As regiões e cidades de cada estado ficam em `scripts/rede/estados.yaml`; as
coordenadas e o fuso vêm do cadastro do IBGE. O repositório gerado traz um README
com o passo a passo para colocar o canal no ar.

## Fonte de dados

[MET Norway](https://api.met.no), gratuita e liberada para uso comercial
(CC BY 4.0). Toda legenda credita a fonte e a licença, e as requisições se
identificam com o @ e o repositório do canal. A MET Norway não fornece
probabilidade de chuva nem rajada para o Brasil, então o Reel fala de
milímetros previstos, horário da chuva e vento médio. O Open-Meteo continua no
código, desligado em `config/fontes.yaml`.

## Verificações

| Comando | O que confere |
| --- | --- |
| `python -m pytest -q` | motor, roteiro, legenda, horários e o gerador dos 24 estados |
| `python -m scripts.validar_estado` | coerência de `estado.yaml`, `locais.yaml` e workflows |
| `python scripts/isolation_guard.py` | nenhum identificador de outro canal no código |
| `python -m scripts.sincronizar_marca --check` | card "Seguir", avatar e `brand.yml` com a marca do canal |
