import unittest
from unittest.mock import MagicMock, Mock, call, patch

from sqlalchemy.exc import ProgrammingError

from src.text_to_sql import (
    ALLOWED_VIEWS,
    ConsultaInseguraError,
    executar_sql_leitura,
    perguntar,
    validar_sql,
)


PERGUNTAS_FIXAS = (
    (
        "Qual foi o juro real medio em 2023?",
        "SELECT AVG(juro_real_pct) AS media_pct FROM vw_juro_real "
        "WHERE data >= DATE '2023-01-01' AND data < DATE '2024-01-01'",
        "vw_juro_real",
    ),
    (
        "Qual foi a maior inflacao acumulada em 12 meses?",
        "SELECT MAX(inflacao_12_meses_pct) AS maxima_pct "
        "FROM vw_ipca_12_meses",
        "vw_ipca_12_meses",
    ),
    (
        "Qual foi o cambio medio em 2023?",
        "SELECT AVG(cambio_medio_brl_por_usd) AS cambio_medio_brl_usd "
        "FROM vw_analise_mensal WHERE data >= DATE '2023-01-01' "
        "AND data < DATE '2024-01-01'",
        "vw_analise_mensal",
    ),
)


class ValidarSQLTests(unittest.TestCase):
    def test_fixed_business_questions_have_valid_view_queries(self):
        for pergunta, sql, view in PERGUNTAS_FIXAS:
            with self.subTest(pergunta=pergunta):
                validado = validar_sql(sql)
                self.assertIn(view, ALLOWED_VIEWS)
                self.assertIn(view, validado)
                self.assertIn("LIMIT 100", validado)

    def test_allows_select_and_cte_using_only_analysis_views(self):
        query = validar_sql(
            "WITH juros AS (SELECT juro_real_pct FROM vw_juro_real) "
            "SELECT AVG(juro_real_pct) FROM juros"
        )

        self.assertIn("WITH juros AS", query)
        self.assertIn("LIMIT 100", query)

    def test_caps_requested_limit(self):
        query = validar_sql("SELECT data FROM vw_juro_real LIMIT 10000")

        self.assertTrue(query.endswith("LIMIT 100"))

    def test_rejects_non_selects_and_multiple_statements(self):
        proibidas = (
            "DELETE FROM series_valores",
            "SELECT 1; DROP TABLE series_valores",
            "WITH apagado AS (DELETE FROM series_valores RETURNING *) "
            "SELECT * FROM apagado",
        )
        for sql in proibidas:
            with self.subTest(sql=sql), self.assertRaises(ConsultaInseguraError):
                validar_sql(sql)

    def test_rejects_unapproved_relations_and_functions(self):
        proibidas = (
            "SELECT * FROM series_valores",
            "SELECT * FROM information_schema.tables",
            "SELECT * FROM outro_esquema.vw_juro_real",
            "SELECT pg_sleep(10) FROM vw_juro_real",
        )
        for sql in proibidas:
            with self.subTest(sql=sql), self.assertRaises(ConsultaInseguraError):
                validar_sql(sql)

    def test_rejects_non_literal_and_zero_limits(self):
        for sql in (
            "SELECT data FROM vw_juro_real LIMIT (SELECT 1)",
            "SELECT data FROM vw_juro_real LIMIT 0",
        ):
            with self.subTest(sql=sql), self.assertRaises(ConsultaInseguraError):
                validar_sql(sql)


class ExecucaoSomenteLeituraTests(unittest.TestCase):
    def test_starts_read_only_transaction_with_timeout(self):
        engine = MagicMock()
        connection = engine.connect.return_value.__enter__.return_value
        rows = [{"media_pct": 5.2}]
        connection.execute.return_value.mappings.return_value = rows

        resultado = executar_sql_leitura(
            "SELECT AVG(juro_real_pct) AS media_pct FROM vw_juro_real",
            engine,
        )

        self.assertEqual(resultado, rows)
        self.assertEqual(
            connection.exec_driver_sql.call_args_list,
            [
                call("SET TRANSACTION READ ONLY"),
                call("SET LOCAL statement_timeout = '5000ms'"),
            ],
        )


class PerguntarTests(unittest.TestCase):
    @patch("src.text_to_sql._gemini_text")
    @patch("src.text_to_sql.executar_sql_leitura", return_value=[{"media_pct": 5.2}])
    @patch("src.text_to_sql.gerar_sql")
    def test_generates_query_executes_it_and_explains_results(
        self, gerar_sql, executar, gemini
    ):
        gerar_sql.return_value = (
            "SELECT AVG(juro_real_pct) AS media_pct FROM vw_juro_real"
        )
        gemini.return_value = "A media foi de 5,2% ao ano."
        engine = Mock()

        resultado = perguntar("Qual foi o juro real medio?", engine, "api-key")

        self.assertEqual(resultado.resposta, gemini.return_value)
        self.assertEqual(resultado.linhas, [{"media_pct": 5.2}])
        executar.assert_called_once()
        self.assertEqual(gemini.call_count, 1)
        engine.dispose.assert_not_called()

    @patch("src.text_to_sql._gemini_text")
    @patch("src.text_to_sql.executar_sql_leitura")
    @patch("src.text_to_sql.gerar_sql")
    def test_retries_once_when_database_rejects_generated_sql(
        self, gerar_sql, executar, gemini
    ):
        gerar_sql.side_effect = [
            "SELECT coluna_errada FROM vw_juro_real",
            "SELECT AVG(juro_real_pct) FROM vw_juro_real",
        ]
        executar.side_effect = [
            ProgrammingError("query", {}, Exception("column does not exist")),
            [{"avg": 5.2}],
        ]
        gemini.return_value = "A media foi de 5,2%."

        resultado = perguntar("Qual a media?", Mock(), "api-key")

        self.assertEqual(len(resultado.linhas), 1)
        self.assertEqual(gerar_sql.call_count, 2)
        self.assertIn("column does not exist", gerar_sql.call_args.kwargs["erro_anterior"])
        self.assertEqual(executar.call_count, 2)

    def test_requires_api_key_and_rejects_empty_question(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            with self.assertRaisesRegex(ValueError, "pergunta"):
                perguntar("  ", api_key="")
            with self.assertRaisesRegex(RuntimeError, "GEMINI_API_KEY"):
                perguntar("Pergunta válida", api_key="")


if __name__ == "__main__":
    unittest.main()
