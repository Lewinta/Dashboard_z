# Import de facturas atómico y con reporte de errores

Fecha: 2026-08-03
Sitio afectado: `asicorp.tzcode.tech`
Apps tocadas: `dashboard_z`, `saas_dgii`

## Problema

El 2026-08-03 se cargó el CSV `13-FACTURACION LAUREADO ORTEGA 1Q JULIO.csv` (60 filas) en el
Invoice Creation Tool y se pulsó Import. Se crearon **58** facturas y el proceso se detuvo. El
usuario no recibió ningún aviso de que faltaban 2, y el estado por fila no quedó registrado.

### Reconstrucción del fallo

| Hora | Evento |
|---|---|
| 13:05:27 | Se sube el CSV |
| 13:05:35 | "Load Invoices" guarda las 60 filas (`modified` del Single) |
| 13:06:53 → 13:07:32.42 | Se crean 58 facturas, NCF `B0200020657`→`B0200020714`, consecutivos y sin huecos |
| 13:07:32.92 | Fila 59: se crea el Patient `PID-23561` (SANTA VINICIO) |
| 13:07:32.93 | Se crea el Customer `CUST-24227` |
| 13:07:32.95 | Última escritura (`Patient.modified`). Fin del proceso. |

El contador NCF quedó en **20715**, es decir `doc.insert()` de la fila 59 nunca llegó a
ejecutarse — el NCF se asigna en `autoname`, que es lo primero del insert.

### Causas descartadas con evidencia

- **Timeout**: el import tardó 39 s; gunicorn está en `-t 120` y nginx en `proxy_read_timeout 120`.
- **Muerte del worker**: los procesos gunicorn llevan corriendo desde el 2026-08-02 06:29 sin reinicio.
- **Dato inválido en el CSV**: se reejecutó el `insert + submit` real de las filas 58, 59 y 60 en
  consola con los commits neutralizados; las tres se crean sin error y luego se hizo rollback.
- **Duplicado**: no existe ninguna Sales Invoice con `authorization_no` 1918141148 ni 1918141223.

### Causa raíz

Un `frappe.throw` (ValidationError) entre `create_customer()` y el insert de la factura —
con alta probabilidad dentro de `set_missing_values()` contra el Customer recién creado en esa
misma iteración. Frappe devuelve las ValidationError al navegador como msgprint y **no** las
escribe en Error Log, por eso no hay traza en ningún log.

Dos defectos estructurales lo convirtieron en pérdida de datos silenciosa:

1. **No hay atomicidad.** `get_next_avail_ncf()` hace `frappe.db.commit()` en cada asignación de
   NCF (`saas_dgii/.../dgii_settings.py:43`) y el import hace `frappe.db.sql("commit")` al crear
   cada paciente (`invoice_creation_tool.py:189`). Cada factura commitea toda la transacción, así
   que un fallo a mitad deja el lote partido y ningún rollback puede repararlo.
2. **No hay reporte.** `import_invoices()` asigna `row.status` pero nunca llama a `self.save()`,
   de modo que los estados `Imported`/`Duplicate` se pierden siempre. Y el handler de progreso en
   el cliente llama `frappe.hide_msgprint(true)`, que oculta los diálogos de error.

## Objetivos

1. El import es **todo o nada**: o se registran las 60 facturas o ninguna.
2. Cualquier error se le informa al usuario con suficiente detalle para corregir el CSV.
3. Dejar el lote actual consistente: exactamente 60 facturas visibles en "Cargar Facturas"
   para PHY-00018 + ARS-00002.

## Diseño

### 1. `saas_dgii` — allocator de NCF transaccional

`DGIISettings.get_next_avail_ncf()` deja de commitear y toma un lock de fila sobre el contador:

```python
cfg = frappe.db.sql(
    "SELECT `current`, `max` FROM `tabNCF Configuration` WHERE name=%s FOR UPDATE",
    row.name, as_dict=True,
)[0]
if cint(cfg.current) >= cint(cfg.max):
    frappe.throw(_("Serie {} reached it's limit please reload").format(serie))
new_seq = cint(cfg.current)
frappe.db.set_value("NCF Configuration", row.name, "current", new_seq + 1, update_modified=False)
row.current = new_seq + 1   # mantener el doc en memoria en sincronía
return "{0}{1:08d}".format(serie.split(".")[0], new_seq)
```

Consecuencias:

- El rollback **libera** el número en vez de quemarlo: menos huecos en la secuencia fiscal.
- Cierra una carrera latente: hoy dos requests que carguen el doc a la vez pueden obtener el
  mismo NCF; el commit rápido no lo impide, el `FOR UPDATE` sí.
- **Trade-off aceptado**: el lock se sostiene hasta el fin de la transacción, así que un import
  de 60 facturas (~40 s) bloquea la creación de facturas del **mismo médico** durante ese rato
  (`innodb_lock_wait_timeout` por defecto es 50 s). Médicos distintos no se estorban. Si llega a
  molestar, el siguiente paso es mover el import a un background job.
