import unittest

import pandas as pd

from src.transform import (
    criar_dataframe,
    limpar_serie,
    padronizar_periodicidade_mensal,
    transformar_series,
)


class TransformTests(unittest.TestCase):
    def test_creates_typed_sorted_dataframe_and_removes_invalid_and_duplicate_rows(self):
        registros = [
            {"data": "03/01/2024", "valor": "3.5"},
            {"data": "01/01/2024", "valor": "1,5"},
            {"data": "01/01/2024", "valor": "99"},
            {"data": "data inválida", "valor": "2"},
            {"data": "04/01/2024", "valor": "não numérico"},
            {"data": "05/01/2024", "valor": None},
            {"data": None, "valor": "5"},
        ]

        resultado = criar_dataframe(registros, 11)

        self.assertEqual(list(resultado.columns), ["codigo", "data", "valor"])
        self.assertEqual(resultado["codigo"].tolist(), ["11", "11"])
        self.assertEqual(
            resultado["data"].tolist(),
            [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-03")],
        )
        self.assertEqual(resultado["valor"].tolist(), [1.5, 3.5])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(resultado["data"]))
        self.assertTrue(pd.api.types.is_float_dtype(resultado["valor"]))

    def test_combines_series_in_long_format_and_empty_input_has_schema(self):
        resultado = transformar_series(
            {
                11: [{"data": "02/01/2024", "valor": "2"}],
                "432": [{"data": "01/01/2024", "valor": "1"}],
            }
        )

        self.assertEqual(list(resultado.columns), ["codigo", "data", "valor"])
        self.assertEqual(resultado["codigo"].tolist(), ["11", "432"])
        self.assertEqual(resultado["valor"].tolist(), [2.0, 1.0])

        vazio = transformar_series({})
        self.assertEqual(list(vazio.columns), ["codigo", "data", "valor"])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(vazio["data"]))
        self.assertTrue(pd.api.types.is_float_dtype(vazio["valor"]))

    def test_monthly_resampling_uses_mean_and_month_start(self):
        original = pd.DataFrame(
            {
                "codigo": ["11", "11", "11", "432"],
                "data": ["02/01/2024", "31/01/2024", "01/02/2024", "15/01/2024"],
                "valor": ["2", "4", "8", "10"],
            }
        )
        original_copia = original.copy(deep=True)

        resultado = padronizar_periodicidade_mensal(original)

        self.assertEqual(list(resultado.columns), ["codigo", "data", "valor"])
        self.assertEqual(
            list(zip(resultado["codigo"], resultado["data"], resultado["valor"])),
            [
                ("11", pd.Timestamp("2024-01-01"), 3.0),
                ("11", pd.Timestamp("2024-02-01"), 8.0),
                ("432", pd.Timestamp("2024-01-01"), 10.0),
            ],
        )
        pd.testing.assert_frame_equal(original, original_copia)

    def test_monthly_resampling_does_not_create_empty_months(self):
        original = pd.DataFrame(
            {
                "codigo": ["11", "11"],
                "data": ["15/01/2024", "15/03/2024"],
                "valor": ["2", "6"],
            }
        )

        resultado = padronizar_periodicidade_mensal(original)

        self.assertEqual(
            resultado["data"].tolist(),
            [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-03-01")],
        )
        self.assertFalse(resultado["valor"].isna().any())

    def test_cleaning_does_not_modify_input(self):
        original = pd.DataFrame(
            {"codigo": [11], "data": ["01/01/2024"], "valor": ["1.25"]}
        )
        original_copia = original.copy(deep=True)

        limpar_serie(original)

        pd.testing.assert_frame_equal(original, original_copia)

    def test_rejects_missing_columns_and_empty_code(self):
        with self.assertRaisesRegex(ValueError, "colunas"):
            limpar_serie(pd.DataFrame({"data": [], "valor": []}))
        with self.assertRaisesRegex(ValueError, "código"):
            criar_dataframe([], " ")


if __name__ == "__main__":
    unittest.main()
