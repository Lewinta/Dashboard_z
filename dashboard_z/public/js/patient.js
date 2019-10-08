frappe.ui.form.on("Patient", {
	onload: frm=> {
		frm.set_df_property("naming_series", "hidden", 1)
	},
	refresh: frm => {
		frm.set_query("ars", event => {
            let condition = ["in", "ARS"]
            return {
                "query": "erpnext.controllers.queries.customer_query",  
                "filters": {
                    "customer_group": condition,
                }
            }
        });
	},
	patient_name: frm => {
		const {patient_name} = frm.doc;

		if(!patient_name)
			return
		frm.set_value("patient_name", patient_name.toUpperCase().trim());
	},
});