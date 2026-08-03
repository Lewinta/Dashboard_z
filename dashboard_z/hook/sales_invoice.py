import frappe
from frappe import _

def validate_ncf_length(doc):
	return
	ncf = (doc.ncf or "").strip()
	if not ncf:
		return
	# E-NCF (electrónico) -> 13 caracteres | B-NCF -> 11 caracteres
	if ncf.startswith("E") and len(ncf) != 13:
		frappe.throw(_("El NCF <b>{0}</b> inicia con E y debe tener 13 caracteres (tiene {1}).").format(ncf, len(ncf)))
	if ncf.startswith("B") and len(ncf) != 11:
		frappe.throw(_("El NCF <b>{0}</b> inicia con B y debe tener 11 caracteres (tiene {1}).").format(ncf, len(ncf)))

def validate(doc, event):
	validate_ncf_length(doc)
	validate_authorization_no(doc)

	if doc.invoice_type == "Suppliers":
		validate_duplicate_ncf(doc)
	else:
		validate_duplicated_claims(doc)

def on_submit(doc, event):
	if not doc.invoice_type:
		frappe.throw(_("Please set Invoice Type before proceed!"))

	if not doc.physician:
		frappe.throw(_("Please set Physician before proceed!"))

	if not doc.clinic and doc.invoice_type != "Suppliers":
		frappe.throw(_("Please set Clinic before proceed!"))

	update_invoices(doc, event)

	if not doc.invoice_type == "Suppliers":
		return

	if not doc.items[0].paid_sales_invoices:
		return
		
	for name in doc.items[0].paid_sales_invoices.split(','):
		d = frappe.get_doc("Sales Invoice", name)
		if d.docstatus == 0:
			d.submit()  

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
	from frappe import _
	# Let's validate there is no other invoice with the same
	# authorization_no same ARS and same docstatus
	filters = {
		"ars": doc.ars,
		"authorization_no": doc.authorization_no,
		"invoice_type": "Insurance Customers",
		"docstatus": ["!=", 2],
	}
	invoice_qty = frappe.db.count("Sales Invoice", filters)

	if invoice_qty > 1:
		frappe.throw(_(u"""Ya existe una factura con el numero de autorizacion 
			<b>{authorization_no}</b> en la ARS <b>{ars_name}</b> """.format(**doc.as_dict())
		))

def validate_duplicate_ncf(doc):
	duplicates = frappe.db.sql("""
		SELECT  
			COUNT(1) qty
		FROM 
			`tabSales Invoice`
		WHERE
			physician = %s
		AND
			ncf = %s
		AND
			docstatus != 2
		GROUP BY 
			ncf
	""", (doc.physician, doc.ncf))

	if duplicates and duplicates[0][0] > 1:
		frappe.throw(_("NCF <b>{ncf}</b>  duplicado para el medico <b>{physician_name}</b>".format(**doc.as_dict())))

def validate_duplicated_claims(doc):
	if not doc.items:
		return

	paid_invs = doc.items[0].paid_sales_invoices 

	if not paid_invs:
		return 

	invoices = paid_invs.split(',')

	if not invoices:
		return
	
	duplicates = frappe.db.sql("""
		SELECT 
			authorization_no, 
			COUNT(1) qty
		FROM 
			`tabSales Invoice`
		WHERE
			name in ({})
		GROUP BY 
			authorization_no, ars
		HAVING
			qty > 1
	""".format("'{}'".format("','".join(invoices))), debug=False, as_dict=True)

	for row in duplicates:
		frappe.throw("El numero de autorizacion <b>{}</b> esta duplicado".format(row.authorization_no))
