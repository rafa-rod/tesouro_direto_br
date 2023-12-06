#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  8 09:50:30 2023

@author: Rafael
"""

import pandas as pd
import requests
import io
import numpy as np
from typing import Dict, List, Optional, Union
from datetime import datetime, timedelta

import warnings

warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt
import pyettj.ettj as ettj


def nomeclatura_titulos() -> Dict[str, str]:
    nomeclatura_dict = {
        "Tesouro IPCA+ com Juros Semestrais": "NTN-B",
        "Tesouro IGPM+ com Juros Semestrais": "NTN-C",
        "Tesouro Prefixado": "LTN",
        "Tesouro Prefixado com Juros Semestrais": "NTN-F",
        "Tesouro Selic": "LTF",
        "Tesouro IPCA+": "NTN-B Principal",
        "Tesouro RendA+": "RendA+",
        "Tesouro Educa+": "Educa+",
    }
    return nomeclatura_dict


class Titulo:
    def __init__(
        self,
        tipo_titulo=None,
        data_vencimento=None,
        data_investimento=None,
        investimento=None,
    ):
        self.tipo_titulo = tipo_titulo
        self.data_investimento = data_investimento
        self.data_vencimento = data_vencimento
        self.investimento = investimento
        if self.tipo_titulo:
            self.nomeclatura = nomeclatura_titulos()[self.tipo_titulo]
        else:
            self.nomeclatura = None
        self.titulo = {
            "Tipo": self.tipo_titulo,
            "Nomeclatura": self.nomeclatura,
            "Vencimento": self.data_vencimento,
            "Data Investimento": self.data_investimento,
            "Investimento": self.investimento,
        }


class Carteira(Titulo):
    def __init__(self, Titulo):
        self.titulo = Titulo.titulo
        self.titulos = []

    def add(self, outro_titulo):
        self.titulos.append(outro_titulo.titulo)


def busca_tesouro_direto(
    tipo: str = "venda", proxies: Optional[Dict[str, str]] = None, agrupar: bool = True
):
    """
    Função que retorna os dados diários do Tesouro Transparente.
        Parâmetros:
                tipo (str) => informar "venda" ou "resgate" ou "taxa";
                proxies (dict) => opcional. se necessário, informar dicionário com as proxies, exemplo: {"http":f'https://{LOGIN}:{SENHA}@{PROXY_EMPRESA}:{PORTA}'}
                agrupar (bool) => opcional. para agrupar o dataframe por titulo e vencimento.
            Retorno:
                df (dataframe): tabela contendo as informações dos TPFs por data.
    """
    if tipo.lower() == "venda":
        url = "https://www.tesourotransparente.gov.br/ckan/dataset/f0468ecc-ae97-4287-89c2-6d8139fb4343/resource/e5f90e3a-8f8d-4895-9c56-4bb2f7877920/download/VendasTesouroDireto.csv"
    elif tipo.lower() == "taxa":
        url = "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv"
    elif tipo.lower() == "resgate":
        url = "https://www.tesourotransparente.gov.br/ckan/dataset/f30db6e4-6123-416c-b094-be8dfc823601/resource/30c2b3f5-6edd-499a-8514-062bfda0f61a/download/RecomprasTesouroDireto.csv"
    else:
        raise ValueError("Tipo não encontrado")
    if proxies:
        data = requests.get(url, proxies=proxies, verify=False).text
    else:
        data = requests.get(url).text

    data_str = io.StringIO(data)
    df = pd.read_csv(data_str, sep=";", decimal=",")

    coluna_datas = [
        x for x in df.columns if x.startswith("Data") or x.startswith("Vencimento")
    ]
    if coluna_datas:
        for col in coluna_datas:
            df[col] = pd.to_datetime(df[col], format="%d/%m/%Y")

    if agrupar:  # titulo e seu vencimento
        multi_indice = pd.MultiIndex.from_frame(df.iloc[:, :2])
        df = df.set_index(multi_indice).iloc[:, 2:]
    return df


def calcula_taxa_b3(serie_mtm: pd.DataFrame) -> pd.DataFrame:
    """
    Taxa cobrada pela custódia da B3 de 0,2% no ano, cobrado 0,1% em Janeiro e Julho, ou de forma proporcional
    ao tempo investido.
    Títulos Públicos via mercado secundário não pagam esta taxa,
    uma vez que estes ativos são custodiados no Sistema Especial de Liquidação e Custódia (Selic) e não na B3.
    O valor incide sobre o valor investimento mais os rendimentos brutos, ou seja, sem descontar imposto de renda e outros.
    Desde agosto de 2020, para investimentos (incluindo juros) em Tesouro Selic de até R$ 10.000,00,
    não há cobrança da taxa de custódia. Se houver rendimentos e ultrapassar esse valor, incide sobre o excedente.
    """
    datas_b3 = serie_mtm.groupby(pd.Grouper(freq="MS")).first()
    datas_b3 = datas_b3[
        (datas_b3.index.month == 1) | (datas_b3.index.month == 7)
    ]  # meses de pagamento à B3

    ano, mes, dia = str(serie_mtm.index[0])[:-9].split("-")
    inicio_primeiro_semestre = "/".join([dia, mes, ano])
    ano, mes, dia = str(datas_b3.index[0])[:-9].split("-")
    fim_primeiro_semestre = "/".join([dia, mes, ano])
    if datas_b3.index[0] < serie_mtm.index[0]:
        datas_b3.drop(datas_b3.index[0], inplace=True)
        ano, mes, dia = str(datas_b3.index[0])[:-9].split("-")
        fim_primeiro_semestre = "/".join([dia, mes, ano])

    if serie_mtm.columns.str.contains("LTF"):
        # incide sobre o excedente de 10000
        serie_mtm = serie_mtm - 10_000
        serie_mtm[serie_mtm.columns] = np.where(serie_mtm < 0, 0, serie_mtm)

    hoje = datetime.today().date()
    if not datas_b3.empty:
        # custos semestrais:
        custos_b3 = datas_b3.copy()
        custos_b3["custo"] = [
            custos_b3.loc[x, :].values[0] * (0.25 / 2 / 100)
            if x < pd.to_datetime("2022-01-01")
            else custos_b3.loc[x, :].values[0] * (0.2 / 2 / 100)
            for x in custos_b3.index
        ]  # era 0,25% e a partir de jan/22 é de 0,2%aa ou 0,1%semestre

        # custos proporcionais após completar semestre
        ano, mes, dia = str(custos_b3.index[-1])[:-9].split("-")
        inicio = "/".join([dia, mes, ano])
        ano, mes, dia = str(hoje).split("-")
        fim = "/".join([dia, mes, ano])
        datas = ettj.listar_dias_uteis(inicio, fim)
        custos_b3["custo"] = (
            custos_b3["custo"]
            + ((len(datas) * (0.1 / 100)) / 126) * custos_b3["MTM"].values[-1]
        )

        # custos proporcionais no inicio do semestre
        datas = ettj.listar_dias_uteis(inicio_primeiro_semestre, fim_primeiro_semestre)
        custos_b3["custo"] = (
            custos_b3["custo"]
            + ((len(datas) * (0.1 / 100)) / 126) * custos_b3["MTM"].values[0]
        )
    else:
        # custos proporcionais antes de completar o semestre (resgate em menos de 6 meses)
        ano, mes, dia = str(serie_mtm.index[0])[:-9].split("-")
        inicio = "/".join([dia, mes, ano])
        ano, mes, dia = str(serie_mtm.index[-1])[:-9].split("-")
        fim = "/".join([dia, mes, ano])
        datas = ettj.listar_dias_uteis(inicio, fim)
        custos_b3 = pd.DataFrame(
            np.array(
                [
                    serie_mtm.iloc[-1].values[0],
                    serie_mtm.iloc[-1].values[0] * (len(datas) * 0.1 / 100) / 126,
                ]
            ),
            index=["MTM", "custo"],
            columns=[hoje],
        ).T
    return custos_b3


def get_custos(
    serie_mtm: pd.DataFrame,
    custo_b3: bool = False,
) -> Union[pd.DataFrame, pd.DataFrame]:
    """
    Calcula os custos (taxas: custódia B3 e impostos: IOF e IRPF) incidentes sobre os títulos públicos.
    Taxa de administração está sendo considerada zero, pois a maior parte das corretoras não cobram.
    Se estiver negociando TPF pelo mercado secundário, o valor dos custos da B3 é zero, informe custo_b3=False.
    """

    mtm_atual = serie_mtm.iloc[-1].values[0]
    investimento = serie_mtm.iloc[0].values[0]

    datas = serie_mtm.index.tolist()
    T = len(datas)
    if T < 30:
        iof = pd.read_excel("tabela_iof_investimentos.xlsx", index_col=0)
        iof = iof.loc[T, :].values[0]
        print(f"IOF de {int(iof*100)}%")
    else:
        iof = 0

    if T > 720:
        irpf = 0.15
    elif T <= 720 and T > 360:
        irpf = 0.175
    elif T <= 360 and T > 180:
        irpf = 0.2
    elif T <= 180:
        irpf = 0.225

    if not custo_b3:
        taxa_custodia = 0
        custo_b3 = mtm_atual * taxa_custodia
    else:
        custos = calcula_taxa_b3(serie_mtm)
        custo_b3 = custos["custo"].sum()

    rendimento = mtm_atual - investimento
    detalhamento_custos = {
        "IRPF": rendimento * irpf,
        "Taxa Custódia B3": custo_b3,
        "IOF": iof * rendimento,
    }
    custos = (rendimento * irpf) + custo_b3 + (iof * rendimento)

    print(f"Retorno Bruto {rendimento}")
    retorno_liquido = rendimento - custos
    print(f"Retorno Liquido {retorno_liquido}")
    print(f"MTM Liquido {mtm_atual+retorno_liquido}")
    return custos, detalhamento_custos


def _get_valid_date(
    date: Union[str, datetime], carteira_tesouro_direto: pd.DataFrame()
) -> datetime:
    if isinstance(date, str):
        date = pd.to_datetime(date)
    count = 0
    df = carteira_tesouro_direto[
        carteira_tesouro_direto.index.isin([date + timedelta(days=count)])
    ]
    while df.empty:
        count += 1
        df = carteira_tesouro_direto[
            carteira_tesouro_direto.index.isin([date.date() + timedelta(days=count)])
        ]
    return date + timedelta(days=count)


def movimentacoes_titulos_publicos(
    tipo_movimentacao: str,
    proxies: Optional[Dict[str, str]] = None,
    excluir: List[str] = ["Juros Semestrais", "Educa+", "RendA+"],
    filtrar_data: Union[str, None] = None,
) -> pd.DataFrame:
    """
    Função para obter as movimentações de resgate (recompra) ou venda de TPF.
    Parâmetros:
            tipo_movimentacao (str) => informar "venda" ou "resgate";
            excluir (list) => opcional. tipos de títulos a serem desconsiderados;
            proxies (dict) => opcional. se necessário, informar dicionário com as proxies, exemplo: {"http":f'https://{LOGIN}:{SENHA}@{PROXY_EMPRESA}:{PORTA}'}
            filtrar_data (str) => opcional. recomendado filtrar pela data de investimento para excluir TPFs que você não possua em carteira.
        Retorno:
            movimentacao_pivot (dataframe): tabela contendo a quantidade de TPFs movimentados por data.
    """
    if tipo_movimentacao != "resgate" and tipo_movimentacao != "venda":
        raise ValueError("Tipo de Movimentação não encontrada.")
    # quando vc resgata antes do vencimento, Tesouro recompra o título
    taxa_agrupada = busca_tesouro_direto(
        tipo=tipo_movimentacao, proxies=proxies, agrupar=True
    )
    movimentacao = (
        taxa_agrupada.reset_index()
        .groupby(
            [
                "Tipo Titulo",
                "Vencimento do Titulo",
                f"Data {tipo_movimentacao.title()}",
            ],
            as_index=False,
        )[["Quantidade"]]
        .sum()
    )
    if filtrar_data:
        dt_investimento = pd.to_datetime(filtrar_data)
        movimentacao = movimentacao[
            (movimentacao["Vencimento do Titulo"] > dt_investimento)
            & (movimentacao[f"Data {tipo_movimentacao.title()}"] > dt_investimento)
        ]
    movimentacao = movimentacao.set_index(
        ["Tipo Titulo", "Vencimento do Titulo"]
    ).reset_index()
    movimentacao["Vencimento do Titulo"] = movimentacao["Vencimento do Titulo"].astype(
        str
    )
    if excluir:
        df1 = pd.DataFrame()
        for remover in excluir:
            df = movimentacao[movimentacao["Tipo Titulo"].str.contains(f"{remover}")]
            df1 = pd.concat([df1, df])
        movimentacao = movimentacao.drop(df1.index)
    movimentacao["Titulo"] = (
        movimentacao["Tipo Titulo"] + "_" + movimentacao["Vencimento do Titulo"]
    )
    movimentacao = movimentacao.drop(["Tipo Titulo", "Vencimento do Titulo"], axis=1)
    movimentacao_pivot = pd.pivot_table(
        movimentacao.reset_index(),
        values="Quantidade",
        index=f"Data {tipo_movimentacao.title()}",
        columns="Titulo",
    )
    return movimentacao_pivot


def calcula_retorno_titulo(
    tipo_titulo: str,
    vencimento: str,
    data_investimento: str,
    investimento: str,
    proxies: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Função que calcula os retornos diários de um título público.
        Parâmetros:
                tipo_titulo (str) => informar tipo de TPF, exemplo: Tesouro Selic (consultar: tesouro_direto.nomeclatura_titulos());
                vencimento (str) => data de vencimento do TPF;
                data_investimento (str) => data de aquisição do TPF;
                investimento (str) => valor investido;
                proxies (dict) => opcional. se necessário, informar dicionário com as proxies, exemplo: {"http":f'https://{LOGIN}:{SENHA}@{PROXY_EMPRESA}:{PORTA}'}
            Retorno:
                serie_retorno (dataframe): retorno acumulado desde a data de investimento.
    """
    taxa_agrupada = busca_tesouro_direto(tipo="taxa", proxies=proxies, agrupar=True)
    titulo = taxa_agrupada.loc[(tipo_titulo, vencimento)]
    serie_pu = titulo.sort_values("Data Base").set_index("Data Base")[["PU Base Manha"]]
    nom = nomeclatura_titulos()
    venc = vencimento.split("-")[0]
    serie_pu.columns = [nom[tipo_titulo].upper() + "_" + venc + "_" + data_investimento]
    serie_pu_filtrado = serie_pu[serie_pu.index >= pd.to_datetime(data_investimento)]
    rentabilidade_diaria = serie_pu_filtrado.pct_change()
    serie_retorno = (1 + rentabilidade_diaria.fillna(investimento)).cumprod() - 1
    return serie_retorno


