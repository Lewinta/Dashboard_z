import frappe

import json
from frappe.defaults import get_global_default
from frappe.utils import flt
from frappe import _
def on_session_creation():
	usr_profile = frappe.get_value(
		"User",
		frappe.session.user,
		"role_profile_name"
	)
	
	if usr_profile and usr_profile == "Physician":
		frappe.response["home_page"] = "/dashboard"

@frappe.whitelist()
def update_sales_invoice(doc, selections, args):
	json_object = json.loads(doc)

	sinv = frappe.get_doc(json_object)

	# clear the items table
	sinv.set("items", [])

	total = 0.000

	invoices_qty = len(selections.split(","))

	for name in selections.split(","):
		total += frappe.get_value("Sales Invoice", name, "authorized_amount") or 0.000

	if not frappe.get_value("Item", "Servicios Medicos"):
		create_service_item()

	sinv.append("items", {
		"item_code": "Servicios Medicos",
		"item_name": "Servicios Medicos",
		"description": "Servicios Medicos",
		"item_group": "Servicios",
		"stock_uom": "Unidad(es)",
		"uom": "Unidad(es)",
		"paid_sales_invoices": selections,
		"qty": -1 if sinv.get("is_return") else 1,
		"print_qty": invoices_qty,
		"rate": total,
		"difference_amount": total,
		"amount": total,
		"cobertura": 100
	})

	sinv.set_missing_values()

	return sinv.as_dict()

def invoice_to_claim(sinv_name):
	if not sinv_name:
		frappe.throw(_("Sales Invoice name can't be empty!"))

	fields = [
		"name",
		"posting_date",
		"ars",
		"customer_name",
		"authorization_no",
		"nss",
		"authorized_amount",
		"received_amount",
	]
	sinv = frappe.db.get_value("Sales Invoice", sinv_name, fields, as_dict=True)
	if not sinv:
		frappe.throw("Factura {} no encontrada".format(sinv_name))
	if not sinv.get('ars'):
		frappe.throw("Factura <b> <a href='/desk#Form/Sales%20Invoice/{}'></b> no tiene ARS".format(sinv_name))
	fee = frappe.db.get_value("Customer", sinv.ars, "fee_percentage") / 100.00
	return  {
		"document": sinv.name,
		"date": sinv.posting_date,
		"customer": sinv.customer_name,
		"authorization": sinv.authorization_no,
		"nss": sinv.nss,
		"claimed_amount": flt(sinv.authorized_amount),
		"paid_amount": flt(sinv.received_amount),
		"fee_amount": flt(sinv.authorized_amount) * fee ,
		"pending_amount": sinv.authorized_amount - sinv.received_amount,
		"fee": fee,
	}
	

def create_service_item():
	default_company = get_global_default("company")
	default_income_account = frappe.get_value(
		"Company",
		default_company,
		"default_income_account"
	)
	item = frappe.new_doc("Item")

	item.update({
		"item_code": "Servicios Medicos",
		"item_name": "Servicios Medicos",
		"description": "Servicios Medicos",
		"is_stock_item": 0,
		"is_purchase_item": 0,
		"income_account": default_income_account,
		"item_group": "Servicios"
	})

	item.insert(ignore_permissions=True)
