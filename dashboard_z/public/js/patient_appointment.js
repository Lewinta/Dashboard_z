frappe.ui.form.on("Patient Appointment", {
	refresh: frm => {
		frm.add_fetch("patient", "physician", "physician");
	},
	physician: frm => {
		const {physician} = frm.doc;

		if(!physician){
			frm.set_value("physician_name", "");
			return
		}

		frappe.db.get_value(
			"Physician",
			physician, "full_name", ({full_name}) => {
				if(full_name)
					frm.set_value("physician_name", full_name);
			})
	},

});