"""
Tests esenciales.

    python3 -m unittest -v
"""

import unittest
from decimal import Decimal

from fintual_portfolio_stock import Portfolio, Position, Side, Stock, Trade, apply_trades


def make_portfolio(holdings, allocation):
    """Crea un portfolio a partir de {símbolo: (precio, acciones)}."""
    positions = [
        Position(Stock(symbol, price), shares)
        for symbol, (price, shares) in holdings.items()
    ]
    return Portfolio(positions, allocation)


class RebalanceTest(unittest.TestCase):
    def test_caso_principal_con_numeros(self):
        # $5.000 en META y $5.000 en AAPL; el objetivo es 40/60 de $10.000.
        # META: $5.000 -> $4.000, vender $1.000 = 2 acciones a $500.
        # AAPL: $5.000 -> $6.000, comprar $1.000 = 4 acciones a $250.
        portfolio = make_portfolio(
            {"META": (500, 10), "AAPL": (250, 20)},
            {"META": "0.40", "AAPL": "0.60"},
        )
        self.assertEqual(
            portfolio.rebalance(),
            [
                Trade("META", Side.SELL, Decimal("2"), Decimal("1000")),
                Trade("AAPL", Side.BUY, Decimal("4"), Decimal("1000")),
            ],
        )

    def test_aplicar_y_rebalancear_da_vacio(self):
        portfolio = make_portfolio(
            {"META": (500, 10), "AAPL": (500, 20), "NVDA": (600, 40)},
            {"META": "0.40", "AAPL": "0.60"},
        )
        rebalanced = apply_trades(portfolio, portfolio.rebalance())
        self.assertEqual(rebalanced.rebalance(), [])

    def test_accion_fuera_de_la_allocation_se_vende_completa(self):
        portfolio = make_portfolio(
            {"META": (500, 10), "NVDA": (600, 5)},
            {"META": 1},
        )
        nvda = [t for t in portfolio.rebalance() if t.symbol == "NVDA"]
        self.assertEqual(
            nvda, [Trade("NVDA", Side.SELL, Decimal("5"), Decimal("3000"))]
        )

    def test_suma_vendida_igual_a_la_comprada(self):
        portfolio = make_portfolio(
            {"META": (500, 10), "AAPL": (500, 20), "NVDA": (600, 40)},
            {"META": "0.40", "AAPL": "0.60"},
        )
        trades = portfolio.rebalance()
        sold = sum(t.amount for t in trades if t.side is Side.SELL)
        bought = sum(t.amount for t in trades if t.side is Side.BUY)
        self.assertEqual(sold, bought)


class ToleranceTest(unittest.TestCase):
    # Precio $1 para que el valor de cada posición sea igual a sus acciones.
    # Total $100, objetivo $50 en cada una; la diferencia es lo que sobra en A.

    def rebalance_with_difference(self, difference):
        portfolio = make_portfolio(
            {
                "A": (1, Decimal("50") + Decimal(difference)),
                "B": (1, Decimal("50") - Decimal(difference)),
            },
            {"A": "0.5", "B": "0.5"},
        )
        return portfolio.rebalance()

    def test_diferencia_menor_a_la_tolerancia_no_se_opera(self):
        self.assertEqual(self.rebalance_with_difference("0.009"), [])

    def test_diferencia_igual_a_la_tolerancia_si_se_opera(self):
        # El límite es exclusivo: se ignora solo lo *menor* a un centavo.
        trades = self.rebalance_with_difference("0.01")
        self.assertEqual(
            trades,
            [
                Trade("A", Side.SELL, Decimal("0.01"), Decimal("0.01")),
                Trade("B", Side.BUY, Decimal("0.01"), Decimal("0.01")),
            ],
        )

    def test_diferencia_mayor_a_la_tolerancia_se_opera(self):
        self.assertEqual(len(self.rebalance_with_difference("0.02")), 2)


class AllocationTest(unittest.TestCase):
    def test_allocation_que_no_suma_1_se_rechaza(self):
        for allocation in (
            {"META": "0.40", "AAPL": "0.50"},  # suma 0.90
            {"META": "0.50", "AAPL": "0.60"},  # suma 1.10
        ):
            with self.subTest(allocation=allocation), self.assertRaises(ValueError):
                make_portfolio({"META": (500, 10), "AAPL": (250, 20)}, allocation)

    def test_allocation_con_floats_se_guarda_exacta(self):
        # Con floats, 0.1 + 0.2 no da 0.3. Al convertir vía str, cada peso
        # queda exacto, la suma da 1 y los montos no arrastran error.
        self.assertNotEqual(0.1 + 0.2, 0.3)
        portfolio = make_portfolio(
            {"A": (1, 1000), "B": (1, 0), "C": (1, 0)},
            {"A": 0.1, "B": 0.2, "C": 0.7},
        )
        self.assertEqual(
            portfolio.allocation,
            {"A": Decimal("0.1"), "B": Decimal("0.2"), "C": Decimal("0.7")},
        )
        amounts = {t.symbol: t.amount for t in portfolio.rebalance()}
        self.assertEqual(
            amounts,
            {"A": Decimal("900"), "B": Decimal("200"), "C": Decimal("700")},
        )


if __name__ == "__main__":
    unittest.main()