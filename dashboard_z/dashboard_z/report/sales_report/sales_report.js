// Copyright (c) 2016, Lewin Villar and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Sales Report"] = {
	"filters": [
		{
			"label": __("From Date"),
			"fieldname": "from_date",
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
		},
		{
			"label": __("To Date"),
			"fieldname": "to_date",
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1,
		},
		{
			"label": __("Invoice Type"),
			"fieldname": "invoice_type",
			"fieldtype": "Select",
			"options": "Insurance Customers\nPrivate Customers\nSuppliers"
		},
		{
			"label": __("Physician"),
			"fieldname": "physician",
			"fieldtype": "Link",
			"options": "Physician",
			"reqd": 1,
		}
	]
}
