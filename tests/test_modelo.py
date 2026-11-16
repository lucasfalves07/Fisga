import pytest

from app import model
from app.features.url_features import HOST_FEATURES, host_features, is_official
from app.scoring import score_url

pytestmark = pytest.mark.skipif(not model.disponivel(), reason="modelo não treinado")


def test_features_tem_todas_as_colunas():
    assert list(host_features("https://exemplo.com.br").keys()) == HOST_FEATURES


def test_www_nao_muda_as_features():
    assert host_features("https://www.uol.com.br") == host_features("https://uol.com.br")


def test_caminho_nao_muda_as_features():
    assert host_features("https://site.com.br/login/pix") == host_features("https://site.com.br")


@pytest.mark.parametrize("url", ["https://www.nubank.com.br", "https://servicos.receita.gov.br", "https://rastreamento.correios.com.br"])
def test_dominio_oficial_pula_o_modelo(url):
    assert is_official(url)
    assert model.prob_golpe(url) is None


@pytest.mark.parametrize("url", [
    "http://pjdesbloqueio.appsempresa.tk/pj/",
    "https://review-santander-login.com",
    "http://nubank-seguranca.xyz/login",
])
def test_modelo_reconhece_golpe(url):
    assert model.prob_golpe(url) >= 0.5


@pytest.mark.parametrize("url", ["https://github.com", "https://www.uol.com.br", "https://www.globo.com"])
def test_modelo_nao_acusa_site_comum(url):
    assert model.prob_golpe(url) < 0.4


def test_resposta_mostra_os_componentes():
    r = score_url("https://review-santander-login.com")
    assert set(r["componentes"]) == {"regras", "modelo"}
    assert any("Modelo treinado" in m for m in r["motivos"])
