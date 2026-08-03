# -*- coding: utf-8 -*-
# Copyright (c) 2020, TZCODE and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_site_path
from . import UnicodeReader
from frappe.utils import nowdate, add_days, flt, strip_html
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

	def _import_context(self):
		"""Everything the import needs that does not change from row to row."""
		company = frappe.db.get_single_value("Global Defaults", "default_company")
		income_account, receivable_account, expense_account, cash_account = frappe.get_value(
			"Company",
			company,
			["default_income_account", "default_receivable_account",
			 "default_expense_account", "default_cash_account"],
		)

		return frappe._dict({
			"company": company,
			"income_account": income_account,
			"receivable_account": receivable_account,
			"expense_account": expense_account,
			"cash_account": cash_account,
			"avail_ncf": frappe.get_doc("DGII Settings", self.physician).get_remaining_ncf("B02.########"),
		})

	def _row_error(self, row, message):
		return {
			"idx": row.idx,
			"customer": row.customer or "",
			"authorization_no": str(row.authorization_no or "").strip(),
			"message": message,
		}

	def _validate_rows(self, ctx):
		"""Classify every row before anything is written.

		A duplicate is not an error: it is an authorization already invoiced, so
		we skip it. That is what makes retrying a half-done batch safe.
		"""
		pattern = re.compile(r"^\d{4}\-(0[1-9]|1[012])\-(0[1-9]|[12][0-9]|3[01])$")
		to_create, duplicated, errors = [], [], []
		seen = set()

		for row in self.invoices:
			authorization_no = str(row.authorization_no or "").strip()
			row_date = str(row.date or "")
			problem = None

			if not str(row.customer or "").strip():
				problem = _("Falta el nombre del paciente")
			elif not authorization_no:
				problem = _("Falta el no. de autorización")
			elif not row_date:
				problem = _("Falta la fecha")
			elif not pattern.match(row_date):
				problem = _("Fecha inválida: {0}").format(row_date)
			elif row_date > nowdate():
				problem = _("La fecha {0} es futura").format(row_date)
			elif row.ars and not frappe.db.exists("Customer", row.ars):
				problem = _("La ARS {0} no existe como cliente").format(row.ars)
			elif flt(row.claimed) <= 0:
				problem = _("El monto reclamado debe ser mayor que cero")
			elif authorization_no in seen:
				problem = _("El no. de autorización {0} se repite en el archivo").format(authorization_no)

			if problem:
				errors.append(self._row_error(row, problem))
				continue

			seen.add(authorization_no)

			if invoice_exists(authorization_no):
				duplicated.append(row)
			else:
				to_create.append(row)

		if not errors and len(to_create) > ctx.avail_ncf:
			errors.append({
				"idx": 0,
				"customer": "",
				"authorization_no": "",
				"message": _("No hay suficientes B02 para {0}: se necesitan {1} y quedan {2}").format(
					self.physician_name, len(to_create), ctx.avail_ncf
				),
			})

		return to_create, duplicated, errors

	def _resolve_patient(self, row):
		"""Find the Patient for this row, creating it when it is new."""
		if row.nss and frappe.db.exists("Patient", {"nss": row.nss}):
			return frappe.get_doc("Patient", {"nss": row.nss})

		if frappe.db.exists("Patient", {"patient_name": row.customer}):
			return frappe.get_doc("Patient", {"patient_name": row.customer})

		patient = frappe.new_doc("Patient")
		patient.update({
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
		patient.save()
		return patient

	def _create_invoice(self, row, ctx):
		patient = self._resolve_patient(row)

		# legacy/new patients may not be linked to a Customer (Healthcare only
		# auto-links when 'link_customer_to_patient' is on) -> ensure one exists
		if not patient.customer:
			from healthcare.healthcare.doctype.patient.patient import create_customer
			create_customer(patient)
			patient.reload()

		# the invoice's ars/ars_name are fetched from the customer (read-only),
		# so stamp the ARS on the customer or the fetch overwrites it with None
		if row.ars and row.ars != 'PACIENTE PRIVADO':
			frappe.db.set_value("Customer", patient.customer, {
				"ars": row.ars,
				"nombre_ars": row.ars_name,
			}, update_modified=False)

		doc = frappe.new_doc("Sales Invoice")
		doc.update({
			"customer": patient.customer,
			"patient": patient.name,
			"set_posting_time": 1,
			"naming_series": "B02.########",
			"ars": '' if row.ars == 'PACIENTE PRIVADO' else row.ars,
			"ars_name": '' if row.ars == 'PACIENTE PRIVADO' else row.ars_name,
			"invoice_type": 'Private Customers' if not row.ars else 'Insurance Customers',
			"against_income_account": ctx.income_account,
			"posting_date": row.date,
			"authorization_no": str(row.authorization_no).strip(),
			"nss": str(row.nss).strip(),
			"physician": self.physician,
			"physician_name": self.physician_name,
			"clinic": self.clinic.strip(),
			"debit_to": ctx.receivable_account,
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
			"parent": doc.name,
			"conversion_factor": 1,
			"item_name": row.service,
			"description": row.service,
			"uom": "Unidad(es)",
			"expense_account": ctx.expense_account,
			"income_account": ctx.income_account,
		})

		if row.ars:
			doc.append("payments", {
				"account": ctx.cash_account,
				"amount": flt(row.authorized),
				"base_amount": flt(row.authorized),
				"mode_of_payment": "Seguro",
				"type": "Cash",
			})

		doc.append("payments", {
			"account": ctx.cash_account,
			"amount": row.difference,
			"base_amount": row.difference,
			"mode_of_payment": "Efectivo",
			"type": "Cash",
		})

		doc.set_missing_values()
		# crear la factura validada (enviada), no en borrador
		doc.submit()
		return doc

	@frappe.whitelist()
	def import_invoices(self):
		ctx = self._import_context()
		to_create, duplicated, errors = self._validate_rows(ctx)

		# nada se escribe si el archivo trae problemas: el lote es todo o nada
		if errors:
			return self._report([], duplicated, errors)

		created = []
		try:
			for row in to_create:
				self._create_invoice(row, ctx)
				created.append(row)
				frappe.publish_realtime(
					'import_invoice_progress',
					{"progress": [len(created), len(to_create),
						"{0} {1}".format(row.authorization_no, row.customer)]},
					doctype="Invoice Creation Tool",
					user=frappe.session.user,
				)
		except Exception as exc:
			# the whole batch shares one transaction, so this undoes the invoices,
			# the patients and the NCF numbers taken so far
			frappe.db.rollback()
			failed_row = to_create[len(created)]
			message = strip_html(str(exc)) or exc.__class__.__name__
			return self._report([], duplicated, [self._row_error(failed_row, message)])

		return self._report(created, duplicated, [])

	def _report(self, created, duplicated, errors):
		"""Persist the per-row outcome and hand a summary to the client.

		Deliberately runs after the rollback and commits on its own: raising
		here (frappe.throw) would roll the report back along with the batch.
		"""
		failed = {e["idx"]: e["message"] for e in errors}
		created_idx = set(row.idx for row in created)
		duplicated_idx = set(row.idx for row in duplicated)

		for row in self.invoices:
			if row.idx in failed:
				row.status, row.error_message = "Error", failed[row.idx]
			elif row.idx in created_idx:
				row.status, row.error_message = "Imported", ""
			elif row.idx in duplicated_idx:
				row.status, row.error_message = "Duplicate", ""
			else:
				row.status, row.error_message = "", ""

		# physician/clinic are mandatory on the doctype; the report must persist regardless
		self.flags.ignore_mandatory = True
		self.save()
		frappe.db.commit()

		return {
			"ok": not errors,
			"created": len(created),
			"duplicated": len(duplicated),
			"errors": errors,
		}


def invoice_exists(authorization_no):
	# dedup by authorization_no (unique per authorization). nss is unreliable due
	# to leading-zero formatting differences between the CSV and stored invoices.
	return bool(frappe.db.exists("Sales Invoice", {
		"authorization_no": authorization_no,
		"docstatus": ["<", 2],
	}))
	


