// Copyright (c) 2019, TZCODE and contributors
// For license information, please see license.txt

frappe.ui.form.on('Physician Defaults', {
	refresh: frm => {
		frm.trigger("set_queries");
	},
	set_queries: frm => {
		let field = frm.fields_dict.pss_codes;
		let filter = function() {
			return {
				"filters": {
					"customer_group": "ARS",
				}
			}
		}
		field.grid.get_field('ars').get_query = filter;
	}

});
