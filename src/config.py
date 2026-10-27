import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def criar_engine() -> Engine:
    """Cria o engine PostgreSQL com credenciais obtidas do ambiente."""
    obrigatorias = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    ausentes = [nome for nome in obrigatorias if not os.getenv(nome)]
    if ausentes:
        raise RuntimeError(
            "Variáveis de ambiente obrigatórias ausentes: " + ", ".join(ausentes)
        )

    return create_engine(
        URL.create(
            drivername="postgresql+psycopg2",
            username=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.environ["POSTGRES_DB"],
        ),
        pool_pre_ping=True,
    )


def criar_engine_leitura() -> Engine:
    """Cria um engine usando a credencial PostgreSQL de somente leitura."""
    obrigatorias = (
        "POSTGRES_DB",
        "POSTGRES_READONLY_USER",
        "POSTGRES_READONLY_PASSWORD",
    )
    ausentes = [nome for nome in obrigatorias if not os.getenv(nome)]
    if ausentes:
        raise RuntimeError(
            "Variáveis de ambiente obrigatórias ausentes: " + ", ".join(ausentes)
        )

    return create_engine(
        URL.create(
            drivername="postgresql+psycopg2",
            username=os.environ["POSTGRES_READONLY_USER"],
            password=os.environ["POSTGRES_READONLY_PASSWORD"],
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.environ["POSTGRES_DB"],
        ),
        pool_pre_ping=True,
    )