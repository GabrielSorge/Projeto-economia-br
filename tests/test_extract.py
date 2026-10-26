import unittest
from datetime import date
from unittest.mock import Mock, patch

import requests

from src.extract import buscar_serie


class BuscarSerieTests(unittest.TestCase):
    @patch("src.extract.requests.get")
    def test_builds_request_and_returns_records(self, get):
        response = Mock()
        response.json.return_value = [{"data": "02/01/2024", "valor": "0.043739"}]
        get.return_value = response

        registros = buscar_serie(11, "01/01/2024", "03/01/2024")

        self.assertEqual(registros, [{"data": "02/01/2024", "valor": "0.043739"}])
        get.assert_called_once_with(
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados",
            params={
                "formato": "json",
                "dataInicial": "01/01/2024",
                "dataFinal": "03/01/2024",
            },
            timeout=30,
        )
        response.raise_for_status.assert_called_once_with()

    @patch("src.extract.requests.get")
    def test_splits_intervals_longer_than_ten_years(self, get):
        first_response = Mock()
        first_response.json.return_value = [{"data": "01/01/2010", "valor": "1"}]
        second_response = Mock()
        second_response.json.return_value = [{"data": "01/01/2020", "valor": "2"}]
        get.side_effect = [first_response, second_response]

        registros = buscar_serie(432, date(2010, 1, 1), date(2021, 1, 1))

        self.assertEqual([registro["valor"] for registro in registros], ["1", "2"])
        self.assertEqual(get.call_count, 2)
        self.assertEqual(
            [chamada.kwargs["params"] for chamada in get.call_args_list],
            [
                {
                    "formato": "json",
                    "dataInicial": "01/01/2010",
                    "dataFinal": "31/12/2019",
                },
                {
                    "formato": "json",
                    "dataInicial": "01/01/2020",
                    "dataFinal": "01/01/2021",
                },
            ],
        )

    @patch("src.extract.requests.get")
    def test_returns_empty_list_when_api_has_no_observations(self, get):
        response = Mock()
        response.json.return_value = []
        get.return_value = response

        self.assertEqual(buscar_serie("12", "01/01/2024", "03/01/2024"), [])

    @patch("src.extract.requests.get")
    def test_propagates_timeout(self, get):
        get.side_effect = requests.Timeout("request timed out")

        with self.assertRaises(requests.Timeout):
            buscar_serie(11, "01/01/2024", "03/01/2024")

    @patch("src.extract.requests.get")
    def test_propagates_http_errors(self, get):
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError("HTTP 500")
        get.return_value = response

        with self.assertRaises(requests.HTTPError):
            buscar_serie(11, "01/01/2024", "03/01/2024")

    def test_rejects_reversed_dates(self):
        with self.assertRaisesRegex(ValueError, "posterior"):
            buscar_serie(11, "02/01/2024", "01/01/2024")


if __name__ == "__main__":
    unittest.main()
