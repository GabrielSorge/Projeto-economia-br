from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


MESES = (
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
)
IPCA_MENSAL_2023_PCT = (
    0.53,
    0.84,
    0.71,
    0.61,
    0.23,
    -0.08,
    0.12,
    0.23,
    0.26,
    0.24,
    0.28,
    0.56,
)
IPCA_ACUMULADO_2023_PCT = (
    np.prod(1 + np.asarray(IPCA_MENSAL_2023_PCT) / 100) - 1
) * 100
assert round(IPCA_ACUMULADO_2023_PCT, 2) == 4.62


def main() -> None:
    destino = Path(__file__).resolve().parents[1] / "assets" / "ipca-mensal-2023.png"
    destino.parent.mkdir(parents=True, exist_ok=True)

    fig, eixo = plt.subplots(figsize=(10, 5.5), layout="constrained")
    cores = [
        "tab:red" if valor < 0 else "tab:blue"
        for valor in IPCA_MENSAL_2023_PCT
    ]
    barras = eixo.bar(MESES, IPCA_MENSAL_2023_PCT, color=cores)
    eixo.axhline(0, color="black", linewidth=0.8)
    eixo.set_title("IPCA mensal — Brasil, 2023")
    eixo.set_xlabel("Mês")
    eixo.set_ylabel("Variação mensal (%)")
    eixo.grid(axis="y", alpha=0.25)
    eixo.bar_label(barras, fmt="%.2f%%", padding=3, fontsize=8)
    eixo.text(
        0.99,
        0.97,
        f"Acumulado composto no ano: {IPCA_ACUMULADO_2023_PCT:.2f}%",
        transform=eixo.transAxes,
        ha="right",
        va="top",
        bbox={"facecolor": "white", "edgecolor": "0.8", "alpha": 0.9},
    )
    fig.text(
        0.01,
        0.005,
        "Referência oficial IBGE/SGS; gráfico de referência, não extraído do banco local.",
        fontsize=8,
        color="0.35",
    )
    fig.savefig(destino, dpi=160)
    plt.close(fig)
    print(f"Gráfico salvo em {destino}")
    print(f"IPCA acumulado composto: {IPCA_ACUMULADO_2023_PCT:.5f}%")


if __name__ == "__main__":
    main()
