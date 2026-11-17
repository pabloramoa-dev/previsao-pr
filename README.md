# Previsão PR — @previsaopr

Reels automáticos de previsão do tempo no Paraná: **Bira do Tempo** às
06:00 com a previsão de hoje e **Bia da Orla** às 18:00 com a de
amanhã (hora local, UTC-3; 06:00 e 18:00 em Brasília).

Gerado de `pabloramoa-dev/previsao-modelo` por `scripts/novo_estado.py`. Motor, personagens,
vozes e testes são os do modelo; o que é deste canal está em `config/estado.yaml` e
`config/locais.yaml`. Correção no motor se faz no modelo e se propaga.

Dados: [MET Norway](https://api.met.no) (licença CC BY 4.0, crédito em toda legenda).

## Quadro das seis regiões

| Região | Âncora (todo Reel) | Reservas |
| --- | --- | --- |
| Curitiba | Curitiba | São José dos Pinhais, Colombo |
| Litoral | Paranaguá | Matinhos, Guaratuba |
| Campos Gerais | Ponta Grossa | Castro, Telêmaco Borba |
| Norte | Londrina | Apucarana, Cornélio Procópio |
| Noroeste | Maringá | Umuarama, Paranavaí |
| Oeste | Cascavel | Foz do Iguaçu, Toledo |

## Colocar no ar

1. Settings → Actions → General → Workflow permissions: **Read and write**.
2. Settings → Secrets and variables → Actions → **Variables**:
   `AUTOMATION_ENABLED=false`, `EXPECTED_IG_USERNAME=previsaopr`.
3. Rodar **CI**, **Coletar dados (sem publicação)** e **Validar estúdio HyperFrames**;
   assistir aos dois MP4 (nomes, preposições, cenário, sigla).
4. Conta @previsaopr profissional + app da Meta ("API do Instagram com login do
   Instagram", escopos `instagram_business_basic`, `instagram_business_content_publish`,
   `instagram_business_manage_insights`).
5. **Secrets**: `IG_USER_ID`, `IG_ACCESS_TOKEN`, `GH_PAT_SECRETS` (fine-grained, só este
   repo, Secrets: write).
6. **Health — conexão com a Meta** → `verified` com @previsaopr.
7. **Reel manual** sem publicar → revisar → com publicar → conferir no perfil.
8. **Token — renovar IG** uma vez à mão; depois roda sozinho nos dias 1 e 15.
9. `AUTOMATION_ENABLED=true`.
10. cron-job.org, fuso `America/Sao_Paulo`, POST
    `https://api.github.com/repos/pabloramoa-dev/previsao-pr/dispatches`:
    `{"event_type":"reel_manha"}` às 05:35 e `{"event_type":"reel_noite"}` às 17:35.
