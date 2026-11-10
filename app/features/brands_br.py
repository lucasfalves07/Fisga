BRANDS = {
    "nubank": ["nubank.com.br", "nu.com.br"],
    "itau": ["itau.com.br"],
    "bradesco": ["bradesco.com.br"],
    "santander": ["santander.com.br"],
    "caixa": ["caixa.gov.br"],
    "bancodobrasil": ["bb.com.br"],
    "bb": ["bb.com.br"],
    "bancointer": ["bancointer.com.br", "inter.co"],
    "picpay": ["picpay.com"],
    "mercadopago": ["mercadopago.com.br"],
    "mercadolivre": ["mercadolivre.com.br"],
    "correios": ["correios.com.br"],
    "govbr": ["gov.br"],
    "receita": ["gov.br"],
    "serasa": ["serasa.com.br"],
    "detran": ["gov.br"],
    "magalu": ["magazineluiza.com.br", "magalu.com"],
    "americanas": ["americanas.com.br"],
    "shopee": ["shopee.com.br"],
    "ifood": ["ifood.com.br"],
}

RISKY_TLDS = {
    "xyz", "top", "click", "online", "site", "live", "shop", "info",
    "icu", "buzz", "cfd", "sbs", "rest", "store", "fun", "monster",
}

SENSITIVE_WORDS = [
    "login", "senha", "acesso", "verificar", "atualizar", "seguranca",
    "bloqueio", "desbloqueio", "pix", "boleto", "taxa", "rastreio",
    "pagamento", "cadastro", "token", "conta",
]

SHORTENERS = {"bit.ly", "tinyurl.com", "cutt.ly", "encurtador.com.br", "t.co", "is.gd", "rb.gy"}
