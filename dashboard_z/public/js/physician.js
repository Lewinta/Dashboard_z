frappe.ui.form.on("Physician", {
	first_name: frm => {
		const {first_name} = frm.doc; 

		if(!first_name)
			return

		frm.set_value("first_name", first_name.toUpperCase().trim());
	},
	last_name: frm => {
		const {last_name} = frm.doc; 

		if(!last_name)
			return

		frm.set_value("last_name", last_name.toUpperCase().trim());
	}
});