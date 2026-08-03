// Copyright (c) 2016, TZCODE and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Comissions By Physician"] = {
	"filters": [
		{
			"label": __("From Date"),
			"fieldname": "from_date",
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"label": __("To Date"),
			"fieldname": "to_date",
			"fieldtype": "Date",
			"reqd": 1
		},
		{
			"label": __("Physician"),
			"fieldname": "physician",
			"fieldtype": "Link",
			"options": "Physician"
		},
		{
			"label": __("Based on"),
			"fieldname": "based_on",
			"fieldtype": "Select",
			"options": __("Claimed\nInvoiced"),
			"default": "Invoiced",
			"reqd": 1
		},
	]
}
