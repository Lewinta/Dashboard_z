# -*- coding: utf-8 -*-
# Copyright (c) 2020, TZCODE and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_site_path
from . import UnicodeReader
from frappe.utils import nowdate, add_days, flt
import re
import io


# CSV templates come from mixed Excel exports (UTF-8, Mac Roman, Latin-1/CP1252).
# Auto-detection libraries misread Spanish Mac Roman (0x84 = ñ), so pick the
# decoding that yields the most valid Spanish accented characters.
def read_csv_with_encoding(full_path):
	with open(full_path, "rb") as fh:
		raw = fh.read()

	try:
		return raw.decode("utf-8")
	except UnicodeDecodeError:
		pass

	spanish = set("ñÑáéíóúüÁÉÍÓÚÜ¿¡")
	best_text, best_score = None, None
	for enc in ("mac_roman", "cp1252", "latin-1"):
		try:
			text = raw.decode(enc)
		except UnicodeDecodeError:
			continue
		# reward Spanish letters, penalise control characters (wrong-encoding noise)
		score = sum(1 for c in text if c in spanish) \
			- 5 * sum(1 for c in text if ord(c) < 32 and c not in "\r\n\t")
		if best_score is None or score > best_score:
			best_text, best_score = text, score

	return best_text if best_text is not None else raw.decode("latin-1", "replace")


