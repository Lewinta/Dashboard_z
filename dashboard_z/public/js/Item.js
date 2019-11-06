frapp.ui.form.on("Item", {
	refresh: frm => {
		console.log("loaded");
	},
	item_name: frm => {
		frm.set_value("item_name", frm.doc.item_name.trim().toUpperCase());
	}
})