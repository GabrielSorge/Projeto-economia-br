import logging
import os
from datetime import date, datetime

from src.config import criar_engine
from src.extract import buscar_serie
from src.load import carregar_valores, obter_ultima_data
from src.transform import criar_dataframe


logger = logging.getLogger(__name__)
CODIGOS_PADRAO = (432, 11, 433, 1)


def executar_pipeline(
    codigos: tuple[int, ...] = CODIGOS_PADRAO,
    data_inicial: date = date(2020, 1, 1),
    data_final: date | None = None,
) -> int:
    """Processa as séries e retorna quantas falharam."""
    engine = criar_engine()
    fim = data_final or date.today()
    series_sucesso = 0
    series_falha = 0
    linhas_carregadas = 0
    try:
        for codigo in codigos:
            try:
                ultima_data = obter_ultima_data(codigo, engine)
                inicio = ultima_data or data_inicial
                if inicio > fim:
                    logger.info(
                        "Série SGS %s: já está atualizada até %s.",
                        codigo,
                        inicio.isoformat(),
                    )
                    series_sucesso += 1
                    continue

                registros = buscar_serie(codigo, inicio, fim)
                dados = criar_dataframe(registros, codigo)
                carregados = carregar_valores(dados, codigo, engine)
                linhas_carregadas += carregados
                series_sucesso += 1
                logger.info(
                    "Série SGS %s: %d observações processadas (%d recebidas).",
                    codigo,
                    carregados,
                    len(registros),
                )
            except Exception:
                series_falha += 1
                logger.exception("Falha ao processar a série SGS %s.", codigo)

        logger.info(
            "Resumo do pipeline: %d séries com sucesso, %d séries com falha, "
            "%d linhas carregadas.",
            series_sucesso,
            series_falha,
            linhas_carregadas,
        )
    finally:
        engine.dispose()
    return series_falha


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    codigos = tuple(
        int(codigo.strip())
        for codigo in os.getenv(
            "SERIES_CODES", ",".join(map(str, CODIGOS_PADRAO))
        ).split(",")
        if codigo.strip()
    )
    data_inicial = datetime.strptime(
        os.getenv("DATA_INICIAL", "01/01/2020"), "%d/%m/%Y"
    ).date()
    if not codigos:
        raise ValueError("SERIES_CODES deve conter ao menos um código SGS.")
    return int(bool(executar_pipeline(codigos, data_inicial)))


if __name__ == "__main__":
    raise SystemExit(main())