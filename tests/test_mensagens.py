import pandas as pd
import pytest

from app.features.header_checks import extract_urls
from app.llm.analyzer import heuristic
from scripts import avaliar_texto

DADOS = pd.read_csv("data/mensagens.csv")


def test_dataset_balanceado_e_sem_repeticao():
    assert set(DADOS["label"]) == {0, 1}
    assert abs(DADOS["label"].mean() - 0.5) < 0.05
    assert not DADOS["texto"].duplicated().any()


@pytest.mark.parametrize("texto,esperado", [
    ("Cancele em itau-dispositivo.com agora.", ["itau-dispositivo.com"]),
    ("entre no grupo t.me/lucro_certo", ["t.me/lucro_certo"]),
    ("Valor R$ 1.200,00 no CNPJ 51.893.221/0001-04", []),
    ("mande para joao@gmail.com", []),
    ("Dr. Paulo as 9h", []),
])
def test_extrai_dominio_sem_http(texto, esperado):
    assert extract_urls(texto) == esperado


def test_heuristica_ignora_acento():
    assert heuristic("", "Informe o codigo de verificacao")["score"] == heuristic("", "Informe o código de verificação")["score"]


def test_avaliacao_com_llm_falso(tmp_path, monkeypatch):
    monkeypatch.setattr(avaliar_texto, "CACHE", tmp_path / "cache.json")
    rotulo = dict(zip(DADOS["texto"], DADOS["label"]))
    monkeypatch.setattr(avaliar_texto, "llm", lambda s, t: {"score": 0.9 if rotulo[t] else 0.1})
    amostra = pd.concat([DADOS.head(10), DADOS.tail(10)]).reset_index(drop=True)
    res = avaliar_texto.avaliar(amostra, usar_llm=True, pausa=0)
    assert res["teste"]["LLM (só texto)"]["f1"] == 1.0
    assert (tmp_path / "cache.json").exists()
