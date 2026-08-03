# Import de facturas atómico — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que el Invoice Creation Tool registre las 60 facturas del lote o ninguna, y que cualquier error se le reporte al usuario por fila para que pueda corregir el CSV.

**Architecture:** Se elimina el `frappe.db.commit()` del allocator de NCF (reemplazado por un lock `FOR UPDATE` sobre el contador) y el `frappe.db.sql("commit")` del import, de modo que el lote entero corre en una sola transacción con rollback. Encima se añade una fase de validación previa que no escribe nada y una fase de reporte que persiste el resultado por fila en su propia transacción.

**Tech Stack:** Frappe v16.15.0, ERPNext 17.x develop, MariaDB/InnoDB, Python 3.13, sitio `asicorp.tzcode.tech`.

## Global Constraints

- Sitio único de trabajo: `asicorp.tzcode.tech`. Es **producción**; toda prueba destructiva va envuelta en `frappe.db.rollback()`.
- `apps/dashboard_z` es repo git (rama `master`) → cada tarea termina en commit.
- `apps/saas_dgii` **no es repo git** → no hay commit posible; antes de editarlo se guarda copia en `apps/saas_dgii.bak-2026-08-03/`.
- Directorio de scratch para todo script temporal: `/tmp/claude-1000/-home-tzcode-frappe-bench/5d5d9190-7ae6-47a2-8fb3-9fe6c7eb17db/scratchpad`.
- Tras **cualquier** edición de `.py` hay que recargar los workers o el cambio no toma efecto (módulos ya en `sys.modules`):
  ```bash
  MASTER=$(ps -eo pid,ppid,cmd | grep "[f]rappe-bench/env/bin/gunicorn" | awk '{print $2}' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
  kill -HUP "$MASTER"
  ```
- Los scripts de verificación se ejecutan así (la consola de bench lee de stdin):
  ```bash
  cd /home/tzcode/frappe-bench && echo "exec(open('<ruta>').read())" | bench --site asicorp.tzcode.tech console
  ```
- Serie fiscal en uso: `B02.########`. Médico del lote: `PHY-00018`. ARS: `ARS-00002`.
- No usar `frappe.throw` para reportar el resultado del import: un throw provoca el rollback del propio reporte.

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `apps/saas_dgii/saas_dgii/saas_dgii/doctype/dgii_settings/dgii_settings.py` | Asignar el próximo NCF sin committear, serializando con un lock de fila. |
| `apps/dashboard_z/dashboard_z/dashboard_z/doctype/invoice_creation_item/invoice_creation_item.json` | Añadir `error_message` a la grilla. |
| `apps/dashboard_z/dashboard_z/dashboard_z/doctype/invoice_creation_tool/invoice_creation_tool.py` | Import en tres fases: validar → crear en una transacción → reportar. |
| `apps/dashboard_z/dashboard_z/dashboard_z/doctype/invoice_creation_tool/invoice_creation_tool.js` | Diálogo de resumen a partir del payload; dejar de ocultar los msgprint. |

---

### Task 1: Allocator de NCF transaccional

**Files:**
- Modify: `apps/saas_dgii/saas_dgii/saas_dgii/doctype/dgii_settings/dgii_settings.py:12-44`
- Test: `<scratchpad>/t1_ncf_rollback.py`

**Interfaces:**
- Consumes: nada.
- Produces: `DGIISettings.get_next_avail_ncf(serie) -> str`. Misma firma y mismo formato de retorno (`'B02' + 8 dígitos`) que hoy. Cambia el contrato transaccional: ya **no** committea, y el número queda reservado con lock hasta que la transacción del llamador termine.

- [ ] **Step 1: Respaldar la app (no tiene git)**

```bash
cp -a /home/tzcode/frappe-bench/apps/saas_dgii /home/tzcode/frappe-bench/apps/saas_dgii.bak-2026-08-03
ls -d /home/tzcode/frappe-bench/apps/saas_dgii.bak-2026-08-03
```

- [ ] **Step 2: Escribir la prueba que falla**

Crear `<scratchpad>/t1_ncf_rollback.py`:

```python
import frappe

SERIE = "B02.########"
settings = frappe.get_doc("DGII Settings", "PHY-00018")
cfg_name = frappe.db.get_value(
    "NCF Configuration", {"parent": settings.name, "ncf_type": SERIE}, "name"
)

def counter():
    return frappe.db.get_value("NCF Configuration", cfg_name, "current")

before = counter()
ncf = settings.get_next_avail_ncf(SERIE)
during = counter()
frappe.db.rollback()
after = counter()

print("NCF entregado:", ncf)
print("contador antes=%s durante=%s despues_del_rollback=%s" % (before, during, after))
assert during == before + 1, "el contador debio avanzar dentro de la transaccion"
assert after == before, "FALLO: el rollback no libero el NCF (hubo commit intermedio)"
print("OK: el rollback libera el NCF")
```

- [ ] **Step 3: Ejecutarla para verificar que falla**

Run:
```bash
cd /home/tzcode/frappe-bench && echo "exec(open('<scratchpad>/t1_ncf_rollback.py').read())" | bench --site asicorp.tzcode.tech console
```
Expected: `AssertionError: FALLO: el rollback no libero el NCF (hubo commit intermedio)`.

