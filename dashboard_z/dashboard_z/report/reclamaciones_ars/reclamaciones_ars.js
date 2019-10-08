// Copyright (c) 2016, TZCODE and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Reclamaciones ARS"] = {
	"filters": [
		{
			"label": __("From Date"),
			"fieldname": "from_date",
			"fieldtype": "Date",
			"reqd": 1,
		},
		{
			"label": __("To Date"),
			"fieldname": "to_date",
			"fieldtype": "Date",
			"reqd": 1,
		},
		{
			"label": __("Physician"),
			"fieldname": "physician",
			"fieldtype": "Link",
			"options": "Physician",
			"reqd": 1,
		},
		{
			"label": __("ARS"),
			"fieldname": "ars",
			"fieldtype": "Link",
			"options": "Customer",
		},
		{
			"label": __("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
		}
	]
}
