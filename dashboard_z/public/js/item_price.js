frappe.ui.form.on("Item Price", {
	price_list: frm => {
		const {price_list} = frm.doc;
		frappe.db.exists(
			"Customer", 
			price_list
		).then( response => {
				if(response){
					frappe.db.get_value(
						"Customer",
						price_list,
						"customer_name",
						({customer_name}) => {
							frm.set_value("ars_name", customer_name);
						}
					);
				}
			}
		)
	}
});