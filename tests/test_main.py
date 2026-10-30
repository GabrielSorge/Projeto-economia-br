import unittest
from datetime import date
from unittest.mock import call, patch

from src.main import executar_pipeline, main


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

        falhas = executar_pipeline(
            (11, 12), date(2020, 1, 1), data_final=date(2024, 1, 3)
        )

        self.assertEqual(falhas, 0)
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

    @patch("src.main.logger")
    @patch("src.main.carregar_valores", return_value=3)
    @patch("src.main.criar_dataframe", return_value="dataframe")
    @patch("src.main.buscar_serie")
    @patch("src.main.obter_ultima_data", return_value=None)
    @patch("src.main.criar_engine")
    def test_continues_after_series_failure_and_summarizes(
        self,
        criar_engine,
        obter_ultima_data,
        buscar_serie,
        criar_dataframe,
        carregar,
        logger,
    ):
        buscar_serie.side_effect = [
            RuntimeError("falha na API"),
            [{"data": "02/01/2024", "valor": "1"}],
        ]

        falhas = executar_pipeline(
            (11, 12), date(2020, 1, 1), data_final=date(2024, 1, 3)
        )

        self.assertEqual(falhas, 1)
        self.assertEqual(buscar_serie.call_count, 2)
        criar_dataframe.assert_called_once_with(
            [{"data": "02/01/2024", "valor": "1"}], 12
        )
        carregar.assert_called_once()
        logger.exception.assert_called_once_with(
            "Falha ao processar a série SGS %s.", 11
        )
        self.assertEqual(
            logger.info.call_args_list[-1].args,
            (
                "Resumo do pipeline: %d séries com sucesso, %d séries com falha, "
                "%d linhas carregadas.",
                1,
                1,
                3,
            ),
        )
        criar_engine.return_value.dispose.assert_called_once_with()

    @patch("src.main.executar_pipeline", return_value=1)
    def test_main_returns_nonzero_when_any_series_fails(self, executar):
        with patch.dict(
            "os.environ",
            {"SERIES_CODES": "11,12", "DATA_INICIAL": "01/01/2020"},
        ):
            codigo_saida = main()

        self.assertEqual(codigo_saida, 1)
        executar.assert_called_once_with((11, 12), date(2020, 1, 1))


if __name__ == "__main__":
    unittest.main()
