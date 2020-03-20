# Copyright (c) 2013, TZCODE and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import db, _
from frappe.utils import cstr, flt

def execute(filters=None):
	return get_columns(filters), get_data(filters)

def get_columns(filters):
	columns = (
		(_("name"), "name", "Link/Sales Invoice", 160),
		(_("Date"), "posting_date", "Date", 85),
		(_("Patient"), "patient", "Data", 180),
		(_("ARS"), "ars", "Data", 100),
		(_("NCF"), "ncf", "Data", 100),
		(_("Authorization No"), "authorization_no", "Data", 100),
		(_("NSS"), "nss", "Data", 100),
		(_("Claimed Amount"), "claimed_amount", "Currency", 120),
		(_("Fee Amount"), "fee_amount", "Currency", 100),
		(_("Paid Amount"), "received_amount", "Currency", 100),
		(_("Pending Amount"), "pending_amount", "Currency", 100),
		(_("Status"), "status", "Data", 90),
	)

	formatted_columns = []

	for label, fieldname, fieldtype, width in columns:
		formatted_column = get_formatted_field(label=label,
			fieldtype=fieldtype, width=width)

		formatted_columns.append(formatted_column)

	return formatted_columns

def get_data(filters):
	fields = get_fields(filters)
	conditions = get_conditions(filters)
	results = []
	if filters.get('summarize'):

		query = frappe.db.sql("""
			Select
				SUM(1) as total_points,
				SUM(total_score) total_submitted,
				SUM(IF(DATEDIFF(DATE(`tabAppraisal`.modified), `tabAppraisal`.end_date) < 5, total_score,0)) total_earned,
				`tabAppraisal`.employee,
				`tabAppraisal`.employee_name
			FROM 
				`tabAppraisal`
			Where
				{conditions}
			GROUP BY 
				`tabAppraisal`.employee
			""".format(
				fields=fields,
				conditions=conditions or "1 = 1",
			), filters, as_dict=True, debug=False
		)

		total_points = filters.get('weeks') * 5
		for data in query:
			results.append(
				(
					data.employee,
					data.employee_name,
					data.total_submitted,
					data.total_earned,
					total_points,
					data.total_submitted / total_points * 100,
					data.total_earned / total_points * 100,
				)
			)

	else:
		data = frappe.db.sql("""
			Select
				{fields}
			FROM 
				`tabSales Invoice`
			Where
				{conditions}
			""".format(fields=fields, conditions=conditions or "1 = 1"),
			filters, as_dict=True, debug=False
		)
		for row in data:
			status = "ERROR"
			
			if flt(row.received_amount) == .00:
				status = _("UNPAID") 
			if flt(row.claimed_amount, 2)  > .00:
				status = _("PARTIALLY") 
			if flt(row.received_amount, 2) ==  flt(row.claimed_amount, 2):
				status = _("PAID")

			ncf, customer = frappe.db.get_value("Sales Invoice", filters.get("sales_invoice"), ["ncf", "customer"])
			fee = flt(frappe.db.get_value("Customer", customer, "fee_percentage")) / 100.00

			results.append(
				(
					row.name,
					row.posting_date,
					row.customer_name,
					row.ars_name,
					ncf,
					row.authorization_no,
					row.nss,
					row.authorized_amount,
					row.received_amount * fee,
					row.received_amount * (1 - fee),
					flt(row.claimed_amount) - flt(row.received_amount),
					status
				)
			)
	return results

def get_conditions(filters):

	sql_conditions = []
	conditions = [
		("Sales Invoice", "invoice_type", "=", "Insurance Customers"),
		# ("Sales Invoice", "posting_date", ">=", filters.get("from_date")),
		# ("Sales Invoice", "posting_date", "<=", filters.get("to_date")),
		("Sales Invoice", "physician", "=", filters.get("physician")),
	]
	if filters.get("sales_invoice"):
		filters = {
			"parent": filters.get("sales_invoice"),
			"idx": 1
		}
		paid_invoices = frappe.db.get_value(
			"Sales Invoice Item",
			filters,
			"paid_sales_invoices"
		).split(',')
		# Let's remove the u prefix for unicode
		paid_invoices = [str(r) for r in paid_invoices]
		conditions.append(
			("Sales Invoice", "name", "in", tuple(paid_invoices)),
		)

	for doctype, fieldname, compare, value in conditions:

		if not value:
			continue

		if type(value) == tuple:
			sql_condition = "`tab{doctype}`.`{fieldname}` {compare} {value}" \
				.format(doctype=doctype, fieldname=fieldname, compare=compare,
					value=value)
		else:
			sql_condition = "`tab{doctype}`.`{fieldname}` {compare} '{value}'" \
				.format(doctype=doctype, fieldname=fieldname, compare=compare,
					value=value)

		sql_conditions.append(sql_condition)


	return " And ".join(sql_conditions)


def get_formatted_field(label, width=100, fieldtype=None):
	"""
	Returns formatted string
		[Label]:[Field Type]/[Options]:[Width]
	"""
	from frappe import _

	parts = (
		_(label).title(),
		fieldtype if fieldtype else "Data",
		cstr(width),
	)
	return ":".join(parts)

def get_fields(filters):
	sql_fields = []

	fields = (
		("Sales Invoice", "name"),
		("Sales Invoice", "posting_date"),
		("Sales Invoice", "customer_name"),
		("Sales Invoice", "ars_name"),
		("Sales Invoice", "authorization_no"),
		("Sales Invoice", "nss"),
		("Sales Invoice", "authorized_amount"),
		("Sales Invoice", "received_amount"),
	)

	for args in fields:
		sql_field = get_field(args)

		sql_fields.append(sql_field)

	return ", ".join(sql_fields)

def get_field(args):

	if len(args) == 2:
		doctype, fieldname = args
	else:
		return args if isinstance(args, basestring) \
			else " ".join(args)

	sql_field = "`tab{doctype}`.`{fieldname}`" \
		.format(doctype=doctype, fieldname=fieldname)

	return sql_field


