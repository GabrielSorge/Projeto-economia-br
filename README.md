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

A função aplica timeout de 30 segundos, tenta novamente falhas temporárias do
endpoint e rejeita respostas JSON fora do formato esperado. Intervalos longos
são consultados em blocos anuais.

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

## Banco de dados PostgreSQL

Instale as dependências do projeto:

```powershell
python -m pip install -r requirements.txt
```

Configure `.env` na raiz do projeto (use `.env.example` como referência) com
`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` e
`POSTGRES_PORT`. O arquivo `.env` não é versionado; mantenha nele as credenciais
locais e use uma senha própria.

Para subir somente o banco:

```powershell
docker compose up -d postgres
```

O serviço persiste os dados no volume `postgres_data` e executa os scripts SQL
de `sql/` automaticamente na primeira inicialização do volume. Para verificar a
conexão Python e executar `SELECT 1`:

```powershell
python -m src.main
```

Os scripts de inicialização só são executados quando o volume de dados é criado.
Alterações posteriores no SQL não recriam as tabelas automaticamente.

## Pipeline incremental

O pipeline extrai as séries configuradas em `SERIES_CODES` (padrão: `432,11,12,433,1`),
iniciando em `DATA_INICIAL` (padrão: `01/01/2020`) quando ainda não há dados. Para
cada série, ele consulta a data máxima carregada e busca novamente a partir dela;
o upsert atualiza observações existentes e evita duplicatas. Ajuste essas
variáveis no `.env` se necessário.

Para construir a imagem e executar o banco e o pipeline em ordem:

```powershell
docker compose up --build
```

O serviço `pipeline` aguarda o healthcheck do PostgreSQL e termina após a carga.
Executar `docker compose up` novamente processa as séries de forma incremental.
Os logs informam as observações carregadas por série.

## Análises

As views `vw_ipca_12_meses`, `vw_juro_real` e `vw_analise_mensal` são definidas
em `sql/02_views.sql`. A inflação acumulada compõe as variações mensais da série
SGS 433; o juro real usa a última Selic anual (SGS 12) do mês e a inflação
acumulada, ambos como percentuais. A view mensal também calcula a média mensal
do câmbio (SGS 1) em BRL por USD e sua variação percentual.

Abra `notebooks/analise.ipynb` e execute as células em ordem. O notebook cria ou
atualiza as views antes de consultá-las, compara o IPCA acumulado de dezembro de
2023 com os 4,62% publicados pelo IBGE, calcula a correlação entre a variação
mensal do câmbio e o IPCA mensal, cria gráficos com unidades e produz achados
descritivos. A correlação é associação estatística, não evidência de causalidade.
É necessário primeiro carregar as séries no PostgreSQL; sem dados, o notebook
informa a ausência de observações e ainda executa todas as células.