Si el contador quedó avanzado por esta corrida, devolverlo a su valor original antes de seguir:
```bash
cd /home/tzcode/frappe-bench && echo "exec(open('<scratchpad>/t1_reset.py').read())" | bench --site asicorp.tzcode.tech console
```
con `<scratchpad>/t1_reset.py`:
```python
import frappe
cfg = frappe.db.get_value("NCF Configuration",
    {"parent": "PHY-00018", "ncf_type": "B02.########"}, ["name", "current"], as_dict=1)
print("actual:", cfg)
# ajustar VALOR_ORIGINAL al valor impreso como "contador antes" en el paso 3
VALOR_ORIGINAL = 20715
frappe.db.set_value("NCF Configuration", cfg.name, "current", VALOR_ORIGINAL, update_modified=False)
frappe.db.commit()
print("restaurado a", frappe.db.get_value("NCF Configuration", cfg.name, "current"))
```

- [ ] **Step 4: Implementar**

En `dgii_settings.py`, reemplazar el cuerpo de `get_next_avail_ncf` desde `row = row[0]` hasta el `return`:

```python
		row = row[0]

		# Lock the counter row for the rest of the transaction. Two invoices for
		# the same physician serialise here instead of racing on a stale in-memory
		# copy. Deliberately no commit: if the caller rolls back, the number is
		# released instead of burnt, so the fiscal sequence keeps no gaps.
		cfg = frappe.db.sql(
			"""SELECT `current`, `max` FROM `tabNCF Configuration` WHERE name = %s FOR UPDATE""",
			row.name,
			as_dict=True,
		)[0]

		if cint(cfg.current) >= cint(cfg.max):
			frappe.throw(
				_("Serie {} reached it's limit please reload".format(serie))
			)

		new_seq = cint(cfg.current)
		frappe.db.set_value(
			"NCF Configuration", row.name, "current", new_seq + 1, update_modified=False
		)
		row.current = new_seq + 1   # keep the in-memory child row in sync

		return '{0}{1:08d}'.format(serie.split(".")[0], new_seq)
```

Borrar también la línea `frappe.errprint(row)` (ensucia `web.error.log` en cada factura).

- [ ] **Step 5: Recargar workers**

```bash
MASTER=$(ps -eo pid,ppid,cmd | grep "[f]rappe-bench/env/bin/gunicorn" | awk '{print $2}' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
kill -HUP "$MASTER" && echo "workers recargados (master $MASTER)"
```

- [ ] **Step 6: Ejecutar la prueba y verificar que pasa**

Run:
```bash
cd /home/tzcode/frappe-bench && echo "exec(open('<scratchpad>/t1_ncf_rollback.py').read())" | bench --site asicorp.tzcode.tech console
```
Expected: `OK: el rollback libera el NCF`.

- [ ] **Step 7: Verificar que una factura real se sigue creando con NCF correlativo**

Esto comprueba que el allocator sigue sirviendo al flujo normal de facturación (el hook
`saas_dgii.hook.sales_invoice.autoname`), no sólo en aislamiento.

Crear `<scratchpad>/t1_factura_real.py`:

```python
import frappe

frappe.set_user("bfortuna@asicorprd.com")
cfg_name = frappe.db.get_value("NCF Configuration",
    {"parent": "PHY-00018", "ncf_type": "B02.########"}, "name")
before = frappe.db.get_value("NCF Configuration", cfg_name, "current")

# se clona una factura ya emitida del mismo medico: reproduce el camino real
# de creacion (autoname -> get_next_avail_ncf) sin inventar datos
plantilla = frappe.db.get_value("Sales Invoice",
    {"physician": "PHY-00018", "docstatus": 1, "naming_series": "B02.########"},
    "name", order_by="creation desc")

try:
    nueva = frappe.copy_doc(frappe.get_doc("Sales Invoice", plantilla))
    nueva.authorization_no = "PRUEBA-T1"
    nueva.insert()
    print("factura de prueba:", nueva.name, "ncf:", nueva.ncf)
    assert nueva.ncf == "B02%08d" % before, \
        "esperaba el NCF %s, dio %s" % ("B02%08d" % before, nueva.ncf)
    assert frappe.db.get_value("NCF Configuration", cfg_name, "current") == before + 1
    print("OK: el flujo normal sigue asignando NCF correlativo")
finally:
    frappe.db.rollback()

despues = frappe.db.get_value("NCF Configuration", cfg_name, "current")
assert despues == before, "FALLO: el contador quedo en %s y debia volver a %s" % (despues, before)
assert not frappe.db.exists("Sales Invoice", {"authorization_no": "PRUEBA-T1"}), \
    "FALLO: la factura de prueba sobrevivio al rollback"
print("OK: el rollback deshizo la factura de prueba y devolvio el contador")
```

Run el comando de consola habitual.
Expected: `OK: el flujo normal sigue asignando NCF correlativo` y
`OK: el rollback deshizo la factura de prueba y devolvio el contador`.

- [ ] **Step 8: Registrar el cambio (no hay git en esta app)**

```bash
diff -u /home/tzcode/frappe-bench/apps/saas_dgii.bak-2026-08-03/saas_dgii/saas_dgii/doctype/dgii_settings/dgii_settings.py \
        /home/tzcode/frappe-bench/apps/saas_dgii/saas_dgii/saas_dgii/doctype/dgii_settings/dgii_settings.py \
        > /home/tzcode/frappe-bench/apps/dashboard_z/docs/superpowers/plans/2026-08-03-saas_dgii-ncf.patch
```
El patch queda versionado dentro de `dashboard_z`, que sí es repo. Se commitea en la Task 2.

---

### Task 2: Campo `error_message` en Invoice Creation Item

