# Copyright (c) 2013, TZCODE and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import cstr, flt

def execute(filters=None):
	return get_columns(), get_data(filters)

def get_columns():
	columns = (
		(_("Sales Invoice"), "Link/Sales Invoice", 160),
		(_("NCF"), "Data", 100),
		(_("ARS"), "Data", 200),
		(_("Physician"), "Data", 150),
		(_("F.Envio"), "Date", 100),
		(_("Radicado"), "Currency", 150),
		(_("F.Recibido"), "Date", 100),
		(_("Descuentos"), "Currency", 150),
		(_("Recibido"), "Currency", 150),
		(_("Neto"), "Currency", 150),
		(_("Pendiente"), "Currency", 150),
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


def get_conditions(filters):
	query = ["""
			`tabSales Invoice`.docstatus != 2 
		And 
			`tabSales Invoice`.invoice_type in ('Suppliers')
	"""]

	if filters.get("physician"):
		query.append(
			"`tabSales Invoice`.physician = '{}'".format(
				filters.get('physician')
			)
		)

	return " AND ".join(query)

def get_data(filters):
	conditions = get_conditions(filters)
	results = []
	data = frappe.db.sql("""
		SELECT
			`tabSales Invoice`.name,
			`tabSales Invoice`.ncf,
			`tabSales Invoice`.customer_name,
			`tabSales Invoice`.physician_name,
			`tabSales Invoice`.posting_date as send_date,
			`tabSales Invoice`.grand_total,
			`tabJournal Entry`.posting_date as paid_on,
			(SELECT 
				SUM(
					IF(
						`tabJournal Entry Account`.payment_field = 'other_discounts',
						`tabJournal Entry Account`.debit,
						0
					)
				) 
			FROM 
				`tabJournal Entry Account`
			WHERE
				`tabJournal Entry Account`.parent = `tabJournal Entry`.name
			) as discount,
			`tabSales Invoice`.outstanding_amount
		FROM 
			`tabSales Invoice`
		LEFT JOIN
			`tabJournal Entry`
		ON
			`tabSales Invoice`.name = `tabJournal Entry`.reference_name
		AND
			`tabJournal Entry`.docstatus = 1
		WHERE
			{conditions}
		GROUP BY 
			`tabSales Invoice`.name
		ORDER BY 
			`tabSales Invoice`.posting_date
		""".format(conditions=conditions or "1 = 1"), debug=False, as_dict=True)
	for row in data:
		received = row.grand_total - row.outstanding_amount
		results.append(
			(
				row.name,
				row.ncf,
				row.customer_name,
				row.physician_name,
				row.send_date,
				row.grand_total,
				row.paid_on,
				row.discount,
				received, 
				flt(received, 2) - flt(row.discount, 2),
				row.outstanding_amount,
			)
		)
	return results
 	