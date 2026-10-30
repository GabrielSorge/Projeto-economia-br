from collections.abc import Iterator
import os
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection


INFLACAO_12M_ESPERADA = 12.6825030132
JURO_REAL_ESPERADO = -2.3805852208


@pytest.fixture
def conexao_postgres() -> Iterator[Connection]:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Defina TEST_DATABASE_URL para executar o teste PostgreSQL.")

    engine = create_engine(url)
    raiz = Path(__file__).resolve().parents[1]
    try:
        with engine.connect() as conexao:
            transacao = conexao.begin()
            try:
                for arquivo in ("01_create_tables.sql", "02_views.sql"):
                    sql = (raiz / "sql" / arquivo).read_text(encoding="utf-8")
                    conexao.exec_driver_sql(sql)

                conexao.execute(
                    text(
                        """
                        INSERT INTO series_catalogo (codigo, descricao)
                        VALUES (:codigo, :descricao)
                        """
                    ),
                    [
                        {"codigo": 432, "descricao": "Meta Selic sintética"},
                        {"codigo": 433, "descricao": "IPCA sintético"},
                    ],
                )

                valores_ipca = [
                    {"codigo": 433, "data": date(2024, mes, 1), "valor": 1.0}
                    for mes in range(1, 13)
                ]
                valores_selic = [
                    {"codigo": 432, "data": date(2024, mes, 15), "valor": 9.0}
                    for mes in range(1, 12)
                ]
                valores_selic.extend(
                    [
                        {"codigo": 432, "data": date(2024, 12, 15), "valor": 9.0},
                        {"codigo": 432, "data": date(2024, 12, 31), "valor": 10.0},
                    ]
                )
                conexao.execute(
                    text(
                        """
                        INSERT INTO series_valores (codigo, data, valor)
                        VALUES (:codigo, :data, :valor)
                        """
                    ),
                    valores_ipca + valores_selic,
                )
                yield conexao
            finally:
                transacao.rollback()
    finally:
        engine.dispose()


def test_views_calculam_ipca_12_meses_e_juro_real(conexao_postgres: Connection):
    ipca = conexao_postgres.execute(
        text(
            """
            SELECT data, inflacao_12_meses_pct
            FROM vw_ipca_12_meses
            WHERE data = DATE '2024-12-01'
            """
        )
    ).mappings().one()
    juro = conexao_postgres.execute(
        text(
            """
            SELECT selic_anual_pct, inflacao_12_meses_pct, juro_real_pct
            FROM vw_juro_real
            WHERE data = DATE '2024-12-01'
            """
        )
    ).mappings().one()

    assert ipca["inflacao_12_meses_pct"] == pytest.approx(
        INFLACAO_12M_ESPERADA, abs=1e-9
    )
    assert juro["selic_anual_pct"] == pytest.approx(10.0)
    assert juro["inflacao_12_meses_pct"] == pytest.approx(
        INFLACAO_12M_ESPERADA, abs=1e-9
    )
    assert juro["juro_real_pct"] == pytest.approx(
        JURO_REAL_ESPERADO, abs=1e-9
    )
