import frappe
from frappe import _

def validate(doc, event):
	validate_authorization_no(doc)

def on_submit(doc, event):
	if not doc.invoice_type:
		frappe.throw(_("Please set Invoice Type before proceed!"))

	if not doc.physician:
		frappe.throw(_("Please set Physician before proceed!"))

	if not doc.clinic and doc.invoice_type != "Suppliers":
		frappe.throw(_("Please set Clinic before proceed!"))

	update_invoices(doc, event)

def update_invoices(doc, event):
	for item in doc.items:
		for name in (item.paid_sales_invoices or "").split(","):
			if not name: return

			doc = frappe.get_doc("Sales Invoice", name)
			# update payment_status [PAID|PARTIALLY PAID|UNPAID]
			doc.payment_status = "UNPAID" if doc.get("is_return") else "PAID"

			doc.db_update()

	frappe.db.commit()

def on_cancel(doc, event):
	for item in doc.items:
		for name in (item.paid_sales_invoices or "").split(","):
			if not name: return
			if not frappe.db.exists("Sales Invoice", name):
				continue
			doc = frappe.get_doc("Sales Invoice", name)

			# update payment_status [PAID|PARTIALLY PAID|UNPAID]
			doc.payment_status = "PAID" if doc.get("is_return") else "UNPAID"

			doc.db_update()

	frappe.db.commit()

@frappe.whitelist()
def get_parent_invoice(name):
	if not name:
		return False

	data =  frappe.db.sql("""
		SELECT
			`tabSales Invoice Item`.parent
		FROM
			`tabSales Invoice Item`
		WHERE 
			`tabSales Invoice Item`.docstatus < 2
		AND
			`tabSales Invoice Item`.paid_sales_invoices like '%{}%'
		""".format(name))
	if data:
		return data[0][0]
	else:
		return False

def validate_authorization_no(doc):
	# Let's validate there is no other invoice with the same
	# authorization_no same ARS and same docstatus
	filters = {
		"ars": doc.ars,
		"authorization_no": doc.authorization_no,
		"invoice_type": "Insurance Customers",
		"docstatus": ["<=", 1],
	}
	invoice_qty = frappe.db.count("Sales Invoice", filters)

	if invoice_qty > 1:
		frappe.throw(_(u"""Ya existe una factura con el numero de autorizacion 
			<b>{authorization_no}</b> en la ARS <b>{ars_name}</b> """.format(**doc.as_dict())
		))



