import frappe

def after_insert(doc, event):
	if not doc.customer_group == "ARS" or\
		frappe.db.exists("Price List", doc.name):
		return 0 # exit code is zero

	pricls = frappe.new_doc("Price List")

	pricls.update({
		"selling": 1,
		"currency": "DOP",
		"doctype": "Price List",
		"enabled": 1,
		"physician": doc.physician,
		"price_list_name": doc.name
	})

	pricls.append("countries", {
		"country": u"Dominican Republic"
	})

	pricls.save(ignore_permissions=True)

def on_trash(doc, event):
	frappe.delete_doc_if_exists("Price List", doc.name)
	frappe.db.commit()