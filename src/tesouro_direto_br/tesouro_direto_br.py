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
from typing import Dict, Optional, Union

import warnings

warnings.filterwarnings("ignore")

import matplotlib.pyplot as plt

import pyettj.ettj as ettj
import comparar_fundos_br as comp


def nomeclatura_titulos() -> Dict[str, str]:
    nomeclatura_dict = {
        "Tesouro IPCA+ com Juros Semestrais": "NTN-B",
        "Tesouro IGPM+ com Juros Semestrais": "NTN-C",
        "Tesouro Prefixado": "LTN",
        "Tesouro Prefixado com Juros Semestrais": "NTN-F",
        "Tesouro Selic": "LTF",
        "Tesouro IPCA+": "NTN-B Principal",
        "Tesouro RendA+": "RendA+",
    }
    return nomeclatura_dict


class Titulo:
    def __init__(
        self,
        tipo_titulo=None,
        data_vencimento=None,
        data_investimento=None,
        quantidade=None,
    ):
        self.tipo_titulo = tipo_titulo
        self.data_investimento = data_investimento
        self.data_vencimento = data_vencimento
        self.quantidade = quantidade
        if self.tipo_titulo:
            self.nomeclatura = nomeclatura_titulos()[self.tipo_titulo]
        else:
            self.nomeclatura = None
        self.titulo = {
            "Tipo": self.tipo_titulo,
            "Nomeclatura": self.nomeclatura,
            "Vencimento": self.data_vencimento,
            "Data Investimento": self.data_investimento,
            "Quantidade": self.quantidade,
        }


class Carteira(Titulo):
    def __init__(self, Titulo):
        self.titulo = Titulo.titulo
        self.titulos = []

    def add(self, outro_titulo):
        self.titulos.append(outro_titulo.titulo)


def busca_tesouro_direto(
    tipo: str = "venda", proxies: Optional[Dict[str, str]] = None, agrupar: bool = False
):
    if tipo.lower() == "venda":
        url = "https://www.tesourotransparente.gov.br/ckan/dataset/f0468ecc-ae97-4287-89c2-6d8139fb4343/resource/e5f90e3a-8f8d-4895-9c56-4bb2f7877920/download/VendasTesouroDireto.csv"
    elif tipo.lower() == "taxa":
        url = "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/PrecoTaxaTesouroDireto.csv"
    elif tipo.lower() == "resgate":
        url = "https://www.tesourotransparente.gov.br/ckan/dataset/f30db6e4-6123-416c-b094-be8dfc823601/resource/30c2b3f5-6edd-499a-8514-062bfda0f61a/download/RecomprasTesouroDireto.csv"
    elif tipo.lower() == "investidor":
        url = "https://www.tesourotransparente.gov.br/ckan/dataset/48a7fd9d-78e5-43cb-bcba-6e7dcaf2d741/resource/0fd2ac86-4673-46c0-a889-b46224ade563/download/InvestidoresTesouroDireto.csv"
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
    datas_b3 = serie_mtm.groupby(pd.Grouper(freq="MS")).first()
    datas_b3 = datas_b3[
        (datas_b3.index.month == 1) | (datas_b3.index.month == 7)
    ]  # meses de pagamento à B3

    custos_b3 = datas_b3.copy()
    custos_b3["custo"] = [
        custos_b3.loc[x, :].values[0] * (0.25 / 100)
        if x < pd.to_datetime("2022-01-01")
        else custos_b3.loc[x, :].values[0] * (0.2 / 100)
        for x in custos_b3.index
    ]  # era 0,25% e a partir de jan/22 será 0,2%aa
    return custos_b3


def get_custos(
    serie_mtm: pd.DataFrame,
    investimento: float,
    data_investimento: str,
    data_resgate: str,
    custo_b3: bool = False,
):

    mtm_atual = serie_mtm.iloc[0].values[0]

    datas = ettj.listar_dias_uteis(data_investimento, data_resgate)
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
        taxa_custodia = 0.2 / 100
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
    return custos, detalhamento_custos


def calcula_mtm_titulo(
    tipo_titulo: str,
    quantidade: float,
    data_investimento: str,
    vencimento: str,
    proxies: Optional[Dict[str, str]] = None,
) -> Union[pd.DataFrame, pd.DataFrame]:
    taxa_agrupada = busca_tesouro_direto(tipo="taxa", proxies=proxies, agrupar=True)
    titulo = taxa_agrupada.loc[(tipo_titulo, vencimento)]
    serie_mtm = (
        titulo.sort_values("Data Base").set_index("Data Base")[["PU Base Manha"]]
        * quantidade
    )
    nom = nomeclatura_titulos()
    venc = vencimento.split("-")[0]
    serie_mtm.columns = [nom[tipo_titulo].upper() + "_" + venc]
    serie_mtm_filtrado = serie_mtm[serie_mtm.index >= pd.to_datetime(data_investimento)]
    return serie_mtm, serie_mtm_filtrado


def calcula_mtm_carteira(
    carteira_tesouro_direto: pd.DataFrame,
) -> Union[pd.DataFrame, pd.DataFrame]:
    df1 = carteira_tesouro_direto.copy()
    df1.columns = df1.columns.str.upper()
    retorno_titulos = df1.pct_change()
    retorno_titulos_acumulado = ((1 + retorno_titulos).cumprod() - 1) * 100
    pesos = df1 / df1.iloc[-1].sum()
    retorno_carteira = (pesos * retorno_titulos_acumulado / 100).sum(axis=1)
    return retorno_carteira, retorno_titulos_acumulado


def calcula_retorno_carteira(mtm: pd.DataFrame, periodo=None) -> float:
    if periodo:
        mtm = mtm[:periodo]
    pesos = mtm / mtm.iloc[-1].sum()
    retorno = mtm.pct_change()
    retorno_acumulado = ((1 + retorno).cumprod() - 1) * 100
    retorno_carteira = (pesos * retorno_acumulado / 100).sum(axis=1)
    return round(retorno_carteira.iloc[-1] * 100, 4)


def plot_taxas(
    tipo_titulo: str,
    data_investimento: str,
    vencimento: str,
    proxies: Optional[Dict[str, str]] = None,
) -> None:
    taxa_agrupada = busca_tesouro_direto(tipo="taxa", proxies=proxies, agrupar=True)
    titulo = taxa_agrupada.loc[(tipo_titulo, vencimento)]
    taxa = titulo.sort_values("Data Base").set_index("Data Base")[
        ["Taxa Compra Manha", "Taxa Venda Manha"]
    ]

    plt.figure(figsize=(16, 5))
    plt.plot(taxa)
    plt.axvline(pd.to_datetime(data_investimento), color="red")
    plt.show()


def plot_mtm(
    serie_mtm: pd.DataFrame, data_investimento: str, investimento: float
) -> None:
    plt.figure(figsize=(16, 5))
    plt.plot(serie_mtm)
    plt.axvline(pd.to_datetime(data_investimento), color="red")
    plt.axhline(investimento, color="red", linestyle="--")
    plt.show()
