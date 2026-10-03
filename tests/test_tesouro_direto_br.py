# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import pytest

import tesouro_direto_br as td
from tesouro_direto_br import (
    Carteira,
    Titulo,
    busca_tesouro_direto,
    calcula_retorno_carteira,
    calcula_retorno_titulo,
    get_custos,
    movimentacoes_titulos_publicos,
    nomeclatura_titulos,
)

TAXA_CSV = """Tipo Titulo;Data Vencimento;Data Base;Taxa Compra Manha;Taxa Venda Manha;PU Compra Manha;PU Venda Manha;PU Base Manha
Tesouro Selic;01/03/2025;08/07/2021;0,01;0,02;10800,00;10790,00;10790,00
Tesouro Selic;01/03/2025;09/07/2021;0,01;0,02;10810,00;10800,00;10800,00
Tesouro Selic;01/03/2025;12/07/2021;0,01;0,02;10820,00;10810,00;10810,00
Tesouro IPCA+;15/08/2026;08/07/2021;3,90;4,02;2900,00;2890,00;2890,00
Tesouro IPCA+;15/08/2026;09/07/2021;3,91;4,03;2902,00;2892,00;2892,00
Tesouro IPCA+;15/08/2026;12/07/2021;3,92;4,04;2904,00;2894,00;2894,00
"""

VENDA_CSV = """Tipo Titulo;Vencimento do Titulo;Data Venda;PU;Quantidade;Valor
Tesouro Selic;01/03/2025;08/07/2021;10790,00;10,5;113295,00
Tesouro Selic;01/03/2025;09/07/2021;10800,00;2,0;21600,00
Tesouro IPCA+;15/08/2026;08/07/2021;2890,00;3,0;8670,00
Tesouro IPCA+ com Juros Semestrais;15/05/2035;08/07/2021;4100,00;1,0;4100,00
"""


class _FakeResponse:
    def __init__(self, text):
        self.text = text


@pytest.fixture
def fake_tesouro(monkeypatch):
    """Substitui o download do Tesouro Transparente por CSVs pequenos."""
    calls = []

    def fake_get(url, *args, **kwargs):
        calls.append(url)
        if "PrecoTaxa" in url:
            return _FakeResponse(TAXA_CSV)
        if "Vendas" in url:
            return _FakeResponse(VENDA_CSV)
        raise AssertionError(f"URL inesperada: {url}")

    monkeypatch.setattr(td.tesouro_direto_br.requests, "get", fake_get)
    return calls


class TestClass:
    def setup_method(self):
        """Setup configurations executed before each test"""
        self.titulo_ipca = Titulo("Tesouro IPCA+", "2026-08-15", "2021-07-08", 33.65)
        self.titulo_selic = Titulo("Tesouro Selic", "2025-03-01", "2021-07-08", 50)

    # ==================== PACOTE ====================
    def test_version_matches_package_metadata(self):
        from importlib.metadata import version

        assert td.__version__ == version("tesouro_direto_br")

    # ==================== TITULO E CARTEIRA ====================
    def test_nomeclatura(self):
        nomes = nomeclatura_titulos()
        assert nomes["Tesouro Selic"] == "LTF"
        assert nomes["Tesouro IPCA+"] == "NTN-B PRINCIPAL"

    def test_titulo_e_carteira(self):
        assert self.titulo_ipca.nomeclatura == "NTN-B PRINCIPAL"
        assert Titulo().nomeclatura is None
        carteira = Carteira(Titulo())
        carteira.add(self.titulo_ipca)
        carteira.add(self.titulo_selic)
        assert len(carteira.titulos) == 2
        assert carteira.titulos[1]["Nomeclatura"] == "LTF"

    # ==================== DADOS (SEM REDE) ====================
    def test_busca_tesouro_direto(self, fake_tesouro):
        df = busca_tesouro_direto(tipo="taxa", agrupar=False)
        assert len(df) == 6
        assert pd.api.types.is_datetime64_any_dtype(df["Data Base"])
        assert pd.api.types.is_datetime64_any_dtype(df["Data Vencimento"])
        assert df["PU Base Manha"].iloc[0] == pytest.approx(10790.0)

        agrupado = busca_tesouro_direto(tipo="TAXA", agrupar=True)
        assert agrupado.index.names == ["Tipo Titulo", "Data Vencimento"]

    def test_busca_tipo_invalido(self):
        with pytest.raises(ValueError):
            busca_tesouro_direto(tipo="outro")
        with pytest.raises(ValueError):
            movimentacoes_titulos_publicos("outro")

    def test_movimentacoes(self, fake_tesouro):
        pivot = movimentacoes_titulos_publicos("venda")
        assert pivot.index.name == "Data Venda"
        assert set(pivot.columns) == {"Tesouro Selic_2025-03-01", "Tesouro IPCA+_2026-08-15"}
        assert pivot.loc["2021-07-08", "Tesouro Selic_2025-03-01"] == pytest.approx(10.5)

    def test_calcula_retorno_titulo(self, fake_tesouro):
        serie = calcula_retorno_titulo("Tesouro Selic", "2025-03-01", "2021-07-08", 50)
        assert serie.columns.tolist() == ["LTF_2025_2021-07-08"]
        assert len(serie) == 3
        assert serie.iloc[0, 0] == pytest.approx(50)
        assert serie.iloc[-1, 0] > serie.iloc[0, 0]

    def test_calcula_retorno_carteira(self, fake_tesouro):
        carteira = Carteira(Titulo())
        carteira.add(self.titulo_ipca)
        carteira.add(self.titulo_selic)
        resultado = calcula_retorno_carteira(carteira)
        assert {"MTM", "Cotas", "Rentabilidade Acumulada"} <= set(resultado.columns)
        assert resultado["MTM"].iloc[0] == pytest.approx(33.65 + 50)
        assert resultado["Rentabilidade Acumulada"].iloc[-1] > 0

    # ==================== CUSTOS ====================
    @pytest.mark.parametrize("dias, irpf", [(100, 0.225), (300, 0.2), (500, 0.175), (800, 0.15)])
    def test_get_custos_irpf(self, dias, irpf):
        datas = pd.date_range("2021-01-04", periods=dias, freq="D")
        mtm = pd.DataFrame({"MTM": np.linspace(1000, 1100, dias)}, index=datas)
        custos, detalhes = get_custos(mtm, custo_b3=False)
        assert detalhes["IRPF"] == pytest.approx(100 * irpf)
        assert detalhes["Taxa Custódia B3"] == 0
        assert custos == pytest.approx(100 * irpf)


# ==================== INTEGRAÇÃO (REDE) ====================
@pytest.mark.network
def test_fluxo_completo_com_dados_reais():
    taxa_agrupada = busca_tesouro_direto(tipo="taxa", agrupar=True)
    assert not taxa_agrupada.empty

    carteira = Carteira(Titulo())
    carteira.add(Titulo("Tesouro IPCA+", "2026-08-15", "2021-07-08", 33.65))
    carteira.add(Titulo("Tesouro Selic", "2025-03-01", "2021-07-08", 50))
    carteira_tesouro_direto = calcula_retorno_carteira(carteira)
    assert not carteira_tesouro_direto.empty
    assert carteira_tesouro_direto["Rentabilidade Acumulada"].iloc[-1] != 0

    movimentacao_pivot = movimentacoes_titulos_publicos("venda")
    assert not movimentacao_pivot.empty

    custos, _ = get_custos(carteira_tesouro_direto[["MTM"]], custo_b3=True)
    assert custos > 0
