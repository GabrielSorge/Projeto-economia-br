import pandas as pd
import pytest

from src.transform import (
    criar_dataframe,
    limpar_serie,
    padronizar_periodicidade_mensal,
    transformar_series,
)


def test_creates_typed_sorted_dataframe_and_removes_invalid_and_duplicate_rows():
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

    assert list(resultado.columns) == ["codigo", "data", "valor"]
    assert resultado["codigo"].tolist() == ["11", "11"]
    assert resultado["data"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-01-03"),
    ]
    assert resultado["valor"].tolist() == [1.5, 3.5]
    assert pd.api.types.is_datetime64_any_dtype(resultado["data"])
    assert pd.api.types.is_float_dtype(resultado["valor"])


def test_combines_series_in_long_format_and_empty_input_has_schema():
    resultado = transformar_series(
        {
            11: [{"data": "02/01/2024", "valor": "2"}],
            "432": [{"data": "01/01/2024", "valor": "1"}],
        }
    )

    assert list(resultado.columns) == ["codigo", "data", "valor"]
    assert resultado["codigo"].tolist() == ["11", "432"]
    assert resultado["valor"].tolist() == [2.0, 1.0]

    vazio = transformar_series({})
    assert list(vazio.columns) == ["codigo", "data", "valor"]
    assert pd.api.types.is_datetime64_any_dtype(vazio["data"])
    assert pd.api.types.is_float_dtype(vazio["valor"])


def test_monthly_resampling_uses_mean_and_month_start():
    original = pd.DataFrame(
        {
            "codigo": ["11", "11", "11", "432"],
            "data": ["02/01/2024", "31/01/2024", "01/02/2024", "15/01/2024"],
            "valor": ["2", "4", "8", "10"],
        }
    )
    original_copia = original.copy(deep=True)

    resultado = padronizar_periodicidade_mensal(original)

    assert list(resultado.columns) == ["codigo", "data", "valor"]
    assert list(
        zip(resultado["codigo"], resultado["data"], resultado["valor"])
    ) == [
        ("11", pd.Timestamp("2024-01-01"), 3.0),
        ("11", pd.Timestamp("2024-02-01"), 8.0),
        ("432", pd.Timestamp("2024-01-01"), 10.0),
    ]
    pd.testing.assert_frame_equal(original, original_copia)


def test_monthly_resampling_does_not_create_empty_months():
    original = pd.DataFrame(
        {
            "codigo": ["11", "11"],
            "data": ["15/01/2024", "15/03/2024"],
            "valor": ["2", "6"],
        }
    )

    resultado = padronizar_periodicidade_mensal(original)

    assert resultado["data"].tolist() == [
        pd.Timestamp("2024-01-01"),
        pd.Timestamp("2024-03-01"),
    ]
    assert not resultado["valor"].isna().any()


def test_cleaning_does_not_modify_input():
    original = pd.DataFrame(
        {"codigo": [11], "data": ["01/01/2024"], "valor": ["1.25"]}
    )
    original_copia = original.copy(deep=True)

    limpar_serie(original)

    pd.testing.assert_frame_equal(original, original_copia)


def test_rejects_missing_columns_and_empty_code():
    with pytest.raises(ValueError, match="colunas"):
        limpar_serie(pd.DataFrame({"data": [], "valor": []}))
    with pytest.raises(ValueError, match="código"):
        criar_dataframe([], " ")
