frappe.ui.form.on("Customer", {
	customer_name: frm => {
		const {customer_name} = frm.doc;
		if(!customer_name)
			return
		frm.set_value("customer_name", customer_name);
	},
	tax_id: frm => {
		const {tax_id} = frm.doc;
		if(!tax_id)
			return
		frm.set_value("tax_id", mask_ced_pas_rnc(tax_id.trim()));

	}
});

function mask_ced_pas_rnc(input) {
	input = input.trim().replace(/-/g,"")
	
	if (input.length == 11)
		return ("{0}{1}{2}-{3}{4}{5}{6}{7}{8}{9}-{10}".format(input));

	if (input.length == 9)
		return ("{0}-{1}{2}-{3}{4}{5}{6}{7}-{8}".format(input));
	
	return input
}

