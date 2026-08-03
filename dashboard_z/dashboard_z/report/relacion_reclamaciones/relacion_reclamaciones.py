# Copyright (c) 2013, TZCODE and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_columns():
	return [
		_("Date")		 		+ ":Date:85",
		_("Customer") 			+ ":Data:170",
		_("ARS") 				+ ":Data:120",
		_("Authorization No.")	+ ":Data:130",
		_("NSS") 				+ ":Data:120",
		_("Claimed") 			+ ":Currency/currency:95",
		_("Authorized") 		+ ":Currency/currency:95",
		_("Difference") 		+ ":Currency/currency:95",
	]

def get_data(filters):
	conditions = get_conditions(filters)
	return frappe.db.sql("""
		SELECT
			`tabSales Invoice`.posting_date,
			`tabSales Invoice`.customer_name,
			`tabSales Invoice`.ars_name,
			`tabSales Invoice`.authorization_no,
			`tabSales Invoice`.nss,
			`tabSales Invoice`.claimed_amount,
			`tabSales Invoice`.authorized_amount,
			`tabSales Invoice`.difference_amount
		FROM 
			`tabSales Invoice`
		WHERE
			{conditions}
		ORDER BY 
			`tabSales Invoice`.posting_date
		""".format(conditions=conditions or "1 = 1"),
		filters,
		debug= True
	)

def get_conditions(filters):
	sql_conditions = []
	conditions = [
		("Sales Invoice", "invoice_type", "=", "Insurance Customers"),
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
		)
		if not paid_invoices:
			frappe.throw("Esta Factura no tiene reclamaciones!")

		paid_invoices = paid_invoices.split(',')
		# Let's remove the u prefix for unicode
		if len(paid_invoices) == 1:
			conditions.append(
				("Sales Invoice", "name", "=", paid_invoices[0]),
			)
		else:
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
