# Fintual_portfolio_stock

Solución al ejercicio técnico de Fintual:

You’re building a portfolio management module, part of a personal investments and trading app
Construct a simple Portfolio class that has a collection of Stocks. Assume each Stock has a “Current Price” method that receives the last available price. Also, the Portfolio class has a collection of “allocated” Stocks that represents the distribution of the Stocks the Portfolio is aiming (i.e. 40% META, 60% APPL)
Provide a portfolio rebalance method to know which Stocks should be sold and which ones should be bought to have a balanced Portfolio based on the portfolio’s allocation.
Add documentation/comments to understand your thinking process and solution
Important: If you use LLMs that’s ok, but you must share the conversations.

**Autor:** Jhonatan González

## Requisitos

- Python 3.10 o superior.
- Sin dependencias externas: solo la librería estándar.

## Cómo ejecutarlo

```bash
# Demo: estado inicial, órdenes y estado después del rebalanceo
python3 portfolio.py

# Tests
python3 -m unittest -v
```

## Resultado de la demo

Un portfolio con META, AAPL y NVDA, donde la allocation objetivo es 40% META y 60% AAPL. NVDA no está en la allocation, así que se vende completa.

```
Estado inicial
Acción      Acciones      Precio         Valor    Actual  Objetivo
META         10.0000      500.00      5,000.00    12.82%    40.00%
AAPL         20.0000      500.00     10,000.00    25.64%    60.00%
NVDA         40.0000      600.00     24,000.00    61.54%     0.00%
Total                                39,000.00

Pasos para llegar a la allocation
  1. SELL 40.0000 NVDA ($24,000.00)
  2. BUY 21.2000 META ($10,600.00)
  3. BUY 26.8000 AAPL ($13,400.00)

Estado después del rebalanceo
Acción      Acciones      Precio         Valor    Actual  Objetivo
META         31.2000      500.00     15,600.00    40.00%    40.00%
AAPL         46.8000      500.00     23,400.00    60.00%    60.00%
NVDA          0.0000      600.00          0.00     0.00%     0.00%
Total                                39,000.00
```

## Cómo responde al enunciado

| Enunciado | Solución |
|---|---|
| Clase `Portfolio` con una colección de Stocks | `Portfolio` guarda una colección de `Position`, y cada una contiene una `Stock` y la cantidad de acciones. Sin cantidades no se puede rebalancear. |
| Cada Stock tiene un método "Current Price" | `Stock.current_price()` devuelve el último precio disponible. |
| Colección de Stocks "allocated" (40% META, 60% AAPL) | `Portfolio.allocation`: `{"META": 0.40, "AAPL": 0.60}`. |
| Método de rebalanceo que diga qué vender y qué comprar | `Portfolio.rebalance()` devuelve una lista de `Trade` con el símbolo, `BUY`/`SELL`, la cantidad de acciones y el monto. |
| Documentación del razonamiento | El docstring de `portfolio.py` (decisiones de modelación y supuestos), los comentarios en el código y este README. |

## Modelo

| Clase | Responsabilidad |
|---|---|
| `Stock` | La acción en el mercado: símbolo y último precio. No sabe cuántas acciones tiene nadie. |
| `Position` | Una `Stock` más la cantidad que se tiene de ella. Es inmutable. Una posición con 0 acciones representa una acción que se sigue pero todavía no se tiene. |
| `Portfolio` | Las posiciones (lo que se tiene) y la allocation (lo que se quiere tener). Calcula el rebalanceo. |
| `Trade` | Una orden inmutable: símbolo, `Side`, cantidad de acciones y monto en dinero. |
| `Side` | Enum `BUY` / `SELL`. |

**Convención de nombres:** las lecturas son propiedades (`positions`, `allocation`, `value`, `total_value`), salvo `current_price()`, que es un método porque así lo pide el enunciado. Las escrituras son métodos `update_*()` (`update_price`, `update_allocation`).

## Cómo funciona el rebalanceo

