"""Ejecuta los 15 escenarios E01-E15 de datos/escenarios.csv contra el dominio
y genera la bitácora en docs/bitacora_escenarios.md.

Uso:  python ejecutar_escenarios.py
Cada escenario parte de un load_fixture() nuevo, sin editar los datos.
"""
from decimal import Decimal
from pathlib import Path

from app.domain import DomainException, Money, OrderItem
from app.specifications import discount_rate
from cargar_csv import load_fixture, rows


def steps_for(caso, order):
    """Devuelve la lista de pasos (etiqueta, función) de cada escenario."""
    if caso in ("E01", "E02", "E04", "E05", "E09", "E10"):
        return [("evaluar_descuento", lambda: f"{int(discount_rate(order) * 100)}%")]
    if caso in ("E03", "E06", "E07"):
        return [("confirm()", order.confirm)]
    if caso == "E08":
        return [("add_item(SKU003 x2)",
                 lambda: order.add_item(OrderItem("SKU003", 2, Money(Decimal("120.00")))))]
    if caso == "E11":
        return [("confirm()", order.confirm), ("ship('')", lambda: order.ship(""))]
    if caso == "E12":
        return [("confirm()", order.confirm), ("confirm() (2a vez)", order.confirm)]
    if caso == "E13":
        return [("confirm()", order.confirm), ("ship('GUIA-014')", lambda: order.ship("GUIA-014")),
                ("cancel('Ya no lo quiero')", lambda: order.cancel("Ya no lo quiero"))]
    if caso == "E14":
        return [("confirm()", order.confirm), ("ship('GUIA-015')", lambda: order.ship("GUIA-015")),
                ("return_order()", order.return_order)]
    if caso == "E15":
        return [("confirm()", order.confirm), ("ship('GUIA-016')", lambda: order.ship("GUIA-016")),
                ("deliver()", order.deliver)]
    raise ValueError(caso)


EXPLICACION = {
    "E01": "VIP, total 2100 > 500, 4 unidades y sin promoción: cumple la regla del 10 %.",
    "E02": "No es VIP y el total (1050) no supera 5000: no cumple ninguna regla.",
    "E03": "El cliente C003 está inactivo: confirm() lanza InvalidOrderData y el pedido sigue en DRAFT.",
    "E04": "La promoción activa bloquea ambos descuentos (NOT ActivePromotionSpec).",
    "E05": "Total 18000 > 5000 sin promoción: aplica la regla alterna del 5 %.",
    "E06": "Pedido sin artículos: confirm() lanza InvalidOrderData y no emite evento.",
    "E07": "20 unidades es el máximo permitido (límite sobre la suma de unidades): confirma bien.",
    "E08": "19 + 2 = 21 unidades excede el límite: add_item lanza OrderItemLimitExceeded antes de modificar items.",
    "E09": "Total exactamente 500: la regla usa '>' estricto, por lo que no supera el umbral.",
    "E10": "VIP con total > 500 pero solo 3 unidades: MinimumUnitsSpec(4) falla.",
    "E11": "confirm() es válido; ship('') falla por guía vacía y el pedido se queda en CONFIRMED.",
    "E12": "La segunda confirmación lanza InvalidOrderTransition (ya no está en DRAFT) y no agrega otro evento.",
    "E13": "cancel() solo se permite desde CONFIRMED; desde SHIPPED lanza InvalidOrderTransition.",
    "E14": "SHIPPED permite return_order(): termina en RETURNED.",
    "E15": "SHIPPED permite deliver(): termina en DELIVERED.",
}

# Resultado esperado por escenario (lo que dicta el Word/README del paquete).
ESPERADO = {
    "E01": "10%", "E02": "0%", "E03": "InvalidOrderData", "E04": "0%", "E05": "5%",
    "E06": "InvalidOrderData", "E07": "CONFIRMED", "E08": "OrderItemLimitExceeded",
    "E09": "0%", "E10": "0%", "E11": "InvalidOrderData", "E12": "InvalidOrderTransition",
    "E13": "InvalidOrderTransition", "E14": "RETURNED", "E15": "DELIVERED",
}


def ejecutar(caso, pedido_id, accion):
    order = load_fixture()[pedido_id]
    estado_inicial = order.status.value
    log, final = [], None
    for etiqueta, fn in steps_for(caso, order):
        try:
            out = fn()
            log.append(f"{etiqueta} -> {out}" if out is not None else f"{etiqueta} -> OK")
            final = out if isinstance(out, str) else order.status.value
        except DomainException as exc:
            log.append(f"{etiqueta} -> {type(exc).__name__}: {exc}")
            final = type(exc).__name__
    eventos = [e.name for e in order.events]
    resultado = "; ".join(log) + f". Estado final: {order.status.value}"
    return {
        "caso": caso, "pedido": pedido_id, "inicial": estado_inicial,
        "operacion": accion, "resultado": resultado,
        "explicacion": EXPLICACION[caso],
        "eventos": ", ".join(eventos) if eventos else "(ninguno)",
        "final": final, "ok": final == ESPERADO[caso],
    }


def main():
    resultados = [ejecutar(r["caso_id"], r["pedido_id"], r["accion"]) for r in rows("escenarios.csv")]
    lineas = [
        "# Bitácora de escenarios E01–E15",
        "",
        "| Caso | Pedido | Estado inicial | Operación | Resultado real | Explicación | Evento(s) emitido(s) | ¿Cumple? |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in resultados:
        lineas.append(
            f"| {r['caso']} | {r['pedido']} | {r['inicial']} | {r['operacion']} | {r['resultado']} "
            f"| {r['explicacion']} | {r['eventos']} | {'Sí' if r['ok'] else 'NO'} |"
        )
    destino = Path(__file__).resolve().parent / "docs" / "bitacora_escenarios.md"
    destino.parent.mkdir(exist_ok=True)
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    for r in resultados:
        print(f"{r['caso']} {r['pedido']}: {'OK ' if r['ok'] else 'FALLA'} | {r['resultado']} | eventos={r['eventos']}")
    print(f"\nBitácora escrita en {destino}")
    return all(r["ok"] for r in resultados)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
