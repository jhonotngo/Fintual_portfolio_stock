"""
Ejercicio Fintual - Portfolio
Autor: Jhonatan González
Requiere Python 3.10+

Decisiones de modelación
------------------------
- Stock representa la acción en el mercado (símbolo + último precio).
  No sabe cuántas unidades tiene nadie: eso es información del portfolio.
- Position une una Stock con la cantidad de acciones que tengo de ella.
  Una Position con 0 acciones es una acción que el portfolio sigue pero aún
  no tiene; así el portfolio conoce su precio y puede comprarla.
- Portfolio recibe en el constructor su colección de Positions (lo que tengo)
  y la allocation objetivo (qué fracción del valor total, entre 0 y 1,
  quiero en cada símbolo).
  Las posiciones quedan fijas después de construir el portfolio: se pueden
  leer (positions), pero no agregar, quitar ni modificar. La allocation sí
  se puede reemplazar con update_allocation(), porque cambiar la meta es una
  decisión del usuario.
- rebalance() no ejecuta nada: devuelve la lista de órdenes (Trade) necesarias
  para pasar de las posiciones actuales a la allocation objetivo. Ejecutar las
  órdenes queda fuera del alcance; para reflejarlas se construye un portfolio
  nuevo con las cantidades resultantes (como hace la demo).
- Trade es una orden inmutable: símbolo, tipo (Side), cantidad de acciones
  y monto en dinero, calculados con el precio del momento del rebalanceo.
  Guarda el símbolo y no la Stock porque es un registro de datos: así no
  queda atada a un objeto mutable y es simple de mostrar, comparar o guardar.
- Side (BUY/SELL) es un Enum en vez de un string o de una cantidad con
  signo, para que el tipo de orden sea explícito y no admita valores inválidos.
- Montos y precios usan Decimal: con float, 0.1 + 0.2 no da 0.3,
  y en dinero ese error de redondeo no es aceptable.

Supuestos
---------
- El enunciado dice que Current Price "receives the last available price",
  lo que se puede leer como que devuelve el precio o que lo recibe. Se
  interpretó como que lo devuelve: current_price() entrega el último precio
  disponible, que se asume ya obtenido del mercado. La entrada del precio
  queda cubierta por update_price().
- La allocation se guarda por símbolo (ej.: {"META": 0.40, "AAPL": 0.60}) y
  no por objeto Stock, porque el precio ya lo conoce la Position. Al asignarla
  se valida que cada símbolo tenga una Position en el portfolio.
- Se permiten acciones fraccionarias.
- Sin comisiones ni impuestos.
- Se rebalancea con el valor actual del portfolio (no entra ni sale dinero),
  por lo que el total vendido es igual al total comprado, salvo las
  diferencias menores a la tolerancia, que no se operan.
- Una acción que tengo pero que no está en la allocation tiene objetivo 0%,
  es decir, se vende completa.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

DecimalInput = Decimal | int | float | str


def to_decimal(value: DecimalInput) -> Decimal:
    # Se pasa por str para que 0.1 se convierta en Decimal("0.1") y no en
    # Decimal("0.1000000000000000055511151231257827...") que arrastra el float.
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"Valor numérico inválido: {value!r}") from None
    # Decimal acepta "NaN" e "Infinity", que no tienen sentido como dinero.
    if not result.is_finite():
        raise ValueError(f"Valor numérico no finito: {value!r}")
    return result


class Side(Enum):
    BUY = "BUY"
    SELL = "SELL"


class Stock:
    def __init__(self, symbol: str, price: DecimalInput) -> None:
        self.symbol = symbol
        self.update_price(price)

    def current_price(self) -> Decimal:
        """Último precio disponible (método pedido por el enunciado)."""
        return self._last_price

    def update_price(self, price: DecimalInput) -> None:
        price = to_decimal(price)
        # Con precio 0 no se puede calcular cuántas acciones transar.
        if price <= 0:
            raise ValueError(f"Precio inválido para {self.symbol}: {price}")
        self._last_price = price


# Inmutable: la cantidad solo se valida al construir, así que no debe poder
# cambiarse después. El precio sí cambia, pero vive en Stock.
@dataclass(frozen=True)
class Position:
    stock: Stock
    shares: Decimal = Decimal(0)

    def __post_init__(self) -> None:
        shares = to_decimal(self.shares)
        if shares < 0:
            raise ValueError("La cantidad de acciones no puede ser negativa")
        object.__setattr__(self, "shares", shares)

    @property
    def value(self) -> Decimal:
        return self.shares * self.stock.current_price()


@dataclass(frozen=True)
class Trade:
    symbol: str
    side: Side
    shares: Decimal
    amount: Decimal


class Portfolio:
    # No se opera por diferencias menores a un centavo.
    DEFAULT_TOLERANCE = Decimal("0.01")

    def __init__(self, positions: list[Position], allocation: dict[str, DecimalInput]) -> None:
        self._positions: dict[str, Position] = {}
        for position in positions:
            symbol = position.stock.symbol
            if symbol in self._positions:
                raise ValueError(f"Posición duplicada para {symbol}")
            self._positions[symbol] = position

        self.update_allocation(allocation)

    @property
    def positions(self) -> list[Position]:
        return list(self._positions.values())

    @property
    def allocation(self) -> dict[str, Decimal]:
        return dict(self._allocation)

    def update_allocation(self, allocation: dict[str, DecimalInput]) -> None:
        """Reemplaza la allocation completa (no se mezcla con la anterior)."""
        allocation = {symbol: to_decimal(weight) for symbol, weight in allocation.items()}

        if any(not 0 <= weight <= 1 for weight in allocation.values()):
            raise ValueError("Cada peso debe estar entre 0 y 1")
        # Suma exacta, sin margen de error. Límite conocido: Decimal no representa
        # 1/3 exacto, así que una allocation en tercios no se puede expresar.
        if sum(allocation.values()) != 1:
            raise ValueError("La allocation debe sumar 1 (100%)")

        # Sin el precio de una acción no se puede calcular cuántas unidades comprar.
        missing = set(allocation) - set(self._positions)
        if missing:
            raise ValueError(f"Acciones no registradas en el portfolio: {sorted(missing)}")

        self._allocation = allocation

    @property
    def total_value(self) -> Decimal:
        return sum((p.value for p in self._positions.values()), Decimal(0))

    def rebalance(self, tolerance: Decimal = DEFAULT_TOLERANCE) -> list[Trade]:
        """Devuelve las órdenes para llegar a la allocation; no las ejecuta."""
        total = self.total_value
        if total == 0:
            return []

        sells: list[Trade] = []
        buys: list[Trade] = []
        # Se recorren todas las posiciones, no solo las de la allocation,
        # para detectar acciones que hay que vender completas.
        for symbol, position in self._positions.items():
            target_value = total * self._allocation.get(symbol, Decimal(0))
            difference = target_value - position.value

            if abs(difference) < tolerance:
                continue

            side = Side.BUY if difference > 0 else Side.SELL
            trade = Trade(
                symbol=symbol,
                side=side,
                shares=abs(difference) / position.stock.current_price(),
                amount=abs(difference),
            )
            (buys if side is Side.BUY else sells).append(trade)

        # Ventas primero: como no entra dinero nuevo, son las que financian las compras.
        return sells + buys


def print_portfolio(title: str, portfolio: Portfolio) -> None:
    total = portfolio.total_value
    allocation = portfolio.allocation
    print(f"\n{title}")
    print(f"{'Acción':<8}{'Acciones':>12}{'Precio':>12}{'Valor':>14}{'Actual':>10}{'Objetivo':>10}")
    for position in portfolio.positions:
        symbol = position.stock.symbol
        weight = position.value / total if total else Decimal(0)
        target = allocation.get(symbol, Decimal(0))
        print(
            f"{symbol:<8}{position.shares:>12.4f}{position.stock.current_price():>12,.2f}"
            f"{position.value:>14,.2f}{weight:>10.2%}{target:>10.2%}"
        )
    print(f"{'Total':<8}{'':>24}{total:>14,.2f}")


def print_trades(trades: list[Trade]) -> None:
    print("\nPasos para llegar a la allocation")
    if not trades:
        print("  El portfolio ya está balanceado.")
    for step, trade in enumerate(trades, start=1):
        print(f"  {step}. {trade.side.value} {trade.shares:.4f} {trade.symbol} (${trade.amount:,.2f})")


def apply_trades(portfolio: Portfolio, trades: list[Trade]) -> Portfolio:
    """Simula la ejecución de las órdenes y devuelve un portfolio nuevo.

    Solo para la demo: el modelo no ejecuta órdenes, así que el original
    no se modifica.
    """
    changes = {
        trade.symbol: trade.shares if trade.side is Side.BUY else -trade.shares
        for trade in trades
    }
    new_positions = [
        Position(p.stock, p.shares + changes.get(p.stock.symbol, Decimal(0)))
        for p in portfolio.positions
    ]
    return Portfolio(new_positions, portfolio.allocation)


if __name__ == "__main__":
    meta = Stock("META", 500)
    aapl = Stock("AAPL", 500)
    nvda = Stock("NVDA", 600)

    portfolio = Portfolio(
        positions=[
            Position(meta, 10),
            Position(aapl, 20),
            Position(nvda, 40),
        ],
        allocation={"META": "0.40", "AAPL": "0.60"},
    )

    print_portfolio("Estado inicial", portfolio)

    trades = portfolio.rebalance()
    print_trades(trades)

    print_portfolio("Estado después del rebalanceo", apply_trades(portfolio, trades))