import json
import os
import re

from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from src.config import criar_engine_leitura
from src.text_to_sql import (
    ANSWER_SYSTEM_INSTRUCTION,
    DEFAULT_MODEL,
    MAX_QUESTION_LENGTH,
    ResultadoPergunta,
    _gemini_text,
    executar_sql_leitura,
    gerar_sql,
    validar_sql,
)


def perguntar(
    pergunta: str,
    engine: Engine | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> ResultadoPergunta:
    """Executa uma pergunta em linguagem natural e retorna a resposta."""
    pergunta = pergunta.strip()
    if not pergunta:
        raise ValueError("Informe uma pergunta em portugues.")
    if len(pergunta) > MAX_QUESTION_LENGTH:
        raise ValueError(
            f"A pergunta deve ter no maximo {MAX_QUESTION_LENGTH} caracteres."
        )

    chave = api_key or os.getenv("GEMINI_API_KEY")
    if not chave:
        raise RuntimeError(
            "Defina GEMINI_API_KEY no arquivo .env com a chave do Google AI Studio."
        )
    modelo = model or os.getenv("GEMINI_MODEL", DEFAULT_MODEL)
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,100}", modelo):
        raise ValueError("GEMINI_MODEL contem caracteres invalidos.")
    engine_local = engine if engine is not None else criar_engine_leitura()
    deve_fechar_engine = engine is None

    try:
        sql = validar_sql(gerar_sql(pergunta, chave, modelo))
        try:
            linhas = executar_sql_leitura(sql, engine_local)
        except SQLAlchemyError as exc:
            mensagem_erro = str(getattr(exc, "orig", exc))[:1000]
            sql = validar_sql(
                gerar_sql(pergunta, chave, modelo, erro_anterior=mensagem_erro)
            )
            try:
                linhas = executar_sql_leitura(sql, engine_local)
            except SQLAlchemyError as erro_final:
                raise RuntimeError(
                    "A consulta corrigida pelo Gemini tambem falhou: "
                    f"{getattr(erro_final, 'orig', erro_final)}"
                ) from erro_final

        contexto_resultado = json.dumps(
            {
                "pergunta": pergunta,
                "sql": sql,
                "total_linhas": len(linhas),
                "sem_dados": not any(
                    valor is not None
                    for linha in linhas
                    for valor in linha.values()
                ),
                "linhas": linhas[:20],
            },
            ensure_ascii=False,
            default=str,
        )
        resposta = _gemini_text(
            contexto_resultado,
            ANSWER_SYSTEM_INSTRUCTION,
            chave,
            modelo,
        )
        return ResultadoPergunta(pergunta, sql, linhas, resposta)
    finally:
        if deve_fechar_engine:
            engine_local.dispose()