1. Se calcula el valor total del portfolio: la suma de acciones × precio de cada posición.
2. Para cada posición, el valor objetivo es el valor total × su peso en la allocation. Si la acción no está en la allocation, su peso es 0%.
3. La diferencia entre el valor objetivo y el valor actual indica qué hacer: si es positiva, se compra; si es negativa, se vende.
4. Esa diferencia se divide por el precio actual para obtener la cantidad de acciones.
5. Se ignoran las diferencias menores a la tolerancia ($0,01 por defecto).
6. Las ventas se devuelven antes que las compras, porque como no entra dinero nuevo, son las que financian las compras.
`rebalance()` **no ejecuta las órdenes** ni modifica el portfolio: solo las devuelve. La demo usa `apply_trades()` para simular la ejecución, y lo hace construyendo un portfolio nuevo.

## Decisiones principales

- **`Decimal` en vez de `float`.** En dinero no se acepta el error binario de `0.1 + 0.2 != 0.3`. Los valores se convierten pasando por `str`, para que un float como `0.1` quede como `Decimal("0.1")` exacto.
- **Validar al construir.** Un portfolio no puede existir con posiciones duplicadas, pesos fuera del rango de 0 a 1, una allocation que no suma 1 o símbolos sin posición. Tampoco una acción puede tener precio menor o igual a 0.
- **Mutabilidad controlada.** Las posiciones quedan fijas y cambian solo operando, lo que está fuera del alcance. La allocation se puede reemplazar con `update_allocation()`, porque cambiar la meta es una decisión del usuario. El precio se actualiza con `update_price()`, y el portfolio ve el cambio automáticamente porque comparte la misma `Stock`.
El detalle completo de las decisiones está en el docstring de `portfolio.py`.

## Supuestos

- **"Current Price receives the last available price".** La frase admite dos lecturas: que el método devuelve el precio o que lo recibe. Se interpretó como que lo **devuelve**, porque el rebalanceo necesita leer el precio. La otra lectura queda cubierta por `update_price()`.
- La allocation se guarda **por símbolo**, no por objeto `Stock`. Se valida que cada símbolo tenga una posición en el portfolio.
- Se permiten acciones fraccionarias.
- No hay comisiones ni impuestos.
- No entra ni sale dinero, así que el total vendido es igual al total comprado.
- Una acción que está en el portfolio pero no en la allocation tiene objetivo 0%, y se vende completa.

## Limitaciones conocidas

- **Tolerancia.** Si una acción fuera de la allocation vale menos de $0,01, no se vende, porque su diferencia está bajo la tolerancia.
- **Tercios.** La allocation debe sumar exactamente 1, y `Decimal` no representa 1/3 exacto. Por eso, una allocation en tercios no se puede expresar.
- **Cantidades con muchos decimales.** Al dividir un monto por el precio, la cantidad de acciones puede quedar con muchos decimales (por ejemplo, 0,8333…). Si solo se permitieran acciones enteras, haría falta redondear.

## Tests

`test_portfolio.py` tiene 9 tests con `unittest`, que cubren:

- el caso principal con números (40/60)
- que aplicar las órdenes y volver a rebalancear devuelva una lista vacía
- vender completa una acción que está fuera de la allocation
- que el total vendido sea igual al total comprado
- la tolerancia: una diferencia menor a $0,01 no se opera, pero una de $0,01 exacto sí
- el rechazo de una allocation que no suma 1
- los pesos ingresados como float (`0.1`, `0.2`, `0.7`), que deben quedar exactos

## Uso de LLM

Usé Claude durante el ejercicio para:

- entender el dominio antes de programar (qué es una allocation y cómo se calcula un rebalanceo)
- revisar mi solución como lo haría un evaluador técnico: modelación, nombres y comentarios
- discutir la ambigüedad de "Current Price" y refactorizaciones como el renombre de `Action` a `Side`

El diseño del modelo y las decisiones finales son míos. Revisé cada sugerencia antes de incorporarla.

Conversación: https://claude.ai/share/d75ce96a-4a22-4b8a-bfd4-a3e93bb76e57