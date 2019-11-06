import frappe
from frappe.model.naming import make_autoname
from frappe.permissions import add_user_permission

def autoname(doc, event):
	doc.name = make_autoname("PHY-.#####")	

def validate(doc, event):
	doc.full_name = "{first_name} {last_name}".format(**doc.as_dict())

def after_insert(doc, event):
	create_user(doc, event)
	create_dgii(doc, event)
	create_defaults(doc, event)
	add_permissions(doc, event)

def create_user(doc, event):
	if not doc.email:
		frappe.throw("Please add an email address for this physician")
	
	if frappe.db.exists("User", doc.email):
		frappe.throw("User email already exists!")

	usr = frappe.new_doc("User")

	usr.update({
		u'background_image': '/files/estheto-board-lowquality-mono.jpg',
		u'background_style': u'Fill Screen',
		u'email': doc.email,
		u'enabled': 1,
		u'role_profile_name': 'Physician',
		u'first_name': doc.first_name,
		u'full_name': doc.full_name,
		u'language': u'es',
		u'last_name': doc.last_name,
		u'new_password': 'Admin',
		u'user_type': 'System User',
		u'send_welcome_email': 0,
		u'user_type': u'System User',
		u'username': generate_username(doc)
	})

	usr.save(ignore_permissions=True)

def create_dgii(doc, event):
	import datetime
	
	if frappe.db.exists("DGII Settings", doc.name):
		frappe.throw("DGII Settings already exists!")
	
	year = int(frappe.utils.today()[:4])

	lst = [	
		{
			u'current': 1,
			u'description': u'Facturas con Valor Fiscal',
			u'expiration': datetime.date(year, 12, 31),
			u'max': 100,
			u'ncf_type': u'B01.########',
		},
		{
			u'current': 1,
			u'description': u'Facturas de Consumo',
			u'expiration': datetime.date(year, 12, 31),
			u'max': 1000,
			u'ncf_type': u'B02.########',
		},
		{
			u'current': 1,
			u'description': u'Notas de Credito',
			u'expiration': datetime.date(year, 12, 31),
			u'max': 50,
			u'ncf_type': u'B04.########',
		},
		{
			u'current': 1,
			u'description': u'Gubernamental',
			u'expiration': datetime.date(year, 12, 31),
			u'max': 300,
			u'ncf_type': u'B15.########',
		},
		{
			u'current': 1,
			u'description': u'Regimen Especial',
			u'expiration': datetime.date(year, 12, 31),
			u'max': 100,
			u'ncf_type': u'B14.########',
		}
	]
	
	dgii = frappe.new_doc("DGII Settings")

	dgii.update({
		u'physician': doc.name,
		u'physician_name': doc.full_name
	})

	for ncf in lst:
		dgii.append('ncf', ncf)

	dgii.save(ignore_permissions=True)


def create_defaults(doc, event):
	if frappe.db.exists("Physician Defaults", doc.name):
		frappe.throw("Physician Defaults already exists!")

	default = frappe.new_doc("Physician Defaults")
	
	default.update({
		"physician": doc.name,
		"physician_name": doc.full_name,
		"default_coverage": 80.0,
	})
	
	default.save(ignore_permissions=True)

def add_permissions(doc, event):
	lst = ["Physician Defaults", "DGII Settings", "Physician"]
	
	for doctype in lst:
		add_user_permission(doctype, doc.name, doc.email)

	add_user_permission("Clinic", doc.hospital, doc.email)

def generate_username(doc):
	return "{}_{}".format(doc.first_name.capitalize(), doc.last_name.capitalize())

