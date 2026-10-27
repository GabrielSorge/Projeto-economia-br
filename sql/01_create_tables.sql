CREATE TABLE IF NOT EXISTS series_catalogo (
    codigo INTEGER PRIMARY KEY,
    descricao TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS series_valores (
    codigo INTEGER NOT NULL REFERENCES series_catalogo (codigo) ON DELETE CASCADE,
    data DATE NOT NULL,
    valor NUMERIC NOT NULL,
    PRIMARY KEY (codigo, data)
);