# Previsão PR — @previsaopr

Reels automáticos de previsão do tempo no Paraná: **Bira do Tempo** às
06:00 com a previsão de hoje e **Bia** às 18:00 com a de
amanhã (hora local, UTC-3; 06:00 e 18:00 em Brasília).

Gerado de `pabloramoa-dev/previsao-modelo` por `scripts/novo_estado.py`. Motor, personagens,
vozes e testes são os do modelo; o que é deste canal está em `config/estado.yaml` e
`config/locais.yaml`. Correção no motor se faz no modelo e se propaga.

Dados: [MET Norway](https://api.met.no) (licença CC BY 4.0, crédito em toda legenda).

## Quadro das seis regiões

| Região | Município | Alternativas no rodízio |
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
   `AUTOMATION_ENABLED=false`, `EXPECTED_IG_USERNAME=previsaopr`, `META_GRAPH_VERSION=v26.0`.
3. Rodar **CI**, **Coletar dados (sem publicação)** e **Validar estúdio HyperFrames**;
   assistir aos dois MP4 (nomes, preposições, cenário, sigla).
4. Conta @previsaopr profissional e app da Meta com API do Instagram com login
   unificado (escopos `instagram_basic` e `instagram_content_publish`).
5. **Secrets**: `IG_USER_ID` e `IG_ACCESS_TOKEN`.
6. O envio padrão usa os bytes do MP4 diretamente na Meta. Para homologar sem publicar, use **Reel manual** com fonte `live` e marque `validar_upload`. Se preferir hospedar o MP4 via HTTPS, use um bucket S3 dedicado. Configure `REEL_S3_BUCKET`, `REEL_S3_REGION`,
   `REEL_S3_ACCESS_KEY_ID` e `REEL_S3_SECRET_ACCESS_KEY` (as duas últimas em Secrets).
   O bucket deve servir `s3:GetObject` anônimo somente sob `previsaopr/*`,
   sem listagem pública e sem ACL pública. Restrinja o principal do runner a
   enviar e marcar objetos sob esse prefixo. A regra Lifecycle deve expirar
   objetos do prefixo com a tag `publication=confirmed` após sete dias da
   criação. Objetos pendentes ficam sem a tag e exigem conciliação antes da remoção.
7. **Health — conexão com a Meta** → `verified` com @previsaopr.
8. **Reel manual** sem publicar → revisar → com publicar → conferir no perfil.
9. O diagnóstico semanal verifica o token de usuário do sistema do login unificado. O token foi configurado sem expiração. Se for revogado na Meta, reconecte a conta e substitua o Secret.
10. `AUTOMATION_ENABLED=true`.
11. cron-job.org, fuso `America/Sao_Paulo`, POST
    `https://api.github.com/repos/pabloramoa-dev/previsao-pr/dispatches`:
    `{"event_type":"reel_manha"}` às 05:35 e `{"event_type":"reel_noite"}` às 17:35.
   Envie `Content-Type: application/json` e autentique com token fine-grained
   restrito a este repositório e permissão Contents: write. Confira HTTP 204.
   As reservas do Actions estão configuradas para 05:35, 06:25, 07:25, 17:35, 18:25 e 19:25.
   A publicação manual de teste deve ser disparada separadamente, com autorização
   explícita e dados ao vivo.
