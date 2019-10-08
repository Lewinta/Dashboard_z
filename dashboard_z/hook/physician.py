import frappe
from frappe.model.naming import make_autoname

def autoname(doc, event):
	doc.name = make_autoname("PHY-.#####")	

def validate(doc, event):
	doc.full_name = "{first_name} {last_name}".format(**doc.as_dict())