def calcula_retorno_carteira(
    carteira: Carteira, proxies: Optional[Dict[str, str]] = None
) -> pd.DataFrame:
    """
    Função que calcula o retorno de uma carteira de títulos públicos pelo método de cotização de carteiras.
        Parâmetros:
                carteira (class) => carteira de TPFs (podendo conter 1 ou mais TPFs);
                proxies (dict) => opcional. se necessário, informar dicionário com as proxies, exemplo: {"http":f'https://{LOGIN}:{SENHA}@{PROXY_EMPRESA}:{PORTA}'}
            Retorno:
                carteira_tesouro_direto (dataframe): retorno acumulado desde a data de investimento do primeiro TPF da carteira.
    """
    carteira.titulos = sorted(carteira.titulos, key=lambda d: d["Data Investimento"])
    carteira_tesouro_direto = pd.DataFrame()
    for tpf in carteira.titulos:
        tipo_titulo = tpf["Tipo"]
        investimento = tpf["Investimento"]
        data_investimento = tpf["Data Investimento"]
        vencimento = tpf["Vencimento"]
        serie_retorno = calcula_retorno_titulo(
            tipo_titulo, vencimento, data_investimento, investimento, proxies=proxies
        )
        carteira_tesouro_direto = pd.concat(
            [carteira_tesouro_direto, serie_retorno], axis=1
        )
    columns = carteira_tesouro_direto.columns.tolist()
    carteira_tesouro_direto["MTM"] = carteira_tesouro_direto.sum(axis=1)
    carteira_tesouro_direto["Qde Cotas"] = carteira_tesouro_direto["MTM"].iloc[0]
    carteira_tesouro_direto["Cotas"] = 1
    investimentos = [
        pd.to_datetime(carteira.titulos[x]["Data Investimento"])
        for x in range(len(carteira.titulos))
    ]
    investimentos_datas_validas = [
        _get_valid_date(x, carteira_tesouro_direto) for x in investimentos
    ]
    for x, idx in enumerate(carteira_tesouro_direto.index[1:], start=1):
        idx_investimento = [
            i for i, date in enumerate(investimentos_datas_validas) if idx == date
        ]
        if idx_investimento:
            idx_investimento = idx_investimento[0]
            dt_investimento = [investimentos_datas_validas[idx_investimento]]
            ativo = [
                carteira.titulos[x]["Nomeclatura"]
                + "_"
                + carteira.titulos[x]["Vencimento"][:4]
                + "_"
                + str(investimentos[idx_investimento])[:-9]
                for x in range(len(carteira.titulos))
                if pd.to_datetime(carteira.titulos[x]["Data Investimento"])
                == investimentos[idx_investimento]
            ]
            investimento = carteira_tesouro_direto.loc[dt_investimento, ativo].values[
                0
            ][0]
            carteira_tesouro_direto.loc[dt_investimento, "Qde Cotas"] = (
                carteira_tesouro_direto.iloc[x - 1]["Qde Cotas"]
                + investimento / carteira_tesouro_direto.iloc[x - 1]["Cotas"]
            )
        else:
            carteira_tesouro_direto.loc[
                idx, "Qde Cotas"
            ] = carteira_tesouro_direto.iloc[x - 1]["Qde Cotas"]
        carteira_tesouro_direto.loc[idx, "Cotas"] = (
            carteira_tesouro_direto.loc[idx, columns].dropna().sum()
            / carteira_tesouro_direto.loc[idx, "Qde Cotas"]
        )
    carteira_tesouro_direto["Rentabilidade Diária"] = carteira_tesouro_direto[
        "Cotas"
    ].pct_change()
    carteira_tesouro_direto["Rentabilidade Acumulada"] = (
        1 + carteira_tesouro_direto["Rentabilidade Diária"]
    ).cumprod() - 1
    return carteira_tesouro_direto


