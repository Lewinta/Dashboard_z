// Copyright (c) 2020, TZCODE and contributors
// For license information, please see license.txt

frappe.ui.form.on('Invoice Creation Tool', {
	refresh: function(frm) {
		frm.add_fetch("physician", "hospital", "clinic");
		frm.add_fetch("physician", "full_name", "physician_name");
		$.map(["add_custom_button", "set_queries", "add_realtime_listeners"], event => {
			frm.trigger(event);
		})
		
	}, 
	add_custom_button: frm => {
		frm.add_custom_button(__("Clear Form"), function(){
			frappe.dom.freeze(__("Limpiando formulario... Por favor espere."));
			frm.call("clear_form").then(
				() => frm.reload_doc().then(() => {
					frappe.show_alert({"message":__("Form Cleared"), "indicator":"green"});
					frappe.dom.unfreeze();
				}),
				() => frappe.dom.unfreeze()   // on failure, always release the freeze
			);
		})
		if (frm.doc.template)
			frm.add_custom_button(__("Load Invoices"), function(){
				frappe.dom.freeze(__("Cargando facturas... Por favor espere."));
				frm.call("read_invoices_and_update").then(
					() => frm.reload_doc().then(() => frappe.dom.unfreeze()),
					() => frappe.dom.unfreeze()   // on failure, always release the freeze
				);
			})

		// show the Import action whenever rows are loaded (survives reload_doc)
		if (frm.doc.invoices && frm.doc.invoices.length)
			frm.trigger("final_step");
	},
	set_queries: frm => {
		frm.set_query("ars", "invoices", function () {
			return {
				"filters": {
					"customer_group": "ARS"
				}
			}
		})
	},
	add_realtime_listeners: frm => {
		frappe.realtime.on("import_invoice_progress", function(data) {
			if(data.progress) {
				frappe.hide_msgprint(true);
				frappe.show_progress(
					`Importing Invoices`,
					data.progress[0],
					data.progress[1],
					data.progress[2]
				);

				if (data.progress[0] == data.progress[1])
					setTimeout(function() {frappe.hide_progress()}, 700);
			}
		});
	},
	final_step: frm => {
		frm.page.set_primary_action(__("Import Invoices"), function() {
			// freeze the whole UI immediately so a second click can't create duplicates
			frappe.dom.freeze(__("Importando facturas... Por favor espere y no cierre ni recargue la página."));
			frm.call("import_invoices").then(
				() => frm.reload_doc().then(() => frappe.dom.unfreeze()),
				() => frappe.dom.unfreeze()   // on failure, always release the freeze
			);
		});
	}
});
