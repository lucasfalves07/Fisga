# Fisga

Detector de phishing para URLs e e-mails, focado em golpes comuns no Brasil: Pix, boleto falso, "taxa pendente" dos Correios, falsas centrais de banco e gov.br.

A análise junta três sinais:

- **URL**: typosquatting de marcas brasileiras, TLD, IP no lugar de domínio, encurtadores, punycode
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

Swagger em `http://localhost:8000/docs`.

```bash
curl -X POST localhost:8000/analyze/url \
  -H "Content-Type: application/json" \
  -d '{"url": "http://nubank-seguranca.xyz/login"}'
```

```json
{
  "url": "http://nubank-seguranca.xyz/login",
  "dominio": "nubank-seguranca.xyz",
  "score": 0.8,
  "veredito": "provável golpe",
  "motivos": [
    "Domínio imita a marca 'nubank' mas não é o domínio oficial",
    "TLD de alto risco (.xyz)",
    "Sem HTTPS",
    "URL contém palavra sensível: 'login'"
  ]
}
```

Para e-mail, envie o conteúdo bruto (`.eml`) em `/analyze/email` no campo `raw`.

## Testes

```bash
pytest
```

## Estrutura

```
app/
  main.py
  scoring.py
  features/
    brands_br.py
    url_features.py
    header_checks.py
  llm/
    analyzer.py
data/
tests/
```

## Próximos passos

Ver [ROADMAP.md](ROADMAP.md).
