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
		(_("Physician"), "physician", "Data", 250),
		(_("Total Billed"), "total_billed", "Currency", 200),
		(_("Comission Rate"), "comission_rate", "Percent", 100),
		(_("Total Comission"), "total_comission", "Currency", 200),
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
	return  frappe.db.sql("""
		SELECT 
			`tabPhysician`.full_name,
			SUM(`tabSales Invoice`.grand_total) as total_billed,
			`tabPhysician`.op_consulting_charge,
			SUM(`tabSales Invoice`.grand_total) * `tabPhysician`.op_consulting_charge / 100.0 as total_comission
		FROM 
			`tabSales Invoice`
		JOIN
			`tabPhysician`
		ON
			`tabSales Invoice`.physician = `tabPhysician`.name
		WHERE
			{conditions}
		GROUP BY 	
			`tabSales Invoice`.physician
		""".format(fields=fields, conditions=conditions),
		filters, debug=True
	)
def get_conditions(filters):
	query = ["""
			`tabSales Invoice`.docstatus = 1 
	"""]

	if filters.get("based_on") == "Invoiced":
		query.append("  `tabSales Invoice`.invoice_type = 'Suppliers' ")
	
	if filters.get("based_on") == "Claimed":
		query.append("  `tabSales Invoice`.invoice_type = 'Insurance Customers' ")

	if filters.get("from_date"):
		query.append(
			"`tabSales Invoice`.posting_date >= '{}'".format(
				filters.get('from_date')
			)
		)
	
	if filters.get("to_date"):
		query.append(
			"`tabSales Invoice`.posting_date <= '{}'".format(
				filters.get('to_date')
			)
		)

	if filters.get("physician"):
		query.append(
			"`tabSales Invoice`.physician = '{}'".format(
				filters.get('physician')
			)
		)
	
	return " AND ".join(query)


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