**Files:**
- Modify: `apps/dashboard_z/dashboard_z/dashboard_z/doctype/invoice_creation_item/invoice_creation_item.json`
- Test: `<scratchpad>/t2_campo.py`

**Interfaces:**
- Consumes: nada.
- Produces: campo `error_message` (Small Text, `read_only=1`, `in_list_view=1`) en el doctype `Invoice Creation Item`, escribible como `row.error_message`. La Task 4 lo usa.

- [ ] **Step 1: Escribir la prueba que falla**

Crear `<scratchpad>/t2_campo.py`:

```python
import frappe
meta = frappe.get_meta("Invoice Creation Item")
field = meta.get_field("error_message")
assert field is not None, "FALLO: el campo error_message no existe"
assert field.fieldtype == "Small Text", "fieldtype inesperado: %s" % field.fieldtype
assert field.read_only == 1, "error_message debe ser de solo lectura"
print("OK: error_message existe y es Small Text de solo lectura")
```

- [ ] **Step 2: Ejecutarla para verificar que falla**

Run el comando de consola habitual con `t2_campo.py`.
Expected: `AssertionError: FALLO: el campo error_message no existe`.

- [ ] **Step 3: Añadir el campo al JSON**

Este doctype usa el formato antiguo: **no tiene `field_order`** y cada campo lleva todas sus
propiedades explícitas. El orden lo da el array `fields`. Añadir este objeto al final del array
`fields`, después del de `status` (que necesitará una coma al cierre):

```json
  {
   "allow_bulk_edit": 0,
   "allow_on_submit": 0,
   "bold": 0,
   "collapsible": 0,
   "columns": 0,
   "fieldname": "error_message",
   "fieldtype": "Small Text",
   "hidden": 0,
   "ignore_user_permissions": 0,
   "ignore_xss_filter": 0,
   "in_filter": 0,
   "in_global_search": 0,
   "in_list_view": 1,
   "in_standard_filter": 0,
   "label": "Error",
   "length": 0,
   "no_copy": 0,
   "permlevel": 0,
   "precision": "",
   "print_hide": 0,
   "print_hide_if_no_value": 0,
   "read_only": 1,
   "remember_last_selected_value": 0,
   "report_hide": 0,
   "reqd": 0,
   "search_index": 0,
   "set_only_once": 0,
   "unique": 0
  }
```

Comprobar que el archivo sigue siendo JSON válido antes de continuar:
```bash
python3 -m json.tool /home/tzcode/frappe-bench/apps/dashboard_z/dashboard_z/dashboard_z/doctype/invoice_creation_item/invoice_creation_item.json > /dev/null && echo "JSON valido"
```

- [ ] **Step 4: Aplicar el doctype al sitio**

```bash
cd /home/tzcode/frappe-bench && bench --site asicorp.tzcode.tech reload-doc dashboard_z doctype invoice_creation_item
```

- [ ] **Step 5: Ejecutar la prueba y verificar que pasa**

Run el comando de consola habitual con `t2_campo.py`.
Expected: `OK: error_message existe y es Small Text de solo lectura`.

- [ ] **Step 6: Commit**

```bash
cd /home/tzcode/frappe-bench/apps/dashboard_z
git add dashboard_z/dashboard_z/doctype/invoice_creation_item/invoice_creation_item.json docs/superpowers/plans/
git commit -m "Agrega error_message por fila al Invoice Creation Item

El import necesita decir que fallo en cada fila, no solo que fallo. Incluye
tambien el plan de implementacion y el patch de saas_dgii, que no es repo git."
```

---

### Task 3: Fase 1 — validación sin escritura

**Files:**
- Modify: `apps/dashboard_z/dashboard_z/dashboard_z/doctype/invoice_creation_tool/invoice_creation_tool.py:142-291`
- Test: `<scratchpad>/t3_validacion.py`

**Interfaces:**
- Consumes: `error_message` de la Task 2.
- Produces:
  - `InvoiceCreationTool._import_context() -> frappe._dict` con las llaves `company`, `income_account`, `receivable_account`, `expense_account`, `cash_account`, `avail_ncf`.
  - `InvoiceCreationTool._validate_rows(ctx) -> (to_create: list, duplicated: list, errors: list[dict])`. Cada error es `{"idx": int, "customer": str, "authorization_no": str, "message": str}`.
  - `InvoiceCreationTool._row_error(row, message) -> dict` con esa misma forma.
  - `invoice_exists(authorization_no: str) -> bool` a nivel de módulo, que reemplaza a `exists(row)`.
  La Task 4 consume las cuatro.

- [ ] **Step 1: Escribir la prueba que falla**

Crear `<scratchpad>/t3_validacion.py`:

```python
import frappe

tool = frappe.get_doc("Invoice Creation Tool")
ctx = tool._import_context()
print("contexto:", {k: ctx[k] for k in ("company", "avail_ncf")})
assert ctx.company, "falta la compania"
assert ctx.receivable_account, "falta la cuenta por cobrar"

to_create, duplicated, errors = tool._validate_rows(ctx)
print("a crear=%d duplicadas=%d errores=%d" % (len(to_create), len(duplicated), len(errors)))
assert not errors, "el CSV actual es valido, no debio dar errores: %s" % errors
assert len(to_create) + len(duplicated) == len(tool.invoices), "no se clasificaron todas las filas"

# el lote de hoy ya esta importado: 58 duplicadas y 2 por crear
assert len(duplicated) == 58, "esperaba 58 duplicadas, dio %d" % len(duplicated)
assert len(to_create) == 2, "esperaba 2 por crear, dio %d" % len(to_create)

# y validar no debe haber escrito nada
assert frappe.db.get_value("Sales Invoice", {"authorization_no": "1918141148"}) is None, \
    "FALLO: la validacion creo una factura"
print("OK: la validacion clasifica sin escribir")
frappe.db.rollback()
```

