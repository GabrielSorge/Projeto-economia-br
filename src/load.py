from datetime import date

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.config import criar_engine
from src.transform import limpar_serie


DESCRICOES_SERIES: dict[int, dict[str, str]] = {
    1: {
        "descricao": "Taxa de câmbio - Livre - Dólar americano (venda) - diário",
        "unidade": "u.m.c./US$",
    },
    11: {
        "descricao": "Taxa de juros - Selic",
        "unidade": "% a.d.",
    },
    12: {
        "descricao": "Taxa de juros - CDI",
        "unidade": "% a.d.",
    },
    432: {
        "descricao": "Taxa de juros - Meta Selic definida pelo Copom",
        "unidade": "% a.a.",
    },
    433: {
        "descricao": "Índice nacional de preços ao consumidor-amplo (IPCA)",
        "unidade": "Var. % mensal",
    },
}


def testar_conexao(engine: Engine | None = None) -> int:
    """Executa uma consulta simples e retorna o resultado."""
    engine_local = engine if engine is not None else criar_engine()
    with engine_local.connect() as conexao:
        resultado = conexao.scalar(text("SELECT 1"))
    if resultado is None:
        raise RuntimeError("A consulta de teste não retornou resultado.")
    return int(resultado)


def obter_ultima_data(codigo: int, engine: Engine | None = None) -> date | None:
    """Retorna a data mais recente já carregada para a série."""
    engine_local = engine if engine is not None else criar_engine()
    with engine_local.connect() as conexao:
        resultado = conexao.scalar(
            text("SELECT MAX(data) FROM series_valores WHERE codigo = :codigo"),
            {"codigo": codigo},
        )
    if resultado is None:
        return None
    return resultado.date() if isinstance(resultado, pd.Timestamp) else resultado


def carregar_valores(
    df: pd.DataFrame,
    codigo: int,
    engine: Engine | None = None,
    descricao: str | None = None,
) -> int:
    """Insere ou atualiza observações, de forma transacional e idempotente."""
    dados = limpar_serie(df)
    if not dados.empty and set(dados["codigo"].astype(int)) != {codigo}:
        raise ValueError("O DataFrame deve conter apenas o código informado.")

    registros = [
        {
            "codigo": codigo,
            "data": linha.data.date(),
            "valor": float(linha.valor),
        }
        for linha in dados.itertuples(index=False)
    ]
    engine_local = engine if engine is not None else criar_engine()
    serie = DESCRICOES_SERIES.get(codigo)
    descricao_catalogo = descricao or (
        f"{serie['descricao']} ({serie['unidade']})"
        if serie is not None
        else f"Série SGS {codigo}"
    )
    with engine_local.begin() as conexao:
        conexao.execute(
            text(
                """
                INSERT INTO series_catalogo (codigo, descricao)
                VALUES (:codigo, :descricao)
                ON CONFLICT (codigo)
                DO UPDATE SET descricao = EXCLUDED.descricao
                """
            ),
            {
                "codigo": codigo,
                "descricao": descricao_catalogo,
            },
        )
        if registros:
            conexao.execute(
                text(
                    """
                    INSERT INTO series_valores (codigo, data, valor)
                    VALUES (:codigo, :data, :valor)
                    ON CONFLICT (codigo, data)
                    DO UPDATE SET valor = EXCLUDED.valor
                    """
                ),
                registros,
            )
    return len(registros)