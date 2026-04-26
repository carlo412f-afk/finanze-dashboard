from __future__ import annotations


def monthly_payment(loan: float, annual_rate_pct: float, years: int) -> float:
    r = annual_rate_pct / 100 / 12
    n = years * 12
    if n == 0:
        return 0.0
    if r == 0:
        return loan / n
    return loan * r * (1 + r) ** n / ((1 + r) ** n - 1)


def total_interest(loan: float, annual_rate_pct: float, years: int) -> float:
    return monthly_payment(loan, annual_rate_pct, years) * years * 12 - loan


def upfront_costs(price: float, prima_casa: bool = True) -> dict[str, float]:
    imposta = price * 0.02 if prima_casa else price * 0.09
    notaio = max(1_500.0, price * 0.015)
    agenzia = price * 0.03
    return {
        "Imposta di registro": imposta,
        "Notaio (stima)": notaio,
        "Agenzia immobiliare (stima)": agenzia,
    }
