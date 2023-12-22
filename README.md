<!-- buttons -->
<p align="center">
<a href="https://www.python.org/">
<img src="https://img.shields.io/badge/python-v3-brightgreen.svg"
alt="python"></a> &nbsp;
<a href="https://opensource.org/licenses/MIT">
<img src="https://img.shields.io/badge/license-MIT-brightgreen.svg"
alt="MIT license"></a> &nbsp;
<a href="https://github.com/psf/black">
<img src="https://img.shields.io/badge/code%20style-black-000000.svg"
alt="Code style: black"></a> &nbsp;
<a href="http://mypy-lang.org/">
<img src="http://www.mypy-lang.org/static/mypy_badge.svg"
alt="Checked with mypy"></a> &nbsp;
</p>

<!-- content -->

**tesouro_direto_br** é uma biblioteca Python para executar cálculos para gerenciamento de carteira de Títulos Públicos Federais (TPFs) usando dados do Tesouro Direto. Com ela, você poderá:

- inserir seus TPFs e montar uma carteira;
- calcular o valor de mercado dos TPFs (marcação a mercado) e da carteira;
- calcular retorno da carteira;
- visualizar a evolução do valor de mercado e do retorno;
- detalhamento dos custos envolvidos: IOF, IRPF, taxa de custódia B3;
- obter rentabilidade líquida e bruta da carteira/título;
- você pode simular uma carteira hipotética de TPFs;
- você pode comparar com *benchmarks* como: CDI, ibovespa, IMA-B, IMA-B 5 e IMA-B 5+;

## Instalação

### Usando pip

Pode usar o comando:

```sh
pip install tesouro-direto-br
```

Alternativamente, obter diretamente do Github:

```sh
pip install https://github.com/rafa-rod/tesouro_direto_br/archive/refs/heads/main.zip
```

## Por que é importante?

Notei que algumas corretoras mostraram a rentabilidade da carteira de forma equivocada. Algumas mostram apenas de um título, não da carteira e somente de períodos específicos. Além disso, você pode simular investimentos em períodos históricos específicos e estudar suas opções de investimento antes de adquirir algum título específico.

## Examplos

Importe a biblioteca e insira titulos publicos a uma carteira vazia:

```python
import getpass
import tesouro_direto_br as tesouro_direto

#Criar uma carteira vazia:
carteira = tesouro_direto.Carteira(tesouro_direto.Titulo())

#Adicionar titulos publicos:
titulo1 = tesouro_direto.Titulo("Tesouro IPCA+", "2026-08-15", "2021-07-08", 33.65)
titulo2 = tesouro_direto.Titulo("Tesouro Selic", "2025-03-01", "2021-07-08", 50)

carteira.add(titulo1)
carteira.add(titulo2)
```

Com a carteira montada, é hora de calcular o valor de mercado da carteira (marcação a mercado):

```python
USER = getpass.getuser().lower()
PASS = getpass.getpass("Senha de rede: ")
SERVIDOR = "SERVIDOR"
PORTA = "PORTA"

proxies = {
          "http":f"http://{USER}:{PASS}@{SERVIDOR}:{PORTA}",
          "https":f"http://{USER}:{PASS}@{SERVIDOR}:{PORTA}",
}

carteira_tesouro_direto = tesouro_direto.calcula_retorno_carteira(carteira, proxies=proxies)
```

Com os valores de mercado, é possível obter a rentabilidade da carteira:

```python
retorno_carteira, retorno_titulos_acumulado = tesouro_direto.calcula_mtm_carteira(carteira_tesouro_direto)

ano, mes, dia = str(retorno_carteira.index[0]).split('-')
dia = dia.split(" ")[0]
retorno_periodo = retorno_carteira.iloc[-1]*100
print(f"Retorno da Carteira é de {round(retorno_periodo,2)}% desde {dia}/{mes}/{ano}")
```

Se desejar obter a rentabilidade por período específico (como as corretoras fazem):

```python
rentalibidade_periodo = 100*carteira_tesouro_direto['Rentabilidade Acumulada'].iloc[-1]
print(f"Rentabilidade do período é de {round(rentalibidade_periodo, 3)}%")
```

A análise melhora se você comparar com um *benchmark* como o CDI:

```python
import matplotlib.pyplot as plt
import comparar_fundos_br as comp

cdi, cdi_acumulado = comp.get_benchmark(str(carteira_tesouro_direto.index[0]).split(" ")[0], 
                                        str(carteira_tesouro_direto.index[-1]).split(" ")[0], 
                                        benchmark = "cdi", proxy=proxies)
retorno_cdi = (cdi_acumulado-1)*100

plt.figure(figsize=(17,5))
plt.title("Rentabilidade da Carteira")
plt.plot(carteira_tesouro_direto[["Rentabilidade Acumulada"]]*100)
plt.plot(retorno_cdi, color="red", linestyle="--", lw=1)
plt.legend(["Carteira", "CDI"], frameon=False, loc="center right")
plt.ylabel('%',rotation=0,labelpad=-10,loc="top")
plt.grid(axis="x")
plt.show()
```

<center>
<img src="https://github.com/rafa-rod/tesouro_direto_br/blob/main/media/cdi.png" style="width:100%;"/>
</center>