- **Radio de impacto**: `saas_dgii` está instalado únicamente en `asicorp.tzcode.tech`.

### 2. `dashboard_z` — import en tres fases

`InvoiceCreationTool.import_invoices()` se reestructura:

```
ctx            = contexto (company, cuentas, DGII Settings)
plan, errores  = FASE 1: validar las filas sin escribir nada
si errores     -> reportar y salir; no se crea nada

FASE 2: una sola transacción
  try:    crear las facturas del plan
  except: frappe.db.rollback()  -> 0 facturas, 0 pacientes, 0 NCF consumidos

FASE 3: reportar
```

**Fase 1 — validación sin escritura.** Por cada fila comprueba: `customer` y `date` no vacíos;
fecha con formato válido y no futura; `ars` existe como Customer; `claimed`/`authorized`
numéricos; paciente resoluble (por `nss` o por nombre) o creable; y NCF disponibles ≥ filas a
crear. Los duplicados por `authorization_no` se marcan `Duplicate` y se **omiten** — no son error
y no abortan el lote (es la idempotencia ya existente, que permite reintentar sin duplicar).

**Fase 2 — creación transaccional.** Se eliminan el `frappe.db.sql("commit")` y el
`frappe.local.rollback_observers = []` de `invoice_creation_tool.py:189-190`. Todo el bucle corre
en una única transacción.

**Fase 3 — reporte.** Escribe `status` y `error_message` por fila, hace `self.save()` y su propio
`frappe.db.commit()`, y **devuelve** el resumen al cliente. Nunca usa `frappe.throw`: un throw
provocaría el rollback del propio reporte.

Forma del retorno:

```python
{
  "ok": bool,
  "created": int,
  "duplicated": int,
  "errors": [{"idx": int, "customer": str, "authorization_no": str, "message": str}],
}
```

### 3. Doctype `Invoice Creation Item`

Agregar `error_message` (Small Text, `read_only=1`, `in_list_view=1`). El campo `status` ya tiene
las opciones `''` / `Imported` / `Duplicate` / `Error`.

### 4. `invoice_creation_tool.js`

- Renderizar un diálogo de resumen a partir del payload devuelto por `import_invoices`.
- Quitar el `frappe.hide_msgprint(true)` del handler `import_invoice_progress` (línea 49): oculta
  los diálogos de error y es la razón probable de que el fallo de la fila 59 pasara desapercibido.
- Mantener el freeze anti doble-click ya existente.

### 5. Corrección del estado actual (una sola vez)

Situación objetivo: exactamente 60 facturas para PHY-00018 + ARS-00002 en "Cargar Facturas".

```
AHORA       93 = 58 (lote de hoy) + 2 (creadas 2026-07-07) + 33 (creadas 2026-07-06)
CANCELAR    35  (los lotes del 6 y 7 de julio, posting_date 2026-04-30 a 2026-05-30, RD$113,443.00)
CREAR        2  (filas 59 y 60: SANTA VINICIO/1918141148 y MARIA BATISTA/1918141223)
RESULTADO   60
```

Las 35 se verificaron libres de dependencias: 0 Payment Entry References, 0 facturas de proveedor
que las referencien vía `paid_sales_invoices`, 0 Journal Entry Accounts. Sólo tienen 208 GL Entries
activos, que el cancel revierte. El hook `dashboard_z.hook.sales_invoice.on_cancel` sólo actúa
sobre facturas de proveedor, así que no tiene efecto aquí.

Las 2 faltantes se crean reejecutando Import desde la herramienta con el código ya corregido: la
idempotencia marca las 58 existentes como `Duplicate` y crea únicamente las 2 que faltan.

Al terminar se entrega el **listado de NCF anulados** (número, fecha, monto) para que contabilidad
lo reporte en el formato 608. No se toca nada de DGII automáticamente.

## Verificación

- **Allocator**: dos asignaciones concurrentes no repiten número; un rollback devuelve el contador
  a su valor previo.
- **Atomicidad**: forzar un fallo en la fila N del lote y comprobar que quedan 0 facturas, 0
  pacientes nuevos y el contador NCF intacto.
- **Validación**: CSV con filas inválidas → 0 facturas creadas y una entrada de error por cada
  fila mala, persistida en la grilla.
- **Idempotencia**: reejecutar el import sobre un lote ya creado → 0 nuevas, todas `Duplicate`.
- **Ensayo previo a producción**: la técnica ya usada en el diagnóstico — neutralizar `commit` en
  consola, ejecutar el `insert + submit` real, verificar y hacer rollback.

## Fuera de alcance

- Mover el import a un background job (sólo si la contención del lock resulta molesta).
- El filtro de fechas por defecto en el diálogo "Cargar Facturas".
- Las 14 facturas migradas con `payment_status = 'UNPAID'` pero `status = 'Paid'` y
  `outstanding_amount = 0` (13 de MAPFRE de 2022, 1 de HUMANO de 2024). Sólo quedan ocultas
  porque el diálogo filtra por ARS; si la factura de proveedor se abre sin customer, aparecen.
