from calendar import monthrange
from datetime import date, datetime, timedelta
import logging
from time import sleep
from typing import Dict, List, Union

import requests


API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
TIMEOUT_SECONDS = 30
MAX_REQUEST_ATTEMPTS = 3
RETRYABLE_STATUS_CODES = {429, 502, 503, 504}
MAX_QUERY_YEARS = 1
DateInput = Union[str, date, datetime]
logger = logging.getLogger(__name__)


def _parse_date(value: DateInput, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field_name} deve ser uma data ou texto no formato dd/MM/aaaa.")

    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError as exc:
        raise ValueError(
            f"{field_name} deve estar no formato dd/MM/aaaa: {value!r}."
        ) from exc


def _add_years(value: date, years: int) -> date:
    target_year = value.year + years
    target_day = min(value.day, monthrange(target_year, value.month)[1])
    return value.replace(year=target_year, day=target_day)


def _fetch_block(codigo: str, data_inicial: date, data_final: date) -> List[Dict[str, str]]:
    for tentativa in range(MAX_REQUEST_ATTEMPTS):
        try:
            response = requests.get(
                API_URL.format(codigo=codigo),
                params={
                    "formato": "json",
                    "dataInicial": data_inicial.strftime("%d/%m/%Y"),
                    "dataFinal": data_final.strftime("%d/%m/%Y"),
                },
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            break
        except (requests.Timeout, requests.ConnectionError) as exc:
            if tentativa == MAX_REQUEST_ATTEMPTS - 1:
                raise
            logger.warning(
                "Falha temporária ao consultar série %s; nova tentativa %d/%d: %s",
                codigo,
                tentativa + 2,
                MAX_REQUEST_ATTEMPTS,
                exc,
            )
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if (
                status not in RETRYABLE_STATUS_CODES
                or tentativa == MAX_REQUEST_ATTEMPTS - 1
            ):
                raise
            logger.warning(
                "HTTP %s ao consultar série %s; nova tentativa %d/%d.",
                status,
                codigo,
                tentativa + 2,
                MAX_REQUEST_ATTEMPTS,
            )
        sleep(2**tentativa)

    try:
        registros = response.json()
    except ValueError as exc:
        raise ValueError(f"A API SGS retornou JSON inválido para a série {codigo}.") from exc

    if not isinstance(registros, list):
        raise ValueError(f"A resposta da série {codigo} não é uma lista JSON.")

    for indice, registro in enumerate(registros):
        if (
            not isinstance(registro, dict)
            or not isinstance(registro.get("data"), str)
            or not isinstance(registro.get("valor"), str)
        ):
            raise ValueError(
                f"Registro {indice} da série {codigo} não contém os campos "
                "'data' e 'valor' como texto."
            )

    return registros


def buscar_serie(
    codigo: Union[int, str],
    data_inicial: DateInput,
    data_final: DateInput,
) -> List[Dict[str, str]]:
    """Busca registros de uma série SGS, com datas inclusivas."""
    codigo_texto = str(codigo).strip()
    if not codigo_texto.isdigit():
        raise ValueError("O código SGS deve conter apenas dígitos.")

    inicio = _parse_date(data_inicial, "data_inicial")
    fim = _parse_date(data_final, "data_final")
    if inicio > fim:
        raise ValueError("data_inicial não pode ser posterior a data_final.")

    registros: List[Dict[str, str]] = []
    inicio_bloco = inicio

    while inicio_bloco <= fim:
        aniversario = _add_years(inicio_bloco, MAX_QUERY_YEARS)
        fim_bloco = min(fim, aniversario - timedelta(days=1))
        registros.extend(_fetch_block(codigo_texto, inicio_bloco, fim_bloco))
        inicio_bloco = fim_bloco + timedelta(days=1)

    return registros
