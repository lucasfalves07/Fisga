# Roadmap

## Base
- [x] API com `/analyze/url` e `/analyze/email`
- [x] Features de URL e typosquatting de marcas BR
- [x] SPF / DKIM / DMARC
- [x] Classificação de texto com LLM e fallback heurístico
- [x] Score por regras

## Dataset
- [ ] URLs maliciosas (OpenPhish, Phishing.Database, PhishTank) com alvo BR
- [ ] URLs legítimas (Tranco, domínios .br)
- [ ] 200 a 500 mensagens de golpe em PT-BR
- [ ] Documentar em `data/README.md`

## Modelo
- [ ] Random Forest / XGBoost para URL
- [ ] Comparar regras, ML, LLM e combinado (precisão, recall, F1)
- [ ] Trocar os pesos fixos do `scoring.py` pelo modelo
- [ ] Notebook de avaliação

## Produto
- [ ] Extensão Chrome
- [ ] Dashboard em Streamlit
- [ ] Docker e docker-compose
- [ ] Deploy (Render ou Railway)
- [ ] Vídeo de demo

## Depois
- [ ] Idade do domínio (WHOIS) e certificado SSL
- [ ] Comparação visual com sites oficiais
- [ ] Leitura de QR Code Pix
