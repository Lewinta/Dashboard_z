import frappe

def get_physician_id(physician):
	return frappe.get_value("Physician", {"user_id": physician}, "name")