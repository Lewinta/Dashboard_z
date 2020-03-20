// Copyright (c) 2016, TZCODE and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Reclamaciones ARS"] = {
	"filters": [
		{
			"label": __("From Date"),
			"fieldname": "from_date",
			"fieldtype": "Date",
			"default": frappe.datetime.month_start(),
			"reqd": 1,
		},
		{
			"label": __("To Date"),
			"fieldname": "to_date",
			"fieldtype": "Date",
			"default": frappe.datetime.now_date(),
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
			"label": __("Clinic"),
			"fieldname": "clinic",
			"fieldtype": "Link",
			"options": "Clinic",
		},
		{
			"label": __("Payment Status"),
			"fieldname": "payment_status",
			"fieldtype": "Select",
			"options": "PAID\nPARTIALLY PAID\nUNPAID",
			"default": "UNPAID",
		},
		{
			"label": __("Item Group"),
			"fieldname": "item_group",
			"fieldtype": "Link",
			"options": "Item Group",
		}
	]
}
