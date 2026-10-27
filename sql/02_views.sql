CREATE OR REPLACE VIEW vw_ipca_12_meses AS
WITH ipca_mensal AS (
    SELECT
        date_trunc('month', data)::date AS mes,
        AVG(valor)::double precision AS ipca_mensal_pct
    FROM series_valores
    WHERE codigo = 433
    GROUP BY date_trunc('month', data)::date
),
acumulada AS (
    SELECT
        mes,
        COUNT(*) OVER janela AS quantidade_meses,
        MIN(mes) OVER janela AS primeiro_mes,
        EXP(SUM(LN(1 + ipca_mensal_pct / 100)) OVER janela) - 1
            AS inflacao_12_meses
    FROM ipca_mensal
    WHERE ipca_mensal_pct > -100
    WINDOW janela AS (
        ORDER BY mes
        ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
    )
)
SELECT
    mes AS data,
    inflacao_12_meses * 100 AS inflacao_12_meses_pct
FROM acumulada
WHERE quantidade_meses = 12
  AND primeiro_mes = (mes - INTERVAL '11 months')::date;

CREATE OR REPLACE VIEW vw_juro_real AS
WITH selic_mensal AS (
    SELECT
        date_trunc('month', data)::date AS mes,
        valor::double precision AS selic_anual_pct,
        ROW_NUMBER() OVER (
            PARTITION BY date_trunc('month', data)
            ORDER BY data DESC
        ) AS ordem
    FROM series_valores
    WHERE codigo = 12
)
SELECT
    ipca.data,
    selic.selic_anual_pct,
    ipca.inflacao_12_meses_pct,
    (
        (1 + selic.selic_anual_pct / 100)
        / (1 + ipca.inflacao_12_meses_pct / 100)
        - 1
    ) * 100 AS juro_real_pct
FROM vw_ipca_12_meses AS ipca
JOIN selic_mensal AS selic
  ON selic.mes = ipca.data
 AND selic.ordem = 1
WHERE ipca.inflacao_12_meses_pct > -100;

CREATE OR REPLACE VIEW vw_analise_mensal AS
WITH cambio_mensal AS (
    SELECT
        date_trunc('month', data)::date AS mes,
        AVG(valor)::double precision AS cambio_medio_brl_por_usd
    FROM series_valores
    WHERE codigo = 1
    GROUP BY date_trunc('month', data)::date
),
ipca_mensal AS (
    SELECT
        date_trunc('month', data)::date AS mes,
        AVG(valor)::double precision AS ipca_mensal_pct
    FROM series_valores
    WHERE codigo = 433
    GROUP BY date_trunc('month', data)::date
)
SELECT
    cambio.mes AS data,
    cambio.cambio_medio_brl_por_usd,
    (
        cambio.cambio_medio_brl_por_usd
        / NULLIF(
            LAG(cambio.cambio_medio_brl_por_usd) OVER (ORDER BY cambio.mes),
            0
        )
        - 1
    ) * 100 AS variacao_cambio_mensal_pct,
    ipca.ipca_mensal_pct,
    juro.juro_real_pct
FROM cambio_mensal AS cambio
LEFT JOIN ipca_mensal AS ipca ON ipca.mes = cambio.mes
LEFT JOIN vw_juro_real AS juro ON juro.data = cambio.mes;