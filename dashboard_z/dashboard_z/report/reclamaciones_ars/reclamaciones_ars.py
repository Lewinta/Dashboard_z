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
		(_("Date"), "Date", 90),
		(_("Customer"), "Data", 200),
		# (_("Physician"), "Data", 200),
		(_("Item Group"), "Link/Item Group", 120),
		(_("ARS"), "Data", 100),
		(_("Authorization No"), "Data", 100),
		(_("NSS"), "Data", 100),
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
		("Sales Invoice", "posting_date"),
		("Sales Invoice", "customer_name"),
		("Sales Invoice", "physician_name"),
		("Sales Invoice Item", "item_group"),
		("Sales Invoice", "ars_name"),
		("Sales Invoice", "authorization_no"),
		("Sales Invoice", "nss"),
		("Sales Invoice Item", "claimed_amount"),
		("Sales Invoice Item", "authorized_amount"),
		("Sales Invoice Item", "difference_amount"),
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
			`tabSales Invoice`.invoice_type in ('Insurance Customers')
		And
			`tabSales Invoice`.payment_status != 'PAID'
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

	if filters.get("ars"):
		query.append(
			"`tabSales Invoice`.ars = '{}'".format(
				filters.get('ars')
			)
		)

	if filters.get("item_group"):
		query.append(
			"`tabSales Invoice Item`.item_group = '{}'".format(
				filters.get('item_group')
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
		Join
			`tabSales Invoice Item`
		On
			`tabSales Invoice`.name = `tabSales Invoice Item`.parent
		Where
			{conditions}
		Order By 
			`tabSales Invoice`.posting_date
		""".format(fields=fields, conditions=conditions or "1 = 1"),
	filters, as_dict=True, debug=True)

	for row in data:
		results.append(
			(
				# row.name,
				# row.status,
				row.posting_date,
				row.customer_name,
				# row.physician_name,
				row.item_group,
				row.ars_name,
				row.authorization_no,
				row.nss,
				row.claimed_amount,
				row.authorized_amount,
				row.difference_amount,
			)
		)
	return results
