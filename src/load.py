from datetime import date

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.config import criar_engine
from src.transform import limpar_serie


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
    with engine_local.begin() as conexao:
        conexao.execute(
            text(
                """
                INSERT INTO series_catalogo (codigo, descricao)
                VALUES (:codigo, :descricao)
                ON CONFLICT (codigo) DO NOTHING
                """
            ),
            {
                "codigo": codigo,
                "descricao": descricao or f"Série SGS {codigo}",
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