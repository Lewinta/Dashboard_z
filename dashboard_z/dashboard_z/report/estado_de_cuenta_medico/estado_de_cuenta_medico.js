// Copyright (c) 2016, TZCODE and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Estado de Cuenta Medico"] = {
	"filters": [
		{
			"label": __("Physician"),
			"fieldtype": "Link",
			"fieldname": "physician",
			"options": "Physician",
			"reqd": 1,
		}
	]
}