Os custos de cada TPF podem ser obtidos seguindo o *script* a seguir. Esses serão os custos aproximados caso o TPF seja resgatado na presente data.

```python
nom = tesouro_direto.nomeclatura_titulos()
for tpf in carteira.titulos:
    tipo_titulo = tpf["Tipo"]
    investimento = tpf["Quantidade"]
    data_investimento = tpf["Data Investimento"]
    vencimento = tpf["Vencimento"]
    venc = vencimento.split("-")[0]
    nome_titulo = [nom[tipo_titulo].upper() + "_" + venc + "_" + data_investimento]
    print(nome_titulo[0])
    mtm_titulo = carteira_tesouro_direto[nome_titulo].dropna()
    custos, detalhamento_custos = get_custos( mtm_titulo, custo_b3=True)
    print()
```

O IOF segue uma tabela regressiva de taxa cobrada e é zerado após 30 dias. Já o imposto de renda diminui após dois anos onde atinge o valor mínimo de 15%.
As taxas da B3 são cobradas em Janeiro e Julho de cada ano sobre o valor investido e proporcionais ao tempo investido. Tesouro Selic tem isenção para investimentos abaixo de R$ 10.000,00. Maiores detalhes consultar site da B3.

Estou considerando 0% a taxa da corretora uma vez que a maior parte das corretoras não tem cobrado esse valor.

É possível obter as movimentações de vendas ou resgates (recompras) de TPFs:

```python
movimentacao_tpf = movimentacoes_titulos_publicos("venda", proxies=proxies)

#Maiores Movimentações nos últimos 10 dias:
maiores_movimentacoes = movimentacao_pivot.iloc[-10:].T.dropna()
maiores_movimentacoes["Soma"] = maiores_movimentacoes.sum(axis=1)
maiores_movimentacoes = maiores_movimentacoes.sort_values("Soma", ascending=False)
print(maiores_movimentacoes)

#destaque para os 3 maiores movimentos de venda
tres_maiores = maiores_movimentacoes.index[:3].tolist()
maiores = maiores_movimentacoes.drop(["Soma"], axis=1).T

fig = plt.gcf()
fig.set_size_inches(15, 7, forward = False)
plt.rcParams.update({'font.size': 22})

for tit in maiores.drop(tres_maiores, axis=1).columns:
    plt.plot(maiores[tit], color="gray", alpha=0.35, label='')
for tit in maiores[tres_maiores].columns:
    plt.plot(maiores[tit], lw=3, label=tit)
plt.legend(frameon=False, bbox_to_anchor=(0.95, 1.))
plt.suptitle("Movimentações de Venda de Títulos Públicos")
plt.box(False)
plt.grid(axis="y")
plt.ylabel('Quantidade',rotation=0,labelpad=-30,loc="top")
plt.xticks(rotation=15)
plt.show()
```

<center>
<img src="https://github.com/rafa-rod/tesouro_direto_br/blob/main/media/movimentacao_tpf.png" style="width:100%;"/>
</center>

Você pode estudar o comportamento de uma estratégia ou dos títulos em períodos históricos específicos. Para isso, basta informar a opção *taxa* à função *busca_tesouro_direto*, veja um exemplo de títulos ofertados entre 17/02/2016 e 01/01/2017:

```python
titulos_ofertados = tesouro_direto.busca_tesouro_direto(tipo="taxa", proxies=proxies).reset_index()

excluir = ["Juros Semestrais", "Renda+", "Educa+"]
titulos_ofertados_filtrado = titulos_ofertados[(titulos_ofertados["Data Base"]>="2016-02-17") &
                                   (titulos_ofertados["Data Base"]<"2017-01-01") &
                                   (~titulos_ofertados["Tipo Titulo"].str.contains("&".join(excluir)))].set_index(["Tipo Titulo",
                                                                                    "Data Vencimento"])
titulos_ofertados_filtrado.tail()
```

No exemplo acima, optei por excluir TPFs com Juros Semestrais e os novos Renda+ e Educa+ (sequer eram ofertados no período pesquisado). Filtrando por tipo de indexador para facilitar a identificação:

```python
inflacao = titulos_ofertados_filtrado.loc[["Tesouro IPCA+"], :].sort_values("Data Base", ascending=False)
display(inflacao[inflacao["Data Base"]=="2016-02-17"].sort_index(level=1, ascending=True))

prefixado = titulos_ofertados_filtrado.loc[["Tesouro Prefixado"], :].sort_values("Data Base", ascending=False)
display(prefixado[prefixado["Data Base"]=="2016-02-17"].sort_index(level=1, ascending=True))

selic = titulos_ofertados_filtrado.loc[["Tesouro Selic"], :].sort_values("Data Base", ascending=False)
display(selic[selic["Data Base"]=="2016-02-17"].sort_index(level=1, ascending=True))
```

A partir de um título específico que tenha identificado, pode-se repetir os procedimentos de elaboração de carteira exibido no início deste tutorial e calcular a rentabilidade dos títulos até o vencimento comparando com banchmark. Assim, você consegueria saber se a estratégia foi a que esperava (não necessariamente pode se repetir no futuro).
