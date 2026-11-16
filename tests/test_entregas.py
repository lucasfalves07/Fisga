import pytest

from app.scoring import score_email, score_url


@pytest.fixture(autouse=True)
def sem_llm(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)


GOLPES_URL = [
    "http://correios-taxa-pendente.top/rastreio",
    "https://correios.encomenda-retida.online/pagamento",
    "http://rastreio-correios.xyz/objeto/BR123456789BR",
    "http://correiosbr-entrega.com/taxa",
    "http://corre1os.com/rastreio",
    "http://correois.com.br.liberacao-objeto.site/pix",
    "https://loggi-entrega.top/reagendar",
    "http://jadlog-rastreio.online/taxa",
    "http://shopee-entrega.shop/confirmar",
    "https://totalexpress-objeto.xyz/pagamento",
    "http://receita-taxacao-importacao.site/pagar",
    "http://remessaconforme-taxa.online/boleto",
]

LEGITIMOS_URL = [
    "https://www.correios.com.br",
    "https://rastreamento.correios.com.br/app/index.php",
    "https://www.loggi.com/rastreador",
    "https://www.jadlog.com.br/jadlog/tracking",
    "https://shopee.com.br/user/purchase",
    "https://www.mercadolivre.com.br/minhas-compras",
    "https://www.totalexpress.com.br",
]

GOLPES_SMS = [
    "CORREIOS: sua encomenda foi retida na fiscalizacao. Pague a taxa de R$ 9,90 via Pix hoje para liberar: http://correios-taxa.top/rastreio",
    "Seu pedido da Shopee nao pode ser entregue. Atualize seus dados em 24 horas: http://shopee-entrega.shop/confirmar",
    "Loggi: tentativa de entrega sem sucesso. Reagende pagando a taxa de R$ 4,99: https://loggi-entrega.top/reagendar",
    "Receita Federal: sua compra internacional foi taxada. Pague o boleto imediatamente para evitar devolucao: http://receita-taxacao-importacao.site/pagar",
    "Sua encomenda esta retida. Clique aqui e pague a taxa via Pix: https://bit.ly/3xYz9Kp",
]

LEGITIMOS_SMS = [
    "Seu pedido saiu para entrega e chega hoje. Acompanhe pelo app.",
    "Correios: seu objeto foi entregue. Obrigado por usar nossos servicos.",
    "Sua compra foi aprovada e sera enviada em ate 2 dias uteis.",
]


def sms(texto: str) -> str:
    return f"Subject: \n\n{texto}"


@pytest.mark.parametrize("url", GOLPES_URL)
def test_url_golpe_de_entrega(url):
    r = score_url(url)
    assert r["score"] >= 0.4, f"{url} -> {r['score']} {r['motivos']}"


@pytest.mark.parametrize("url", LEGITIMOS_URL)
def test_url_oficial_de_entrega(url):
    r = score_url(url)
    assert r["score"] < 0.4, f"{url} -> {r['score']} {r['motivos']}"


@pytest.mark.parametrize("texto", GOLPES_SMS)
def test_sms_golpe_de_entrega(texto):
    r = score_email(sms(texto))
    assert r["veredito"] != "provavelmente seguro", f"{r['score']} {r['motivos']}"


@pytest.mark.parametrize("texto", LEGITIMOS_SMS)
def test_sms_legitimo_de_entrega(texto):
    r = score_email(sms(texto))
    assert r["score"] < 0.4, f"{r['score']} {r['motivos']}"


@pytest.mark.parametrize("url,marca", [
    ("http://correios-taxa-pendente.top/rastreio", "correios"),
    ("https://loggi-entrega.top/reagendar", "loggi"),
    ("http://jadlog-rastreio.online/taxa", "jadlog"),
    ("http://shopee-entrega.shop/confirmar", "shopee"),
])
def test_motivo_cita_a_transportadora(url, marca):
    motivos = " ".join(score_url(url)["motivos"]).lower()
    assert marca in motivos


def test_dominio_real_do_subdominio_falso():
    r = score_url("https://correios.encomenda-retida.online/pagamento")
    assert r["dominio"] == "encomenda-retida.online"
