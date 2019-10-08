import frappe
from frappe import _

def on_submit(doc, event):

	if not doc.invoice_type:
		frappe.throw(_("Please set Invoice Type before proceed!"))

	if not doc.physician:
		frappe.throw(_("Please set Physician before proceed!"))

	if not doc.clinic:
		frappe.throw(_("Please set Clinic before proceed!"))
