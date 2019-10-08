import frappe

import json
from frappe.defaults import get_global_default

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
