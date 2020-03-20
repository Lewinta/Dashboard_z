	# Copyright (c) 2013, TZCODE SRL and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, flt

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_columns():
	columns = (
		(_("Invoice"), "Link/Sales Invoice", 160),
		# (_("Status"), "Data", 80),
		(_("Date"), "Date", 90),
		(_("Customer"), "Data", 200),
		(_("ARS"), "Data", 120),
		(_("Authorization"), "Data", 100),
		(_("Claimed"), "Currency", 100),
		(_("Authorized"), "Currency", 100),
		(_("Difference"), "Currency", 100),
	)

	formatted_columns = []
	
	for label, fieldtype, width in columns:
		formatted_columns.append(
			get_formatted_column(label, fieldtype, width)
		)

	return formatted_columns

def get_formatted_column(label, fieldtype, width):
	# [label]:[fieldtype/Options]:width
	parts = (
		_(label),
		fieldtype,
		cstr(width)
	)
	return ":".join(parts)

def get_fields(filters):
	"""
	Return sql fields ready to be used on query
	"""
	fields = (
		("Sales Invoice", "name"),
		# ("Sales Invoice", "status"),
		("Sales Invoice", "posting_date"),
		("Sales Invoice", "customer_name"),
		("Sales Invoice", "ars_name"),
		("Sales Invoice", "authorization_no"),
		("Sales Invoice", "claimed_amount"),
		("Sales Invoice", "authorized_amount"),
		("Sales Invoice", "difference_amount"),
	)
		
	sql_fields = []

	for args in fields:
		sql_field = get_field(args)

		sql_fields.append(sql_field)

	return ", ".join(sql_fields)

def get_field(args):

	if len(args) == 2:
		doctype, fieldname = args
		alias = fieldname
	elif len(args) == 3:
		doctype, fieldname, alias = args
	else:
		return args if isinstance(args, basestring) \
			else " ".join(args)

	sql_field = "`tab{doctype}`.`{fieldname}` as {alias}" \
		.format(doctype=doctype, fieldname=fieldname, alias=alias)

	return sql_field

def get_conditions(filters):
	query = ["""
			`tabSales Invoice`.docstatus != 2 
		And 
			`tabSales Invoice`.invoice_type in ('Insurance Customers', 'Private Customers')
	"""]

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


def get_data(filters):
	"""
	Return the data that needs to be rendered
	"""
	fields = get_fields(filters)
	conditions = get_conditions(filters)
	results = []
	data =  frappe.db.sql("""
		Select
			{fields}
		From
			`tabSales Invoice`
		Where
			{conditions}

		""".format(fields=fields, conditions=conditions or "1 = 1"),
	filters, as_dict=True, debug=True)

	for row in data:
		results.append(
			(
				row.name,
				# row.status,
				row.posting_date,
				row.customer_name,
				row.ars_name,
				row.authorization_no,
				row.claimed_amount,
				row.authorized_amount,
				row.difference_amount,
			)
		)
	return results
