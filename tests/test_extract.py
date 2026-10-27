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
    def test_splits_long_intervals_into_one_year_requests(self, get):
        responses = []
        for year in range(2010, 2022):
            response = Mock()
            response.json.return_value = [{"data": f"01/01/{year}", "valor": str(year)}]
            responses.append(response)
        get.side_effect = responses

        registros = buscar_serie(432, date(2010, 1, 1), date(2021, 1, 1))

        self.assertEqual(len(registros), 12)
        self.assertEqual(get.call_count, 12)
        params = [chamada.kwargs["params"] for chamada in get.call_args_list]
        self.assertEqual(params[0]["dataInicial"], "01/01/2010")
        self.assertEqual(params[0]["dataFinal"], "31/12/2010")
        self.assertEqual(params[-1]["dataInicial"], "01/01/2021")
        self.assertEqual(params[-1]["dataFinal"], "01/01/2021")

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
        self.assertEqual(get.call_count, 3)

    @patch("src.extract.sleep")
    @patch("src.extract.requests.get")
    def test_retries_temporary_http_error(self, get, sleep_retry):
        unavailable = Mock()
        unavailable.status_code = 502
        unavailable.raise_for_status.side_effect = requests.HTTPError(
            "HTTP 502", response=unavailable
        )
        successful = Mock()
        successful.json.return_value = [{"data": "02/01/2024", "valor": "1"}]
        get.side_effect = [unavailable, successful]

        registros = buscar_serie(11, "01/01/2024", "03/01/2024")

        self.assertEqual(registros, [{"data": "02/01/2024", "valor": "1"}])
        self.assertEqual(get.call_count, 2)
        sleep_retry.assert_called_once_with(1)

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
