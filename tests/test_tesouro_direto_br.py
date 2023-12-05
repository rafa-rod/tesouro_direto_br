
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import comparar_fundos_br as comp
import getpass

import sys
sys.path.append("./src/tesouro_direto_br")
import tesouro_direto_br as tesouro_direto

class TestClass():

    USER = getpass.getuser().lower()
    PASS = 1537Rafa!
    SERVIDOR = "proxy.inf.bndes.net"
    PORTA = 8080

    proxies = {
            "http":f"http://{USER}:{PASS}@{SERVIDOR}:{PORTA}",
            "https":f"http://{USER}:{PASS}@{SERVIDOR}:{PORTA}",
    }
    taxa_agrupada = tesouro_direto.busca_tesouro_direto(tipo="taxa", proxies=proxies, agrupar=True)
    assert not taxa_agrupada.empty

    carteira = tesouro_direto.Carteira(tesouro_direto.Titulo())
    titulo1 = tesouro_direto.Titulo("Tesouro IPCA+", "2026-08-15", "2021-07-08", 33.65)
    titulo2 = tesouro_direto.Titulo("Tesouro Selic", "2025-03-01", "2021-07-08", 50)
    carteira.add(titulo1)
    carteira.add(titulo2)
    assert len(carteira.titulos)==2

    carteira_tesouro_direto = tesouro_direto.calcula_retorno_carteira(carteira, proxies=proxies)
    assert not carteira_tesouro_direto.empty

    movimentacao_pivot = tesouro_direto.movimentacoes_titulos_publicos("venda", proxies=proxies)
    assert not movimentacao_pivot.empty

    ano, mes, dia = str(carteira_tesouro_direto.index[0]).split('-')
    dia = dia.split(" ")[0]
    retorno_periodo = 100*carteira_tesouro_direto['Rentabilidade Acumulada'].iloc[-1]
    print(f"Retorno da Carteira é de {round(retorno_periodo,2)}% desde {dia}/{mes}/{ano}")
    assert retorno_periodo != 0

    mtm_carteira = carteira_tesouro_direto[["MTM"]]
    custos, detalhamento_custos = tesouro_direto.get_custos( mtm_carteira, custo_b3=True )
    assert custos > 0

TestClass()