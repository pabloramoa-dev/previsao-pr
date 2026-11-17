# Rede de canais estaduais

- `estados.yaml` — os 24 estados: nome, artigo, título, grupo de horário, cenário e as
  seis regiões do quadro (âncora + reservas). É o único arquivo a editar para mudar
  cidades ou regiões de um estado.
- `municipios.csv`, `ufs.csv` — cadastro de municípios do IBGE com coordenadas e fuso,
  de [kelvins/municipios-brasileiros](https://github.com/kelvins/municipios-brasileiros)
  (licença MIT, Copyright (c) 2016 Kelvin S. do Prado).

Gerar um estado: `python -m scripts.novo_estado PR --destino ../previsao-pr`.
