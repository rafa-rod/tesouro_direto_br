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
- visualizar, de forma gráfica, a evolução do valor de mercado e do retorno;
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

Notei que algumas corretoras mostraram a rentabilidade da carteira de forma equivocada. Algumas mostram apenas de um título, não da carteira.

## Examplos

Importe a biblioteca e insira titulos publicos a uma carteira vazia:

```python
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
carteira_tesouro_direto = pd.DataFrame()
for tpf in carteira.titulos:
	tipo_titulo = tpf["Tipo"]
	quantidade = tpf["Quantidade"]
	data_investimento = tpf["Data Investimento"]
	vencimento = tpf["Vencimento"]

	mtm_completo_titulo, mtm_titulo = tesouro_direto.calcula_mtm_titulo(tipo_titulo, quantidade, data_investimento, vencimento)

	carteira_tesouro_direto = pd.concat([carteira_tesouro_direto, mtm_titulo], axis=1)
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
import numpy as np

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

print(rentabilidades.T)
```

A análise melhora se você comparar com um *benchmark* como o CDI:

```python
import matplotlib.pyplot as plt
import comparar_fundos_br as comp

cdi, cdi_acumulado = comp.get_benchmark(str(retorno_carteira.index[0]).split(" ")[0], 
                                        str(retorno_carteira.index[-1]).split(" ")[0], 
                                        benchmark = "cdi")
retorno_cdi = (cdi_acumulado-1)*100

plt.figure(figsize=(17,5))
plt.title("Rentabilidade da Carteira")
plt.plot(retorno_carteira*100)
plt.plot(retorno_cdi, color="red", linestyle="--", lw=1)
plt.legend(["Carteira", "CDI"], frameon=False, loc="center right")
plt.show()
```

Se precisar plotar cada TPF de forma individual e ver os custos de cada um:

```python
carteira_tesouro_direto = pd.DataFrame()
for tpf in carteira.titulos:
    tipo_titulo = tpf["Tipo"]
    quantidade = tpf["Quantidade"]
    data_investimento = tpf["Data Investimento"]
    vencimento = tpf["Vencimento"]

    mtm_completo_titulo, mtm_titulo = tesouro_direto.calcula_mtm_titulo(tipo_titulo, quantidade, data_investimento, vencimento)

    tesouro_direto.plot_mtm(mtm_completo_titulo, data_investimento, investimento)

    tesouro_direto.plot_taxas(tipo_titulo, data_investimento, vencimento)

    custos, detalhamento_custos = tesouro_direto.get_custos( mtm_titulo, investimento, data_investimento, vencimento )
```

O *script* anterior mostra os custos totais se você permanecer até o vencimento, caso deseje simular desfazer hoje do título, altere a data de vencimento:

```python
carteira_tesouro_direto = pd.DataFrame()
for tpf in carteira.titulos:
    tipo_titulo = tpf["Tipo"]
    quantidade = tpf["Quantidade"]
    data_investimento = tpf["Data Investimento"]
    vencimento = tpf["Vencimento"]

    mtm_completo_titulo, mtm_titulo = tesouro_direto.calcula_mtm_titulo(tipo_titulo, quantidade, data_investimento, vencimento)

    tesouro_direto.plot_mtm(mtm_completo_titulo, data_investimento, investimento)

    tesouro_direto.plot_taxas(tipo_titulo, data_investimento, vencimento)

    custos, detalhamento_custos = tesouro_direto.get_custos( mtm_titulo, investimento, data_investimento, "2023-02-08" )
  
```

O IOF segue uma tabela regressiva de taxa cobrada e é zerado após 30 dias. Já o imposto de renda diminui após dois anos onde atinge o valor mínimo de 15%.
As taxas da B3 são cobradas em Janeiro e Julho de cada ano sobre o valor investido.

Estou considerando 0% a taxa da corretora.
