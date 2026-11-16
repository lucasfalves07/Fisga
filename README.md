# Fisga

[![testes](https://github.com/lucasfalves07/Fisga/actions/workflows/testes.yml/badge.svg)](https://github.com/lucasfalves07/Fisga/actions/workflows/testes.yml)

Detector de phishing para URLs e e-mails, focado em golpes comuns no Brasil: Pix, boleto falso, "taxa pendente" dos Correios, falsas centrais de banco e gov.br.

**Online:** https://fisga.onrender.com

A análise junta quatro sinais:

- **Regras de URL**: typosquatting de marcas brasileiras, TLD, IP no lugar de domínio, encurtadores, punycode
- **Modelo de ML**: Random Forest treinado com 8 mil URLs reais, olhando só o domínio
- **Cabeçalhos**: SPF, DKIM, DMARC e divergência entre From, Reply-To e Return-Path
- **Texto**: LLM (Llama via Groq) classifica o tipo de golpe; sem chave configurada, cai numa heurística local

O resultado vem com score de 0 a 1, veredito e os motivos em português.

## Rodando

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
  gerar_notebook.py
models/
notebooks/
tests/
```

## Próximos passos

Ver [ROADMAP.md](ROADMAP.md).