- [ ] **Step 2: Ejecutarla para verificar que falla**

Run el comando de consola habitual con `t3_validacion.py`.
Expected: `AttributeError: 'InvoiceCreationTool' object has no attribute '_import_context'`.

- [ ] **Step 3: Implementar el contexto y la validación**

En `invoice_creation_tool.py`, añadir a la clase `InvoiceCreationTool` (antes de `import_invoices`):

```python
	def _import_context(self):
		"""Everything the import needs that does not change from row to row."""
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		income_account, receivable_account, expense_account, cash_account = frappe.get_value(
			"Company",
			company,
			["default_income_account", "default_receivable_account",
			 "default_expense_account", "default_cash_account"],
		)

		return frappe._dict({
			"company": company,
			"income_account": income_account,
			"receivable_account": receivable_account,
			"expense_account": expense_account,
			"cash_account": cash_account,
			"avail_ncf": frappe.get_doc("DGII Settings", self.physician).get_remaining_ncf("B02.########"),
		})

	def _row_error(self, row, message):
		return {
			"idx": row.idx,
			"customer": row.customer or "",
			"authorization_no": str(row.authorization_no or "").strip(),
			"message": message,
		}

	def _validate_rows(self, ctx):
		"""Classify every row before anything is written.

		A duplicate is not an error: it is an authorization already invoiced, so
		we skip it. That is what makes retrying a half-done batch safe.
		"""
		pattern = re.compile(r"^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$")
		to_create, duplicated, errors = [], [], []
		seen = set()

		for row in self.invoices:
			authorization_no = str(row.authorization_no or "").strip()
			row_date = str(row.date or "")
			problem = None

			if not str(row.customer or "").strip():
				problem = _("Falta el nombre del paciente")
			elif not authorization_no:
				problem = _("Falta el no. de autorización")
			elif not row_date:
				problem = _("Falta la fecha")
			elif not pattern.match(row_date):
				problem = _("Fecha inválida: {0}").format(row_date)
			elif row_date > nowdate():
				problem = _("La fecha {0} es futura").format(row_date)
			elif row.ars and not frappe.db.exists("Customer", row.ars):
				problem = _("La ARS {0} no existe como cliente").format(row.ars)
			elif flt(row.claimed) <= 0:
				problem = _("El monto reclamado debe ser mayor que cero")
			elif authorization_no in seen:
				problem = _("El no. de autorización {0} se repite en el archivo").format(authorization_no)

			if problem:
				errors.append(self._row_error(row, problem))
				continue

			seen.add(authorization_no)

			if invoice_exists(authorization_no):
				duplicated.append(row)
			else:
				to_create.append(row)

		if not errors and len(to_create) > ctx.avail_ncf:
			errors.append({
				"idx": 0,
				"customer": "",
				"authorization_no": "",
				"message": _("No hay suficientes B02 para {0}: se necesitan {1} y quedan {2}").format(
					self.physician_name, len(to_create), ctx.avail_ncf
				),
			})

		return to_create, duplicated, errors
```

Y reemplazar la función de módulo `exists(row)` (líneas 282-291) por:

```python
def invoice_exists(authorization_no):
	# dedup by authorization_no (unique per authorization). nss is unreliable due
	# to leading-zero formatting differences between the CSV and stored invoices.
	return bool(frappe.db.exists("Sales Invoice", {
		"authorization_no": authorization_no,
		"docstatus": ["<", 2],
	}))
```

- [ ] **Step 4: Recargar workers**

```bash
MASTER=$(ps -eo pid,ppid,cmd | grep "[f]rappe-bench/env/bin/gunicorn" | awk '{print $2}' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
kill -HUP "$MASTER" && echo "workers recargados"
```

- [ ] **Step 5: Ejecutar la prueba y verificar que pasa**

Run el comando de consola habitual con `t3_validacion.py`.
Expected: `OK: la validacion clasifica sin escribir`, con `a crear=2 duplicadas=58 errores=0`.

- [ ] **Step 6: Probar que detecta filas malas**

Crear `<scratchpad>/t3_filas_malas.py`:

```python
import frappe

tool = frappe.get_doc("Invoice Creation Tool")
ctx = tool._import_context()

tool.invoices[0].customer = ""                    # paciente vacio
tool.invoices[1].date = "2030-01-01"              # fecha futura
tool.invoices[2].ars = "ARS-QUE-NO-EXISTE"        # ARS inexistente
tool.invoices[3].claimed = 0                      # monto cero

to_create, duplicated, errors = tool._validate_rows(ctx)
for e in errors:
    print("fila %s -> %s" % (e["idx"], e["message"]))
assert len(errors) == 4, "esperaba 4 errores, dio %d" % len(errors)
print("OK: la validacion detecta las 4 filas malas")
frappe.db.rollback()
```

Run el comando de consola habitual.
Expected: cuatro líneas de error y `OK: la validacion detecta las 4 filas malas`.

- [ ] **Step 7: Commit**

