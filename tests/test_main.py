import unittest
from datetime import date
from unittest.mock import call, patch

from src.main import executar_pipeline


class ExecutarPipelineTests(unittest.TestCase):
    @patch("src.main.carregar_valores", return_value=2)
    @patch("src.main.criar_dataframe", return_value="dataframe")
    @patch("src.main.buscar_serie", return_value=[{"data": "02/01/2024", "valor": "1"}])
    @patch("src.main.obter_ultima_data")
    @patch("src.main.criar_engine")
    def test_uses_latest_date_as_incremental_start_and_loads_each_series(
        self, criar_engine, obter_ultima_data, buscar_serie, criar_dataframe, carregar
    ):
        engine = criar_engine.return_value
        obter_ultima_data.side_effect = [date(2024, 1, 2), None]

        executar_pipeline(
            (11, 12), date(2020, 1, 1), data_final=date(2024, 1, 3)
        )

        self.assertEqual(
            obter_ultima_data.call_args_list,
            [call(11, engine), call(12, engine)],
        )
        self.assertEqual(
            buscar_serie.call_args_list,
            [
                call(11, date(2024, 1, 2), date(2024, 1, 3)),
                call(12, date(2020, 1, 1), date(2024, 1, 3)),
            ],
        )
        self.assertEqual(criar_dataframe.call_count, 2)
        self.assertEqual(carregar.call_count, 2)
        engine.dispose.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
