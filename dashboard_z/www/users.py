import frappe

def get_context(context):
	context.update({
		"user_name":frappe.session.user,
		"users":frappe.db.sql("select first_name, email from `tabUser`", as_dict=True),
		"facturas_fiscal": get_fiscal_invoices('PHY-00006')

	})
	console.log(get_fiscal_invoices('PHY-00006'))

	return context

def get_fiscal_invoices(physician):
	return frappe.db.sql("""
		SELECT
			`tabSales Invoice`.ncf,
			`tabSales Invoice`.customer_name,
			`tabSales Invoice`.posting_date,
			`tabJournal Entry`.voucher_type,
			`tabSales Invoice`.grand_total,
			`tabSales Invoice`.paid_amount,
			`tabJournal Entry`.posting_date
		FROM 
			`tabSales Invoice`
		LEFT JOIN
			`tabJournal Entry`
		ON
			`tabSales Invoice`.name = `tabJournal Entry`.reference_name
		AND
			`tabJournal Entry`.docstatus = 1
		AND
			`tabJournal Entry`.reference_name = (SELECT max(j.name) from `tabJournal Entry` j WHERE j.reference_name = `tabJournal Entry`.reference_name)
		WHERE
			`tabSales Invoice`.physician = %s
		AND
			`tabSales Invoice`.invoice_type = 'Suppliers'
		AND
			`tabSales Invoice`.outstanding_amount > 0
		AND
			`tabSales Invoice`.ncf like '%%B01%%'
		AND
			`tabSales Invoice`.docstatus = 1

		""", physician, as_dict=True, debug=True)