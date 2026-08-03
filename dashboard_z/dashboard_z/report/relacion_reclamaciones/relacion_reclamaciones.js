// Copyright (c) 2016, TZCODE and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Relacion Reclamaciones"] = {
	"filters": [
		{
			"label": __("Sales Invoice"),
			"fieldname": "sales_invoice",
			"fieldtype": "Link",
			"options": "Sales Invoice",
			"reqd": 1,
			get_query: function (){
				return {
					"filters": {
						"invoice_type": "Suppliers",
					}
				}
			}
		}
	]
}
