# Fisga

[![testes](https://github.com/lucasfalves07/Fisga/actions/workflows/testes.yml/badge.svg)](https://github.com/lucasfalves07/Fisga/actions/workflows/testes.yml)

Detector de phishing para URLs e e-mails, focado em golpes comuns no Brasil: Pix, boleto falso, "taxa pendente" dos Correios, falsas centrais de banco e gov.br.

**Online:** https://fisga.onrender.com

A análise junta quatro sinais:

- **Regras de URL**: typosquatting de marcas brasileiras, TLD, IP no lugar de domínio, encurtadores, punycode
- **Modelo de ML**: Random Forest treinado com 8 mil URLs reais, olhando só o domínio
- **Cabeçalhos**: SPF, DKIM, DMARC e divergência entre From, Reply-To e Return-Path
- **Texto**: LLM (gpt-oss-120b via Groq) classifica o tipo de golpe; sem chave configurada, cai numa heurística local

O resultado vem com score de 0 a 1, veredito e os motivos em português.

No site também dá para mandar o **print** da conversa (botão, Ctrl+V ou arrastar). O texto é lido no próprio navegador com Tesseract.js, sem enviar a imagem para servidor nenhum, e a pessoa confere o texto antes de verificar.

## Rodando

Com Docker:

```bash
docker build -t fisga .
docker run -p 8000:8000 --env-file .env fisga
```

Ou direto com Python:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Site em `http://localhost:8000` e Swagger em `http://localhost:8000/docs`.

```bash
curl -X POST localhost:8000/analyze/url \
  -H "Content-Type: application/json" \
  -d '{"url": "http://nubank-seguranca.xyz/login"}'
```

```json
{
  "url": "http://nubank-seguranca.xyz/login",
  "dominio": "nubank-seguranca.xyz",
  "score": 0.91,
  "veredito": "provável golpe",
  "motivos": [
    "Domínio imita a marca 'nubank' mas não é o domínio oficial",
    "TLD de alto risco (.xyz)",
    "Sem HTTPS",
    "URL contém palavra sensível: 'login'",
    "URL contém palavra sensível: 'seguranca'",
    "Modelo treinado com URLs reais estima 96% de chance de golpe pelo domínio"
  ],
  "componentes": { "regras": 0.8, "modelo": 0.96 }
}
```

Para e-mail, envie o conteúdo bruto (`.eml`) em `/analyze/email` no campo `raw`.

## Dataset

```bash
python -m scripts.coletar_urls --balancear
```

Baixa URLs de OpenPhish e Phishing.Database (e PhishTank, se `PHISHTANK_KEY` estiver no `.env`), mantém só as com alvo brasileiro e junta com domínios legítimos da lista Tranco. Sai em `data/processed/urls.csv`. Rodando de novo, as URLs antigas são mantidas e o dataset cresce.

## Modelo

```bash
python -m scripts.treinar_modelo
```

Treina o Random Forest e salva em `models/url_model.joblib`, com as métricas em `models/metricas.json`. A análise completa, com gráficos, está em [notebooks/avaliacao.ipynb](notebooks/avaliacao.ipynb).

Resultado em 1.947 URLs de 1.583 domínios que o modelo nunca viu no treino (risco ≥ 40% conta como golpe):

| Abordagem | Precisão | Recall | F1 | AUC |
|---|---|---|---|---|
| Só regras | 0,96 | 0,17 | 0,28 | 0,83 |
| Random Forest | 0,75 | 0,77 | 0,76 | 0,85 |
| Regressão logística | 0,74 | 0,77 | 0,76 | 0,85 |
| Regras + Random Forest (app) | 0,85 | 0,65 | 0,74 | 0,86 |

Decisões que valem destacar:

- **Vazamento no dataset.** As URLs legítimas da Tranco são só domínios, sempre com `https` e sem caminho. Um modelo com a URL inteira aprenderia "tem caminho, então é golpe". Por isso o modelo usa só características do domínio e ignora `www.`.
- **Separação por domínio.** Treino e teste são divididos com `GroupShuffleSplit` pelo domínio registrado, para o mesmo site não aparecer nos dois lados.
- **Peso das regras.** O app usa `0,3 × regras + 0,7 × modelo`. Perde recall, mas reduz alarme falso em site verdadeiro de 25% para 15% dos alertas.
- **Domínios oficiais** das marcas monitoradas pulam o modelo.

Para rodar o notebook: `pip install -r requirements-dev.txt`.

## Mensagens

`data/mensagens.csv` tem 198 mensagens em PT-BR (100 golpes e 98 legítimas) nos formatos de SMS, WhatsApp e e-mail. Os golpes cobrem entrega, falsa central de banco, parente com número novo, falso emprego, prêmio, gov.br, boleto, investimento e roubo de código do WhatsApp. As legítimas incluem casos difíceis, como códigos de verificação reais, Pix recebido, fatura disponível e "mãe, mudei de número" sem pedido de dinheiro. As mensagens foram escritas a partir de golpes documentados, sem dados de pessoas reais.

```bash
python -m scripts.avaliar_texto
```

Compara a heurística com o LLM, sozinhos e dentro do Fisga completo (texto + links da mensagem). Sem `GROQ_API_KEY`, avalia só a heurística. As respostas do LLM ficam em cache, e o script respeita o limite de requisições da Groq.

| Abordagem | Precisão | Recall | F1 | AUC |
|---|---|---|---|---|
| Heurística (só texto) | 1,00 | 0,15 | 0,26 | 0,70 |
| Fisga com heurística | 1,00 | 0,54 | 0,70 | 0,86 |
| LLM (só texto) | 0,92 | 1,00 | 0,96 | 0,98 |
| Fisga com LLM | 0,92 | 1,00 | 0,96 | 0,99 |

A heurística nunca erra quando dispara, mas não pega golpe sem palavra-chave: parente pedindo dinheiro, falso emprego e investimento ficam com recall zero. O LLM (`openai/gpt-oss-120b` via Groq) pegou os 100 golpes, inclusive esses.

O custo são 9 alarmes falsos em 98 mensagens legítimas, todos do mesmo tipo: notificações verdadeiras que falam de código, Pix, boleto ou encomenda sem pedir nada, como "Seu código de verificação do Google é..." ou "Correios: seu objeto foi entregue". O modelo fica desconfiado demais com o assunto, mesmo quando a mensagem não pede ação nenhuma.

Cuidados ao ler esses números:

- São 198 mensagens escritas a partir de golpes conhecidos. Golpes reais costumam ser menos óbvios, então o recall de 100% é otimista.
- Ajustar o prompt para reduzir os alarmes falsos usando estas mesmas mensagens seria treinar no teste. O certo é separar um conjunto novo antes de mexer no prompt.

## Testes

```bash
pytest
```

Rodam a cada push pelo GitHub Actions.

## Estrutura

```
app/
  main.py
  scoring.py
  model.py
  features/
    brands_br.py
    url_features.py
    header_checks.py
  llm/
    analyzer.py
web/
  index.html
scripts/
  coletar_urls.py
  treinar_modelo.py
  avaliar_texto.py
  gerar_notebook.py
models/
notebooks/
tests/
Dockerfile
```

## Próximos passos

Ver [ROADMAP.md](ROADMAP.md).
