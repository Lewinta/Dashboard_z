import frappe
from frappe.utils import flt, cint


@frappe.whitelist()
def supplier_load_invoices(doctype, txt, searchfield, start, page_len, filters, **kwargs):
	"""Results for the 'Cargar Facturas' MultiSelectDialog on supplier invoices.
	Returns name, date, patient name, authorization no. and amount, filtered by
	ARS + posting_date range (from the dialog) plus the static context filters."""
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	filters = filters or {}

	# only validated (submitted) invoices — old migrated drafts must not appear
	conditions = ["si.docstatus = 1"]
	values = {"start": cint(start), "page_len": cint(page_len)}

	for field in ("invoice_type", "customer_group", "clinic", "physician", "ars", "payment_status"):
		if filters.get(field):
			conditions.append("si.{0} = %({0})s".format(field))
			values[field] = filters.get(field)

	if filters.get("from_date"):
		conditions.append("si.posting_date >= %(from_date)s")
		values["from_date"] = filters.get("from_date")
	if filters.get("to_date"):
		conditions.append("si.posting_date <= %(to_date)s")
		values["to_date"] = filters.get("to_date")

	if txt:
		conditions.append("(si.name LIKE %(txt)s OR si.patient LIKE %(txt)s OR si.authorization_no LIKE %(txt)s)")
		values["txt"] = "%{0}%".format(txt)

	return frappe.db.sql(
		"""
		SELECT
			si.name AS name,
			si.posting_date AS fecha,
			COALESCE(pt.patient_name, si.patient) AS paciente,
			si.authorization_no AS autorizacion,
			FORMAT(si.grand_total, 2) AS monto
		FROM `tabSales Invoice` si
		LEFT JOIN `tabPatient` pt ON pt.name = si.patient
		WHERE {conditions}
		ORDER BY si.posting_date DESC
		LIMIT %(start)s, %(page_len)s
		""".format(conditions=" AND ".join(conditions)),
		values,
		as_dict=kwargs.get("as_dict", 1) or 1,
	)

def item_by_ars(doctype, txt, searchfield, start, page_len, filters):

	if not filters.get("ars"): 
		return frappe.get_list("Item", filters={
			"item_code": ["not in", "Consultas, ALQUILER"]
		}, fields=["item_code"], as_list=True)

	result = frappe.db.sql("""
		SELECT
			item_code AS item,
			item_name,
			ars_name AS ars,
			physician_name AS physician,
			currency,
			price_list_rate AS price
		FROM
			`tabItem Price` AS price 
		WHERE
			price_list = '{1}'
		AND
			physician = '{2}'
		AND
			(item_code LIKE '%{0}%' OR item_name LIKE '%{0}%')
		AND
			item_code != 'Reclamaciones'
		ORDER BY item_code LIMIT 20
	""".format("%".join(txt.split()), filters.get("ars"), filters.get("physician")), as_dict=True)

	return [[row.item, "{1} $ {0}".format(flt(row.price, 2), row.currency), row.item_name] for row in result]

@frappe.whitelist()
def customer_query(doctype, txt, searchfield, start, page_len, filters, **kwargs):
	txt = "%".join(txt.split())

	customer_list = frappe.get_list("Customer", {
		"name": ["like", "%{}%".format(txt) if txt else "%"],
		"customer_group": filters.get("customer_group") or "Clientes",
	}, ["name", "customer_group"], order_by="name")

	return [[row.name, row.customer_group] for row in customer_list]