def plot_taxas(
    tipo_titulo: str,
    data_investimento: str,
    vencimento: str,
    proxies: Optional[Dict[str, str]] = None,
) -> None:
    """
    Função plota a evolução das taxas do TPF.
        Parâmetros:
                tipo_titulo (str) => informar tipo de TPF, exemplo: Tesouro Selic (consultar: tesouro_direto.nomeclatura_titulos());
                data_investimento (str) => data de aquisição do TPF;
                vencimento (str) => data de vencimento do TPF;
                proxies (dict) => opcional. se necessário, informar dicionário com as proxies, exemplo: {"http":f'https://{LOGIN}:{SENHA}@{PROXY_EMPRESA}:{PORTA}'}
    """
    taxa_agrupada = busca_tesouro_direto(tipo="taxa", proxies=proxies, agrupar=True)
    titulo = taxa_agrupada.loc[(tipo_titulo, vencimento)]
    taxa = titulo.sort_values("Data Base").set_index("Data Base")[
        ["Taxa Compra Manha", "Taxa Venda Manha"]
    ]

    plt.figure(figsize=(16, 5))
    plt.plot(taxa)
    plt.legend(["Taxa Compra Manha", "Taxa Venda Manha"], frameon=False)
    plt.axvline(pd.to_datetime(data_investimento), color="red")
    plt.show()
