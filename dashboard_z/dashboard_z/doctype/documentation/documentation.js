// Copyright (c) 2020, TZCODE and contributors
// For license information, please see license.txt

frappe.ui.form.on('Documentation', {
	refresh: frm => {
		let show = eval(frappe.user.has_role("System Manager"));
		
		frm.toggle_enable("link", show);
		frm.add_custom_button("Ver Tutorial", event => {
			frm.trigger("go_to_link");
		})
	},
	go_to_link: frm => {
		window.open(frm.doc.link, '_blank')
	}
});
