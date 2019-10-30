import frappe
from frappe import _

def on_submit(doc, event):

	if not doc.invoice_type:
		frappe.throw(_("Please set Invoice Type before proceed!"))

	if not doc.physician:
		frappe.throw(_("Please set Physician before proceed!"))

	if not doc.clinic:
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

			doc = frappe.get_doc("Sales Invoice", name)
			# update payment_status [PAID|PARTIALLY PAID|UNPAID]
			doc.payment_status = "PAID" if doc.get("is_return") else "UNPAID"

			doc.db_update()

	frappe.db.commit()