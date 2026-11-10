import csv

from scripts import coletar_urls as c


def test_alvo_br():
    assert c.alvo_br("http://nubank-seguranca.xyz/login")
    assert c.alvo_br("http://site.com/pix/pagar")
    assert c.alvo_br("http://correios-entrega.top")
    assert c.alvo_br("http://algo.com.br/x")
    assert not c.alvo_br("http://paypal-login.xyz/verify")


def test_oficial():
    assert c.oficial("https://www.nubank.com.br/login")
    assert c.oficial("https://servicos.receita.gov.br")
    assert not c.oficial("http://nubank-seguranca.xyz")


def test_coletar_e_salvar(tmp_path, monkeypatch):
    fontes = {
        "fake": lambda: [
            "http://nubank-seguranca.xyz/login",
            "http://paypal-verify.top",
            "https://www.itau.com.br",
            "http://nubank-seguranca.xyz/login/",
        ]
    }
    monkeypatch.setattr(c, "tranco", lambda a, b: ["https://uol.com.br", "https://google.com"])

    linhas = c.coletar(fontes, 10, 10)
    golpes = [l for l in linhas if l["label"] == 1]
    assert [l["url"] for l in golpes] == ["http://nubank-seguranca.xyz/login"]

    saida = tmp_path / "urls.csv"
    c.salvar(linhas, saida, balancear=True)
    with saida.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
