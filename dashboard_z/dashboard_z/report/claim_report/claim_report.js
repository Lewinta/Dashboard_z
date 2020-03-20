// Copyright (c) 2016, TZCODE and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Claim Report"] = {
	"filters": [
		
		{
			"label": __("Physician"),
			"fieldname": "physician",
			"fieldtype": "Link",
			"options": "Physician",
			"reqd": 1,
			"on_change": function() {
				var physician = frappe.query_report_filters_by_name.physician.get_value();
				var from_date = frappe.query_report_filters_by_name.from_date.get_value();
				var to_date = frappe.query_report_filters_by_name.to_date.get_value();
				if (!physician || !from_date || !to_date)
					return;
				frappe.query_report_filters_by_name.sales_invoice.get_query = function (){
					return {
						"filters": {
							"invoice_type": "Suppliers",
							"physician": "physician",
							"docstatus": ["<", 2],
							"posting_date": [">=", from_date],
							"creation": ["<=", to_date],
						}
					}
				}
			}
		},
		{
			"label": __("From Date"),
			"fieldname": "from_date",
			"fieldtype": "Date",
			"reqd": 1,
			"on_change": function() {
				var physician = frappe.query_report_filters_by_name.physician.get_value();
				var from_date = frappe.query_report_filters_by_name.from_date.get_value();
				var to_date = frappe.query_report_filters_by_name.to_date.get_value();
				if (!physician || !from_date || !to_date)
					return;
				frappe.query_report_filters_by_name.sales_invoice.get_query = function (){
					return {
						"filters": {
							"invoice_type": "Suppliers",
							"physician": physician,
							"docstatus": ["<", 2],
							"posting_date": [">=", from_date],
							"creation": ["<=", to_date],
						}
					}
				}
			}
		},
		{
			"label": __("To Date"),
			"fieldname": "to_date",
			"fieldtype": "Date",
			"reqd": 1,
			"on_change": function() {
				var physician = frappe.query_report_filters_by_name.physician.get_value();
				var from_date = frappe.query_report_filters_by_name.from_date.get_value();
				var to_date = frappe.query_report_filters_by_name.to_date.get_value();
				if (!physician || !from_date || !to_date)
					return;
				frappe.query_report_filters_by_name.sales_invoice.get_query = function (){
					return {
						"filters": {
							"invoice_type": "Suppliers",
							"physician": physician,
							"docstatus": ["<", 2],
							"posting_date": [">=", from_date],
							"creation": ["<=", to_date],
						}
					}
				}
			}
		},
		{
			"label": __("Sales Invoice"),
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"reqd": 1,
		},
	]
}
