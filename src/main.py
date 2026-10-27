import logging
import os
from datetime import date, datetime

from src.config import criar_engine
from src.extract import buscar_serie
from src.load import carregar_valores, obter_ultima_data
from src.transform import criar_dataframe


logger = logging.getLogger(__name__)
CODIGOS_PADRAO = (432, 11, 12, 433, 1)


def executar_pipeline(
    codigos: tuple[int, ...] = CODIGOS_PADRAO,
    data_inicial: date = date(2020, 1, 1),
    data_final: date | None = None,
) -> None:
    """Executa extração, transformação e carga incremental para cada série."""
    engine = criar_engine()
    fim = data_final or date.today()
    try:
        for codigo in codigos:
            ultima_data = obter_ultima_data(codigo, engine)
            inicio = ultima_data or data_inicial
            if inicio > fim:
                logger.info(
                    "Série SGS %s: já está atualizada até %s.",
                    codigo,
                    inicio.isoformat(),
                )
                continue

            registros = buscar_serie(codigo, inicio, fim)
            dados = criar_dataframe(registros, codigo)
            carregados = carregar_valores(dados, codigo, engine)
            logger.info(
                "Série SGS %s: %d observações processadas (%d recebidas).",
                codigo,
                carregados,
                len(registros),
            )
    finally:
        engine.dispose()


def main() -> None:
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
    executar_pipeline(codigos, data_inicial)


if __name__ == "__main__":
    main()