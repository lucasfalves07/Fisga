# Dataset

## Fontes

| Tipo | Fonte | Observação |
|---|---|---|
| URLs maliciosas | OpenPhish, Phishing.Database, PhishTank | filtrar alvos brasileiros |
| URLs legítimas | Tranco top 1M | filtrar `.br` e marcas da lista |
| Mensagens de golpe | prints/SMS reais anonimizados, relatos públicos | remover nome, CPF, telefone |
| Mensagens legítimas | e-mails próprios, newsletters | |

## Formato

`data/processed/urls.csv`

```
url,label,fonte,data_coleta
http://nubank-seguranca.xyz/login,1,phishtank,2026-11-12
https://www.nubank.com.br,0,tranco,2026-11-12
```

`data/processed/mensagens.csv`

```
texto,label,categoria,fonte
"Sua encomenda está retida...",1,correios,sms
```

`data/raw/` e `data/processed/` não vão pro git.

`data/mensagens.csv`

```
texto,label,categoria
"CORREIOS: Seu objeto ... esta retido ...",1,correios
"Seu codigo de verificacao Nubank e 482913 ...",0,codigo
```

Escritas a partir de golpes documentados, sem dados de pessoas reais. Vai para o git.