class InvoiceCreationTool(Document):
	def validate(self):
		self.calculate_totals()
		
	def calculate_totals(self):
		self.total_claimed = self.total_authorized = self.total_difference = .00
		
		for row in self.invoices:
			self.total_claimed += flt(row.claimed)
			self.total_authorized += flt(row.authorized)
			self.total_difference += flt(row.difference)

	@frappe.whitelist()
	def clear_form(self):
		# delete the attached files (the uploaded CSV templates)
		for name in frappe.get_all("File", filters={
			"attached_to_doctype": self.doctype,
			"attached_to_name": self.name,
		}, pluck="name"):
			frappe.delete_doc("File", name, ignore_permissions=True)

		# clear the fields and the loaded rows
		self.physician = None
		self.physician_name = None
		self.template = None
		self.clinic = None
		self.invoices = []
		# physician/clinic are mandatory on the doctype; allow the cleared state to persist
		self.flags.ignore_mandatory = True
		self.save()

	@frappe.whitelist()
	def read_invoices_and_update(self):
		valid_date = r"^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$"
		pattern = re.compile(valid_date)

		if not self.template:
			return

		self.invoices = []

		path = self.template

		if not path.endswith(".csv"):
			frappe.throw(_("Extension not supported!"))

		site_path = get_site_path("" if path.startswith("/private/")
			else "public")

		full_path = "{}{}".format(site_path, path)
		last_ars = ''
		last_ars_name = ''
		with io.StringIO(read_csv_with_encoding(full_path)) as contents:
			reader = UnicodeReader(contents)
			tmp = list(reader)
			frappe.errprint("{} records".format(len(tmp)))  
			for idx, cursor in enumerate(tmp):
				if idx <= 1:
					header = cursor
					continue

				dictionary = dict(zip(header, cursor))

				# filters = {"customer_group":"ARS", "customer_name": dictionary.get("ars")}
				# ars = frappe.db.exists("Customer", filters)
				ars = frappe.db.exists("Customer", dictionary.get("ars"))
				# frappe.errprint(filters)
				
				if ars:
					if last_ars != ars:
						last_ars = ars
						last_ars_name = frappe.db.get_value("Customer", ars, "customer_name")

					dictionary.update({
						"ars": ars,
						"ars_name": last_ars_name
					})
				else:
					frappe.throw("No se encontro ARS en la linea {}".format(idx))

				if not pattern.match(dictionary.get("date")):
					frappe.throw("Invalid date <b>{}</b> on line <b>{}</b>".format(dictionary.get("date"), idx))

				if dictionary.get("date") > nowdate():
					frappe.throw("Date <b>{}</b> cannot be greater than today on line <b>{}</b>".format(dictionary.get("date"), idx))

				strdict = json.dumps(dictionary, ensure_ascii=False)
				self.append("invoices", json.loads(strdict))
				frappe.publish_realtime(
					'import_invoice_progress',
					{"progress": [idx, len(tmp)-1, "{} {}".format(dictionary.get("authorization_no"), dictionary.get("customer"))]},
					doctype="Invoice Creation Tool",
					user=frappe.session.user
				)

		# persist the parsed rows so the client can reload_doc() and see them
		self.save()

	@frappe.whitelist()
	def import_invoices(self):
		dgii_settings = frappe.get_doc("DGII Settings", self.physician)
		avail_ncf = dgii_settings.get_remaining_ncf("B02.########")
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		income_account, default_receivable_account, default_expense_account, default_cash_account  = frappe.get_value(
			"Company",
			company,
			["default_income_account", "default_receivable_account", "default_expense_account", "default_cash_account"]
		)

		if len(self.invoices) > avail_ncf:
			frappe.throw("No hay suficientes B02 para {0}".format(self.physician_name))

		for row in self.invoices:
			if exists(row):
				row.status = "Duplicate"
				continue
			
			doc = frappe.new_doc("Sales Invoice")

			# row.date may be a datetime.date (loaded from DB) or a str (from the client)
			if not str(row.customer or "").strip() or not row.date:
				frappe.throw("Didn't receive a customer or date  Please add Manually")
	
			if row.nss and frappe.db.exists("Patient", {"nss": row.nss}):
				cust = frappe.get_doc("Patient", {"nss": row.nss})
			elif frappe.db.exists("Patient", {"patient_name": row.customer}):
				cust = frappe.get_doc("Patient", {"patient_name": row.customer})
			else:
				cust = frappe.new_doc("Patient")

				cust.update({
					# healthcare Patient requires first_name and derives patient_name
					# from it; keep the full name so the lookup above keeps matching
					"first_name": row.customer,
					"patient_name": row.customer,
					"customer_group": "Customers",
					"physician": self.physician,
					"physician_name": self.physician_name,
					"ars": row.ars,
					"ars_name": row.ars_name,
					"sex": 'Femenino',
					"nss": row.nss or "",
				})
				
				cust.save()
				frappe.db.sql("commit")
				frappe.local.rollback_observers = []				

			# legacy/new patients may not be linked to a Customer (Healthcare only
			# auto-links when 'link_customer_to_patient' is on) -> ensure one exists
			if not cust.customer:
				from healthcare.healthcare.doctype.patient.patient import create_customer
				create_customer(cust)
				cust.reload()

			# the invoice's ars/ars_name are fetched from the customer (read-only),
			# so stamp the ARS on the customer or the fetch overwrites it with None
			if row.ars and row.ars != 'PACIENTE PRIVADO':
				frappe.db.set_value("Customer", cust.customer, {
					"ars": row.ars,
					"nombre_ars": row.ars_name,
				}, update_modified=False)

			doc.update({
				"customer": cust.customer,
				"patient": cust.name,
				"set_posting_time": 1,
				"naming_series": "B02.########",
				# "ncf": row.ncf or "NO COMP",
				"ars": '' if row.ars == 'PACIENTE PRIVADO' else row.ars,
				"ars_name": '' if row.ars == 'PACIENTE PRIVADO' else row.ars_name,
				"invoice_type": 'Private Customers' if not row.ars else 'Insurance Customers',
				"against_income_account": income_account,
				"posting_date" : row.date,
				"authorization_no" : str(row.authorization_no).strip(),
				"nss" : str(row.nss).strip(),
				"physician" : self.physician,
				"physician_name" : self.physician_name,
				"clinic" : self.clinic.strip(),
				"debit_to" : default_receivable_account,
				"due_date": add_days(row.date, 20),
				"authorized_amount": flt(row.authorized),
				"claimed_amount": flt(row.claimed),
				"difference_amount": row.difference,
			})
	
			doc.append("items", {
				"claimed_amount": flt(row.claimed),
				"authorized_amount": flt(row.authorized),
				"difference_amount": row.difference,
				"coverage": 0 if not row.ars else 80.0,
				"qty": 1,
				"print_qty": 1,
				"rate": flt(row.claimed),
				"net_rate": flt(row.claimed),
				"base_rate": flt(row.claimed),
				"amount": flt(row.claimed),
				"net_amount": flt(row.claimed),
				"base_amount": flt(row.claimed),
				"base_rate": flt(row.claimed),
				"parent": doc.name,
				"conversion_factor": 1,
				"item_name": row.service,
				"description": row.service,
				"uom": "Unidad(es)",
				"expense_account": default_expense_account,
				"income_account": income_account,
			})
	
			if row.ars:
				doc.append("payments", {
					"account": default_cash_account,
					"amount": flt(row.authorized),
					"base_amount": flt(row.authorized),
					"mode_of_payment": "Seguro",
					"type": "Cash"
				})
			
			doc.append("payments", {
				"account": default_cash_account,
				"amount": row.difference,
				"base_amount": row.difference,
				"mode_of_payment": "Efectivo",
				"type": "Cash"
			})
			
			doc.set_missing_values()
			# crear la factura validada (enviada), no en borrador
			doc.submit()
			frappe.publish_realtime(
				'import_invoice_progress',
				{"progress": [row.idx, len(self.invoices)-1, "{authorization_no} {customer}".format(**row.as_dict())]},
				doctype="Invoice Creation Tool",
				user=frappe.session.user
			)
			row.status = "Imported"	


def exists(row):
	# dedup by authorization_no (unique per authorization). The old monto_* fields
	# no longer exist (made this always False), and nss is unreliable due to
	# leading-zero formatting differences between the CSV and stored invoices.
	filters = {
		"authorization_no": str(row.authorization_no).strip(),
		"docstatus": ["<", 2],
	}

	return not not frappe.db.exists("Sales Invoice", filters)
	


