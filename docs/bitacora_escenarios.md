# Bitácora de escenarios E01–E15

| Caso | Pedido | Estado inicial | Operación | Resultado real | Explicación | Evento(s) emitido(s) | ¿Cumple? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| E01 | O001 | DRAFT | evaluar_descuento | evaluar_descuento -> 10%. Estado final: DRAFT | VIP, total 2100 > 500, 4 unidades y sin promoción: cumple la regla del 10 %. | (ninguno) | Sí |
| E02 | O002 | DRAFT | evaluar_descuento | evaluar_descuento -> 0%. Estado final: DRAFT | No es VIP y el total (1050) no supera 5000: no cumple ninguna regla. | (ninguno) | Sí |
| E03 | O003 | DRAFT | confirmar | confirm() -> InvalidOrderData: Requiere artículos y cliente activo. Estado final: DRAFT | El cliente C003 está inactivo: confirm() lanza InvalidOrderData y el pedido sigue en DRAFT. | (ninguno) | Sí |
| E04 | O005 | DRAFT | evaluar_descuento | evaluar_descuento -> 0%. Estado final: DRAFT | La promoción activa bloquea ambos descuentos (NOT ActivePromotionSpec). | (ninguno) | Sí |
| E05 | O006 | DRAFT | evaluar_descuento | evaluar_descuento -> 5%. Estado final: DRAFT | Total 18000 > 5000 sin promoción: aplica la regla alterna del 5 %. | (ninguno) | Sí |
| E06 | O007 | DRAFT | confirmar | confirm() -> InvalidOrderData: Requiere artículos y cliente activo. Estado final: DRAFT | Pedido sin artículos: confirm() lanza InvalidOrderData y no emite evento. | (ninguno) | Sí |
| E07 | O008 | DRAFT | confirmar | confirm() -> OK. Estado final: CONFIRMED | 20 unidades es el máximo permitido (límite sobre la suma de unidades): confirma bien. | OrderConfirmed | Sí |
| E08 | O009 | DRAFT | agregar SKU003 x2 | add_item(SKU003 x2) -> OrderItemLimitExceeded: Máximo 20 unidades. Estado final: DRAFT | 19 + 2 = 21 unidades excede el límite: add_item lanza OrderItemLimitExceeded antes de modificar items. | (ninguno) | Sí |
| E09 | O010 | DRAFT | evaluar_descuento | evaluar_descuento -> 0%. Estado final: DRAFT | Total exactamente 500: la regla usa '>' estricto, por lo que no supera el umbral. | (ninguno) | Sí |
| E10 | O011 | DRAFT | evaluar_descuento | evaluar_descuento -> 0%. Estado final: DRAFT | VIP con total > 500 pero solo 3 unidades: MinimumUnitsSpec(4) falla. | (ninguno) | Sí |
| E11 | O012 | DRAFT | confirmar y enviar sin guia | confirm() -> OK; ship('') -> InvalidOrderData: La guía de envío es obligatoria. Estado final: CONFIRMED | confirm() es válido; ship('') falla por guía vacía y el pedido se queda en CONFIRMED. | OrderConfirmed | Sí |
| E12 | O013 | DRAFT | confirmar dos veces | confirm() -> OK; confirm() (2a vez) -> InvalidOrderTransition: Solo DRAFT. Estado final: CONFIRMED | La segunda confirmación lanza InvalidOrderTransition (ya no está en DRAFT) y no agrega otro evento. | OrderConfirmed | Sí |
| E13 | O014 | DRAFT | confirmar, enviar y cancelar | confirm() -> OK; ship('GUIA-014') -> OK; cancel('Ya no lo quiero') -> InvalidOrderTransition: Solo CONFIRMED puede cancelarse. Estado final: SHIPPED | cancel() solo se permite desde CONFIRMED; desde SHIPPED lanza InvalidOrderTransition. | OrderConfirmed, OrderShipped | Sí |
| E14 | O015 | DRAFT | confirmar, enviar y devolver | confirm() -> OK; ship('GUIA-015') -> OK; return_order() -> OK. Estado final: RETURNED | SHIPPED permite return_order(): termina en RETURNED. | OrderConfirmed, OrderShipped, OrderReturned | Sí |
| E15 | O016 | DRAFT | confirmar, enviar y entregar | confirm() -> OK; ship('GUIA-016') -> OK; deliver() -> OK. Estado final: DELIVERED | SHIPPED permite deliver(): termina en DELIVERED. | OrderConfirmed, OrderShipped, OrderDelivered | Sí |
