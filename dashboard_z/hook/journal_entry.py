import frappe
import json
from frappe.utils import flt
def on_cancel(doc, event):
    if not doc.invoice_dict:
        return
    for inv in json.loads(doc.invoice_dict):
        inv = frappe._dict(inv)
        received = frappe.get_value("Sales Invoice", inv.document, "received_amount")
        frappe.set_value("Sales Invoice", inv.document, "received_amount", flt(received) - flt(inv.received_amount))
 