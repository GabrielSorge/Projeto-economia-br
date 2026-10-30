import unittest
from datetime import date
from unittest.mock import MagicMock

import pandas as pd
from sqlalchemy import create_engine

from src.load import (
    carregar_valores,
    obter_ultima_data,
    testar_conexao as executar_teste_conexao,
)


class TestarConexaoTests(unittest.TestCase):
    def test_runs_simple_query(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        try:
            self.assertEqual(executar_teste_conexao(engine), 1)
        finally:
            engine.dispose()


class CarregarValoresTests(unittest.TestCase):
    def setUp(self):
        self.engine = MagicMock()
        self.connection = self.engine.begin.return_value.__enter__.return_value

    def test_upserts_rows_and_registers_catalog(self):
        dados = pd.DataFrame(
            {
                "codigo": ["11", "11"],
                "data": [pd.Timestamp("2024-01-02"), pd.Timestamp("2024-01-03")],
                "valor": [0.1, 0.2],
            }
        )

        carregados = carregar_valores(
            dados, 11, self.engine, descricao="Taxa de teste"
        )

        self.assertEqual(carregados, 2)
        self.engine.begin.assert_called_once_with()
        chamadas = self.connection.execute.call_args_list
        self.assertEqual(len(chamadas), 2)
        self.assertIn(
            "DO UPDATE SET descricao = EXCLUDED.descricao",
            str(chamadas[0].args[0]),
        )
        self.assertEqual(
            chamadas[0].args[1], {"codigo": 11, "descricao": "Taxa de teste"}
        )
        self.assertIn(
            "DO UPDATE SET valor = EXCLUDED.valor", str(chamadas[1].args[0])
        )
        self.assertEqual(
            chamadas[1].args[1],
            [
                {"codigo": 11, "data": date(2024, 1, 2), "valor": 0.1},
                {"codigo": 11, "data": date(2024, 1, 3), "valor": 0.2},
            ],
        )

    def test_empty_data_still_registers_series(self):
        dados = pd.DataFrame(
            {
                "codigo": pd.Series(dtype="string"),
                "data": pd.Series(dtype="datetime64[ns]"),
                "valor": pd.Series(dtype="float64"),
            }
        )

        self.assertEqual(carregar_valores(dados, 11, self.engine), 0)
        self.connection.execute.assert_called_once()
        self.assertEqual(
            self.connection.execute.call_args.args[1],
            {
                "codigo": 11,
                "descricao": "Taxa de juros - Selic (% a.d.)",
            },
        )

    def test_rejects_rows_for_another_series(self):
        dados = pd.DataFrame(
            {
                "codigo": ["12"],
                "data": [pd.Timestamp("2024-01-02")],
                "valor": [0.1],
            }
        )

        with self.assertRaisesRegex(ValueError, "código informado"):
            carregar_valores(dados, 11, self.engine)

        self.engine.begin.assert_not_called()


class ObterUltimaDataTests(unittest.TestCase):
    def test_returns_latest_date(self):
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value.scalar.return_value = date(
            2024, 1, 2
        )

        self.assertEqual(obter_ultima_data(11, engine), date(2024, 1, 2))
        engine.connect.return_value.__enter__.return_value.scalar.assert_called_once()

    def test_returns_none_for_series_without_values(self):
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value.scalar.return_value = None

        self.assertIsNone(obter_ultima_data(11, engine))


if __name__ == "__main__":
    unittest.main()