```bash
cd /home/tzcode/frappe-bench/apps/dashboard_z
git add dashboard_z/dashboard_z/doctype/invoice_creation_tool/invoice_creation_tool.py
git commit -m "Valida las filas del lote antes de crear ninguna factura

_validate_rows recorre el CSV sin escribir y clasifica cada fila en crear,
duplicada o error. Los duplicados por authorization_no se omiten en vez de
abortar, que es lo que permite reintentar un lote a medias sin duplicar."
```

---

### Task 4: Fase 2 y 3 — creación transaccional y reporte

**Files:**
- Modify: `apps/dashboard_z/dashboard_z/dashboard_z/doctype/invoice_creation_tool/invoice_creation_tool.py`
- Test: `<scratchpad>/t4_atomicidad.py`

**Interfaces:**
- Consumes: `_import_context`, `_validate_rows`, `_row_error`, `invoice_exists` de la Task 3; `error_message` de la Task 2.
- Produces: `InvoiceCreationTool.import_invoices()` (whitelisted) devuelve
  `{"ok": bool, "created": int, "duplicated": int, "errors": list[dict]}`.
  La Task 5 renderiza ese payload. También `_resolve_patient(row)`, `_create_invoice(row, ctx)`
  y `_report(created, duplicated, errors)` como helpers privados.

- [ ] **Step 1: Escribir la prueba que falla**

Crear `<scratchpad>/t4_atomicidad.py`:

```python
import frappe

frappe.set_user("bfortuna@asicorprd.com")
tool = frappe.get_doc("Invoice Creation Tool")
cfg_name = frappe.db.get_value("NCF Configuration",
    {"parent": "PHY-00018", "ncf_type": "B02.########"}, "name")

ncf_before = frappe.db.get_value("NCF Configuration", cfg_name, "current")
si_before = frappe.db.count("Sales Invoice", {"physician": "PHY-00018"})
pt_before = frappe.db.count("Patient")

# hace reventar la segunda fila: la primera ya se creo, asi que se comprueba
# que el rollback tambien deshace lo que ya estaba escrito
from dashboard_z.dashboard_z.doctype.invoice_creation_tool.invoice_creation_tool import (
    InvoiceCreationTool,
)

original = InvoiceCreationTool._create_invoice
calls = {"n": 0}

def exploding(self, row, ctx):
    calls["n"] += 1
    if calls["n"] == 2:
        frappe.throw("fallo simulado en la fila %s" % row.idx)
    return original(self, row, ctx)

InvoiceCreationTool._create_invoice = exploding
try:
    result = tool.import_invoices()
finally:
    InvoiceCreationTool._create_invoice = original
print("resultado:", result)
assert calls["n"] == 2, "esperaba 2 intentos de creacion, hubo %d" % calls["n"]

ncf_after = frappe.db.get_value("NCF Configuration", cfg_name, "current")
si_after = frappe.db.count("Sales Invoice", {"physician": "PHY-00018"})
pt_after = frappe.db.count("Patient")

assert result["ok"] is False, "debio reportar fallo"
assert result["created"] == 0, "no debio quedar ninguna factura creada, quedaron %d" % result["created"]
assert len(result["errors"]) == 1, "esperaba 1 error, dio %d" % len(result["errors"])
assert "fallo simulado" in result["errors"][0]["message"], result["errors"][0]["message"]
assert si_after == si_before, "FALLO: quedaron facturas (%d -> %d)" % (si_before, si_after)
assert pt_after == pt_before, "FALLO: quedaron pacientes (%d -> %d)" % (pt_before, pt_after)
assert ncf_after == ncf_before, "FALLO: se quemo NCF (%s -> %s)" % (ncf_before, ncf_after)
print("OK: todo o nada, sin facturas, sin pacientes y sin NCF quemados")

# y el estado quedo persistido en la grilla
tool.reload()
marcadas = [r for r in tool.invoices if r.status == "Error"]
assert len(marcadas) == 1, "esperaba 1 fila marcada Error, hay %d" % len(marcadas)
assert marcadas[0].error_message, "la fila con error debe traer el motivo"
print("OK: la fila con error quedo marcada con su motivo:", marcadas[0].error_message)

# _report commitea a proposito, asi que el error simulado quedo grabado en el
# documento de produccion: hay que limpiarlo para no confundir al usuario
for row in tool.invoices:
    row.status, row.error_message = "", ""
tool.flags.ignore_mandatory = True
tool.save()
frappe.db.commit()
print("OK: estado de la grilla limpiado tras la prueba")
```

- [ ] **Step 2: Ejecutarla para verificar que falla**

Run el comando de consola habitual con `t4_atomicidad.py`.
Expected: `TypeError` o `AssertionError` — `import_invoices()` hoy no devuelve nada (`None`), así que revienta en `result["ok"]`.

- [ ] **Step 3: Implementar la creación por fila**

En `invoice_creation_tool.py`, añadir a la clase:

```python
	def _resolve_patient(self, row):
		"""Find the Patient for this row, creating it when it is new."""
		if row.nss and frappe.db.exists("Patient", {"nss": row.nss}):
			return frappe.get_doc("Patient", {"nss": row.nss})

		if frappe.db.exists("Patient", {"patient_name": row.customer}):
			return frappe.get_doc("Patient", {"patient_name": row.customer})

		patient = frappe.new_doc("Patient")
		patient.update({
			# healthcare Patient requires first_name and derives patient_name
			# from it; keep the full name so the lookup above keeps matching
			"first_name": row.customer,
			"patient_name": row.customer,
			"customer_group": "Customers",
			"physician": self.physician,
			"physician_name": self.physician_name,
			"ars": row.ars,
			"ars_name": row.ars_name,
			"sex": 'Femenino',
			"nss": row.nss or "",
		})
		patient.save()
		return patient

	def _create_invoice(self, row, ctx):
		patient = self._resolve_patient(row)

		# legacy/new patients may not be linked to a Customer (Healthcare only
		# auto-links when 'link_customer_to_patient' is on) -> ensure one exists
		if not patient.customer:
			from healthcare.healthcare.doctype.patient.patient import create_customer
			create_customer(patient)
			patient.reload()

		# the invoice's ars/ars_name are fetched from the customer (read-only),
		# so stamp the ARS on the customer or the fetch overwrites it with None
		if row.ars and row.ars != 'PACIENTE PRIVADO':
			frappe.db.set_value("Customer", patient.customer, {
				"ars": row.ars,
				"nombre_ars": row.ars_name,
			}, update_modified=False)

		doc = frappe.new_doc("Sales Invoice")
		doc.update({
			"customer": patient.customer,
			"patient": patient.name,
			"set_posting_time": 1,
			"naming_series": "B02.########",
			"ars": '' if row.ars == 'PACIENTE PRIVADO' else row.ars,
			"ars_name": '' if row.ars == 'PACIENTE PRIVADO' else row.ars_name,
			"invoice_type": 'Private Customers' if not row.ars else 'Insurance Customers',
			"against_income_account": ctx.income_account,
			"posting_date": row.date,
			"authorization_no": str(row.authorization_no).strip(),
			"nss": str(row.nss).strip(),
			"physician": self.physician,
			"physician_name": self.physician_name,
			"clinic": self.clinic.strip(),
			"debit_to": ctx.receivable_account,
			"due_date": add_days(row.date, 20),
			"authorized_amount": flt(row.authorized),
			"claimed_amount": flt(row.claimed),
			"difference_amount": row.difference,
		})

		doc.append("items", {
			"claimed_amount": flt(row.claimed),
			"authorized_amount": flt(row.authorized),
			"difference_amount": row.difference,
			"coverage": 0 if not row.ars else 80.0,
			"qty": 1,
			"print_qty": 1,
			"rate": flt(row.claimed),
			"net_rate": flt(row.claimed),
			"base_rate": flt(row.claimed),
			"amount": flt(row.claimed),
			"net_amount": flt(row.claimed),
			"base_amount": flt(row.claimed),
			"parent": doc.name,
			"conversion_factor": 1,
			"item_name": row.service,
			"description": row.service,
			"uom": "Unidad(es)",
			"expense_account": ctx.expense_account,
			"income_account": ctx.income_account,
		})

		if row.ars:
			doc.append("payments", {
				"account": ctx.cash_account,
				"amount": flt(row.authorized),
				"base_amount": flt(row.authorized),
				"mode_of_payment": "Seguro",
				"type": "Cash",
			})

		doc.append("payments", {
			"account": ctx.cash_account,
			"amount": row.difference,
			"base_amount": row.difference,
			"mode_of_payment": "Efectivo",
			"type": "Cash",
		})

		doc.set_missing_values()
		# crear la factura validada (enviada), no en borrador
		doc.submit()
		return doc
```

- [ ] **Step 4: Implementar el orquestador y el reporte**

Reemplazar por completo el método `import_invoices` por:

```python
	@frappe.whitelist()
	def import_invoices(self):
		ctx = self._import_context()
		to_create, duplicated, errors = self._validate_rows(ctx)

		# nada se escribe si el archivo trae problemas: el lote es todo o nada
		if errors:
			return self._report([], duplicated, errors)

		created = []
		try:
			for row in to_create:
				self._create_invoice(row, ctx)
				created.append(row)
				frappe.publish_realtime(
					'import_invoice_progress',
					{"progress": [len(created), len(to_create),
						"{0} {1}".format(row.authorization_no, row.customer)]},
					doctype="Invoice Creation Tool",
					user=frappe.session.user,
				)
		except Exception as exc:
			# the whole batch shares one transaction, so this undoes the invoices,
			# the patients and the NCF numbers taken so far
			frappe.db.rollback()
			failed_row = to_create[len(created)]
			message = strip_html(str(exc)) or exc.__class__.__name__
			return self._report([], duplicated, [self._row_error(failed_row, message)])

		return self._report(created, duplicated, [])

	def _report(self, created, duplicated, errors):
		"""Persist the per-row outcome and hand a summary to the client.

		Deliberately runs after the rollback and commits on its own: raising
		here (frappe.throw) would roll the report back along with the batch.
		"""
		failed = {e["idx"]: e["message"] for e in errors}
		created_idx = set(row.idx for row in created)
		duplicated_idx = set(row.idx for row in duplicated)

		for row in self.invoices:
			if row.idx in failed:
				row.status, row.error_message = "Error", failed[row.idx]
			elif row.idx in created_idx:
				row.status, row.error_message = "Imported", ""
			elif row.idx in duplicated_idx:
				row.status, row.error_message = "Duplicate", ""
			else:
				row.status, row.error_message = "", ""

		# physician/clinic are mandatory on the doctype; the report must persist regardless
		self.flags.ignore_mandatory = True
		self.save()
		frappe.db.commit()

		return {
			"ok": not errors,
			"created": len(created),
			"duplicated": len(duplicated),
			"errors": errors,
		}
```

- [ ] **Step 5: Añadir el import de `strip_html`**

En la cabecera del archivo, cambiar:
```python
from frappe.utils import nowdate, add_days, flt
```
por:
```python
from frappe.utils import nowdate, add_days, flt, strip_html
```

