from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd


COLUNAS = ["codigo", "data", "valor"]


def criar_dataframe(
    registros: Iterable[Mapping[str, object]], codigo: int | str
) -> pd.DataFrame:
    """Converte os registros JSON de uma série para o esquema longo."""
    codigo_texto = str(codigo).strip()
    if not codigo_texto:
        raise ValueError("O código da série não pode ser vazio.")

    dados = pd.DataFrame.from_records(registros)
    if dados.empty and not {"data", "valor"}.issubset(dados.columns):
        dados = pd.DataFrame(columns=["data", "valor"])
    elif not {"data", "valor"}.issubset(dados.columns):
        raise ValueError("Os registros devem conter as colunas 'data' e 'valor'.")

    dados = dados.loc[:, ["data", "valor"]].copy()
    dados.insert(0, "codigo", codigo_texto)
    return limpar_serie(dados)


def limpar_serie(df: pd.DataFrame) -> pd.DataFrame:
    """Tipa, limpa, remove duplicatas e ordena uma série sem alterar a entrada."""
    if not set(COLUNAS).issubset(df.columns):
        raise ValueError(
            "O DataFrame deve conter as colunas 'codigo', 'data' e 'valor'."
        )

    dados = df.loc[:, COLUNAS].copy()
    dados["codigo"] = dados["codigo"].astype("string").str.strip()
    dados["data"] = pd.to_datetime(
        dados["data"], format="%d/%m/%Y", errors="coerce"
    )
    valores = dados["valor"].astype("string").str.replace(",", ".", regex=False)
    dados["valor"] = pd.to_numeric(valores, errors="coerce").astype("float64")

    validos = (
        dados["codigo"].notna()
        & dados["codigo"].ne("")
        & dados["data"].notna()
        & dados["valor"].notna()
        & np.isfinite(dados["valor"])
    )
    dados = dados.loc[validos].copy()
    dados = dados.drop_duplicates(subset=["codigo", "data"], keep="first")
    return dados.sort_values(["codigo", "data"], kind="stable").reset_index(drop=True)


def transformar_series(
    dados_por_codigo: Mapping[int | str, Iterable[Mapping[str, object]]],
) -> pd.DataFrame:
    """Combina várias respostas JSON em um único DataFrame no formato longo."""
    series = [
        criar_dataframe(registros, codigo)
        for codigo, registros in dados_por_codigo.items()
    ]
    if not series:
        return pd.DataFrame(
            {
                "codigo": pd.Series(dtype="string"),
                "data": pd.Series(dtype="datetime64[ns]"),
                "valor": pd.Series(dtype="float64"),
            },
            columns=COLUNAS,
        )
    return limpar_serie(pd.concat(series, ignore_index=True))


def padronizar_periodicidade_mensal(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega cada série pela média mensal e marca a data no início do mês."""
    dados = limpar_serie(df)
    if dados.empty:
        return dados

    mensal = (
        dados.groupby("codigo")
        .resample("MS", on="data")["valor"]
        .mean()
        .reset_index()
        .dropna(subset=["valor"])
    )
    return mensal.loc[:, COLUNAS].sort_values(
        ["codigo", "data"], kind="stable"
    ).reset_index(drop=True)