
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import comparar_fundos_br as comp

import sys
sys.path.append("./src/tesouro_direto_br")
import tesouro_direto_br as tesouro_direto

class TestClass():

    carteira = tesouro_direto.Carteira(tesouro_direto.Titulo())
    titulo1 = tesouro_direto.Titulo("Tesouro IPCA+", "2026-08-15", "2021-07-08", 33.65)
    titulo2 = tesouro_direto.Titulo("Tesouro Selic", "2025-03-01", "2021-07-08", 50)
    carteira.add(titulo1)
    carteira.add(titulo2)
    assert len(carteira.titulos)==2

    carteira_tesouro_direto = pd.DataFrame()
    for tpf in carteira.titulos:
        tipo_titulo = tpf["Tipo"]
        quantidade = tpf["Quantidade"]
        data_investimento = tpf["Data Investimento"]
        vencimento = tpf["Vencimento"]
        mtm_completo_titulo, mtm_titulo = tesouro_direto.calcula_mtm_titulo(tipo_titulo, quantidade, data_investimento, vencimento)
        investimento = mtm_completo_titulo.loc[pd.to_datetime(data_investimento), :].values[0]
        tesouro_direto.plot_mtm(mtm_completo_titulo, data_investimento, investimento)
        tesouro_direto.plot_taxas(tipo_titulo, data_investimento, vencimento)
        custos, detalhamento_custos = tesouro_direto.get_custos( mtm_titulo, investimento, data_investimento, vencimento )
        assert detalhamento_custos

        carteira_tesouro_direto = pd.concat([carteira_tesouro_direto, mtm_titulo], axis=1)

    retorno_carteira, retorno_titulos_acumulado = tesouro_direto.calcula_mtm_carteira(carteira_tesouro_direto)

    ano, mes, dia = str(retorno_carteira.index[0]).split('-')
    dia = dia.split(" ")[0]
    retorno_periodo = retorno_carteira.iloc[-1]*100
    print(f"Retorno da Carteira é de {round(retorno_periodo,2)}% desde {dia}/{mes}/{ano}")

    rentabilidades = pd.DataFrame(data= np.array([[retorno_periodo,
                        tesouro_direto.calcula_retorno_carteira(carteira_tesouro_direto, periodo=21),
                        tesouro_direto.calcula_retorno_carteira(carteira_tesouro_direto, periodo=126),
                        tesouro_direto.calcula_retorno_carteira(carteira_tesouro_direto, periodo=252),
                        tesouro_direto.calcula_retorno_carteira(carteira_tesouro_direto, periodo=504)]]),
                index=["23/01/2023"], 
                columns=[f"Rentabilidade desde {dia}/{mes}/{ano}",
                                                "Rentabilidade 21m",
                                                "Rentabilidade 126m",
                                                "Rentabilidade 252du",
                                                "Rentabilidade 504du"])

    assert not rentabilidades.T.empty

    cdi, cdi_acumulado = comp.get_benchmark(str(retorno_carteira.index[0]).split(" ")[0], 
                                            str(retorno_carteira.index[-1]).split(" ")[0], 
                                            benchmark = "cdi")
    retorno_cdi = (cdi_acumulado-1)*100

    assert not cdi_acumulado.T.empty

    plt.figure(figsize=(17,5))
    plt.title("Rentabilidade da Carteira")
    plt.plot(retorno_carteira*100)
    plt.plot(retorno_cdi, color="red", linestyle="--", lw=1)
    plt.legend(["Carteira", "CDI"], frameon=False, loc="center right")
    plt.show()

TestClass()