- [ ] **Step 6: Recargar workers**

```bash
MASTER=$(ps -eo pid,ppid,cmd | grep "[f]rappe-bench/env/bin/gunicorn" | awk '{print $2}' | sort | uniq -c | sort -rn | head -1 | awk '{print $2}')
kill -HUP "$MASTER" && echo "workers recargados"
```

- [ ] **Step 7: Ejecutar la prueba de atomicidad y verificar que pasa**

Run el comando de consola habitual con `t4_atomicidad.py`.
Expected: `OK: todo o nada, sin facturas, sin pacientes y sin NCF quemados` y `OK: la fila con error quedo marcada con su motivo: ...`.

- [ ] **Step 8: Verificar la idempotencia**

Crear `<scratchpad>/t4_idempotencia.py`:

```python
import frappe

frappe.set_user("bfortuna@asicorprd.com")
tool = frappe.get_doc("Invoice Creation Tool")
ctx = tool._import_context()
to_create, duplicated, errors = tool._validate_rows(ctx)
assert len(duplicated) == 58, "esperaba 58 duplicadas, dio %d" % len(duplicated)
assert not errors, errors
print("OK: las 58 ya importadas se reconocen como duplicadas y no se recrean")
frappe.db.rollback()
```

Run el comando de consola habitual.
Expected: `OK: las 58 ya importadas se reconocen como duplicadas y no se recrean`.

- [ ] **Step 9: Commit**

```bash
cd /home/tzcode/frappe-bench/apps/dashboard_z
git add dashboard_z/dashboard_z/doctype/invoice_creation_tool/invoice_creation_tool.py
git commit -m "El import de facturas es todo o nada y reporta por fila

El lote entero corre en una transaccion: se quitan el commit por paciente y el
reset de rollback_observers, de modo que cualquier fallo deshace facturas,
pacientes y NCF. El resultado se persiste por fila y se devuelve al cliente en
vez de lanzarse con frappe.throw, que haria rollback del propio reporte."
```

---

### Task 5: Diálogo de resumen en el cliente

**Files:**
- Modify: `apps/dashboard_z/dashboard_z/dashboard_z/doctype/invoice_creation_tool/invoice_creation_tool.js`

**Interfaces:**
- Consumes: el payload `{ok, created, duplicated, errors}` de `import_invoices` (Task 4).
- Produces: nada que consuman otras tareas.

- [ ] **Step 1: Añadir el renderizador del resumen**

Al inicio del archivo, después de la línea de licencia y antes de `frappe.ui.form.on`, insertar:

```js
const show_import_summary = message => {
	if (!message) return;

	if (message.ok) {
		frappe.msgprint({
			title: __("Importación completada"),
			indicator: "green",
			message: __("{0} factura(s) creada(s), {1} omitida(s) por estar ya registradas.",
				[message.created, message.duplicated])
		});
		return;
	}

	const rows = (message.errors || []).map(e => `
		<tr>
			<td>${e.idx || "-"}</td>
			<td>${frappe.utils.escape_html(e.customer || "")}</td>
			<td>${frappe.utils.escape_html(e.authorization_no || "")}</td>
			<td>${frappe.utils.escape_html(e.message || "")}</td>
		</tr>`).join("");

	frappe.msgprint({
		title: __("No se importó ninguna factura"),
		indicator: "red",
		message: `
			<p>${__("El lote es todo o nada: se encontraron {0} problema(s), así que no se creó ninguna factura. Corrija el archivo y vuelva a cargarlo.", [(message.errors || []).length])}</p>
			<table class="table table-bordered">
				<thead>
					<tr>
						<th>${__("Fila")}</th>
						<th>${__("Paciente")}</th>
						<th>${__("Autorización")}</th>
						<th>${__("Problema")}</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>`
	});
};
```

- [ ] **Step 2: Mostrar el resumen al terminar el import**

Reemplazar el handler `final_step` por:

```js
	final_step: frm => {
		frm.page.set_primary_action(__("Import Invoices"), function() {
			// freeze the whole UI immediately so a second click can't create duplicates
			frappe.dom.freeze(__("Importando facturas... Por favor espere y no cierre ni recargue la página."));
			frm.call("import_invoices").then(
				r => frm.reload_doc().then(() => {
					frappe.dom.unfreeze();
					show_import_summary(r.message);
				}),
				() => frappe.dom.unfreeze()   // on failure, always release the freeze
			);
		});
	}
```

- [ ] **Step 3: Dejar de ocultar los diálogos de error**

En el handler `add_realtime_listeners`, borrar la línea:

```js
					frappe.hide_msgprint(true);
```

Oculta cualquier msgprint abierto en cada evento de progreso, incluidos los de error.

- [ ] **Step 4: Verificar en el navegador**

Abrir https://asicorp.tzcode.tech/desk/invoice-creation-tool/Invoice%20Creation%20Tool, recargar con Ctrl+Shift+R y pulsar **Import Invoices**.
Expected: el diálogo verde "Importación completada" indicando 2 creadas y 58 omitidas, y la grilla mostrando la columna Error vacía y los status `Imported`/`Duplicate`.

Nota: es la corrida real que crea las 2 facturas faltantes de la Task 6. Si se prefiere separarlas, ejecutar antes el paso de cancelación.

- [ ] **Step 5: Commit**

