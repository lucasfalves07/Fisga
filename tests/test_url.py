import pytest

from app.scoring import score_url


@pytest.mark.parametrize("url", [
    "https://www.nubank.com.br",
    "https://www.itau.com.br/conta-corrente",
    "https://www.gov.br/receitafederal",
    "https://rastreamento.correios.com.br",
])
def test_oficiais(url):
    assert score_url(url)["score"] < 0.4


@pytest.mark.parametrize("url", [
    "http://nubank-seguranca.xyz/login",
    "http://correios-taxa-pendente.top/pagamento",
    "http://itaau.com/acesso",
    "http://192.168.10.5/bradesco/senha",
    "https://caixa.gov.br.atualizacao-cadastro.online/token",
])
def test_golpes(url):
    assert score_url(url)["score"] >= 0.4


def test_motivo_marca():
    r = score_url("http://nubank-seguranca.xyz/login")
    assert any("nubank" in m for m in r["motivos"])
