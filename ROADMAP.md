# Roadmap

## Base
- [x] API com `/analyze/url` e `/analyze/email`
- [x] Features de URL e typosquatting de marcas BR
- [x] SPF / DKIM / DMARC
- [x] Classificação de texto com LLM e fallback heurístico
- [x] Testes de golpes de entrega (Correios, Loggi, Jadlog, Shopee, taxação)

## Dataset
- [x] URLs maliciosas (OpenPhish, Phishing.Database, PhishTank) com alvo BR
- [x] URLs legítimas (Tranco, domínios .br)
- [ ] 200 a 500 mensagens de golpe em PT-BR
- [ ] Coletar por algumas semanas e testar em golpes mais novos que os do treino

## Modelo
- [x] Random Forest com características do domínio
- [x] Comparação entre regras, ML e combinado (precisão, recall, F1, AUC)
- [x] Score do app combina regras e modelo
- [x] Notebook de avaliação
- [ ] Avaliar a parte de texto (heurística × LLM) com o dataset de mensagens

## Produto
- [x] Site com resultado detalhado, quiz e histórico
- [x] Deploy no Render
- [x] Testes no GitHub Actions
- [ ] Dockerfile
- [ ] Extensão Chrome
- [ ] Vídeo de demo

## Depois
- [ ] Idade do domínio (WHOIS) e certificado SSL
- [ ] Comparação visual com sites oficiais
- [ ] Leitura de QR Code Pix
