# Extração de séries do SGS/BCB

O módulo [`src/extract.py`](src/extract.py) consulta as séries temporais do
Banco Central do Brasil pela API SGS.

```python
from src.extract import buscar_serie

registros = buscar_serie(11, "01/01/2020", "31/12/2025")
print(registros[0])  # {"data": "02/01/2020", "valor": "0.017089"}

codigos = (432, 11, 12, 433, 1)
dados_por_serie = {
    codigo: buscar_serie(codigo, "01/01/2020", "31/12/2025")
    for codigo in codigos
}
```

O código da série muda no caminho `bcdata.sgs.{codigo}`. As datas são enviadas
nos parâmetros `dataInicial` e `dataFinal`, em `dd/MM/aaaa`, junto com
`formato=json`. O intervalo informado é inclusivo. Cada registro é devolvido
como um dicionário com os campos textuais `data` e `valor`; uma lista vazia
significa que a API não encontrou observações para aquele intervalo.

A função aplica timeout de 30 segundos, propaga erros HTTP/rede e rejeita
respostas JSON fora do formato esperado. Uma consulta de mais de dez anos
retornou HTTP 406 no teste do endpoint; para acomodar esse limite, intervalos
longos são consultados em blocos consecutivos de até dez anos.

Instale a dependência com `pip install -r requirements.txt` e rode os testes
com `python -m unittest discover -s tests`.

## Transformação das séries

O módulo [`src/transform.py`](src/transform.py) converte as respostas JSON para
DataFrames independentes, com as colunas `codigo`, `data` e `valor`. As datas
são convertidas para `datetime`, os valores para `float`, linhas sem dados
válidos são removidas e a saída é ordenada por código e data. Duplicatas da
mesma série e data mantêm a primeira observação recebida.

```python
from src.transform import padronizar_periodicidade_mensal, transformar_series

dados = transformar_series(dados_por_serie)
dados_mensais = padronizar_periodicidade_mensal(dados)
```

`transformar_series` combina as respostas em formato longo. Para comparar
séries diárias com mensais, `padronizar_periodicidade_mensal` calcula a média
dos valores de cada mês e usa o primeiro dia do mês como data. As funções
recebem e devolvem DataFrames sem modificar os dados de entrada.