```bash
cd /home/tzcode/frappe-bench/apps/dashboard_z
git add dashboard_z/dashboard_z/doctype/invoice_creation_tool/invoice_creation_tool.js
git commit -m "Muestra el resultado del import al usuario

Renderiza el payload de import_invoices: en verde el conteo de creadas y
omitidas, en rojo la tabla de filas con su motivo. Quita el hide_msgprint del
handler de progreso, que ocultaba los propios dialogos de error."
```

---

### Task 6: Corrección del estado actual

**Files:**
- Test: `<scratchpad>/t6_cancelar.py`, `<scratchpad>/t6_verificar.py`

**Interfaces:**
- Consumes: el import corregido de las Tasks 3-5.
- Produces: 60 facturas visibles en "Cargar Facturas" para PHY-00018 + ARS-00002, y el listado de NCF anulados.

- [ ] **Step 1: Escribir la verificación del estado objetivo**

Crear `<scratchpad>/t6_verificar.py`:

```python
import frappe

n = frappe.db.count("Sales Invoice", {
    "docstatus": 1,
    "customer_group": "Customers",
    "invoice_type": "Insurance Customers",
    "clinic": "CENTRO ORIENTAL DE GINECOLOGIA",
    "physician": "PHY-00018",
    "ars": "ARS-00002",
    "payment_status": "UNPAID",
})
print("facturas visibles en el dialogo:", n)
assert n == 60, "esperaba 60, hay %d" % n
print("OK: quedan exactamente las 60 del lote")
```

- [ ] **Step 2: Ejecutarla para verificar que falla**

Run el comando de consola habitual con `t6_verificar.py`.
Expected: `AssertionError: esperaba 60, hay 93` (o 95 si la Task 5 ya creó las 2 faltantes).

- [ ] **Step 3: Cancelar las 35 del lote de julio y exportar los NCF anulados**

Crear `<scratchpad>/t6_cancelar.py`:

```python
import frappe

frappe.set_user("Administrator")

objetivo = frappe.db.sql("""
    SELECT si.name, si.ncf, si.posting_date, si.grand_total, si.customer_name
    FROM `tabSales Invoice` si
    WHERE si.docstatus = 1
      AND si.physician = 'PHY-00018'
      AND si.ars = 'ARS-00002'
      AND si.clinic = 'CENTRO ORIENTAL DE GINECOLOGIA'
      AND si.invoice_type = 'Insurance Customers'
      AND si.payment_status = 'UNPAID'
      AND DATE(si.creation) IN ('2026-07-06', '2026-07-07')
    ORDER BY si.ncf
""", as_dict=True)

print("a cancelar: %d facturas, RD$%s" % (len(objetivo), sum(r.grand_total for r in objetivo)))
assert len(objetivo) == 35, "esperaba 35, la consulta dio %d - REVISAR ANTES DE SEGUIR" % len(objetivo)

ruta = "/home/tzcode/frappe-bench/apps/dashboard_z/docs/superpowers/plans/2026-08-03-ncf-anulados.csv"
with open(ruta, "w") as fh:
    fh.write("ncf,fecha,paciente,monto,factura\n")
    for r in objetivo:
        fh.write("%s,%s,%s,%s,%s\n" % (
            r.ncf, r.posting_date, (r.customer_name or "").replace(",", " "), r.grand_total, r.name))
print("listado de NCF anulados escrito en", ruta)

for r in objetivo:
    doc = frappe.get_doc("Sales Invoice", r.name)
    doc.cancel()
    print("cancelada", r.name, r.ncf)

frappe.db.commit()
print("LISTO: %d facturas canceladas" % len(objetivo))
```

Run el comando de consola habitual.
Expected: 35 líneas `cancelada ...` y `LISTO: 35 facturas canceladas`.

**Es irreversible.** Si el assert del conteo falla, detenerse y revisar antes de continuar.

- [ ] **Step 4: Crear las 2 faltantes**

Si la Task 5 no las creó ya, abrir la herramienta en el navegador y pulsar **Import Invoices**.
Expected: diálogo verde con 2 creadas y 58 omitidas.

- [ ] **Step 5: Ejecutar la verificación y comprobar que pasa**

Run el comando de consola habitual con `t6_verificar.py`.
Expected: `OK: quedan exactamente las 60 del lote`.

- [ ] **Step 6: Comprobar el resultado desde la interfaz**

Abrir una factura de proveedor del ARS SENASA y pulsar **Cargar Facturas**.
Expected: el diálogo lista 60 facturas.

- [ ] **Step 7: Commit**

```bash
cd /home/tzcode/frappe-bench/apps/dashboard_z
git add docs/superpowers/plans/2026-08-03-ncf-anulados.csv
git commit -m "Listado de NCF anulados del lote de julio de PHY-00018

35 facturas canceladas para que Cargar Facturas muestre solo el lote vigente
de 60. El CSV va para el reporte 608 de contabilidad."
```

---

## Notas de riesgo

- **Contención del lock**: mientras corre un import, otro usuario creando una factura del **mismo médico** espera. El `innodb_lock_wait_timeout` por defecto es 50 s y el lote de 60 tarda ~40 s. Vigilar tras el despliegue; si aparece `Lock wait timeout exceeded`, el siguiente paso es mover el import a un background job.
- **`saas_dgii` sin git**: el respaldo de la Task 1 y el `.patch` versionado en `dashboard_z` son la única forma de revertir.
- **Cancelación irreversible**: la Task 6 cancela 35 facturas enviadas y quema sus NCF. Ya se verificó que no tienen Payment Entries, ni facturas de proveedor que las referencien, ni asientos de diario.
