// Copyright (c) 2020, TZCODE and contributors
// For license information, please see license.txt

// el import es todo o nada: o se crean todas las facturas o ninguna, asi que
// el resumen tiene que decir exactamente que fila fallo y por que
const show_import_summary = message => {
	if (!message) return;

	if (message.ok) {
		frappe.msgprint({
			title: __("Importación completada"),
			indicator: "green",
			message: __("{0} factura(s) creada(s), {1} omitida(s) por estar ya registradas.",
				[message.created, message.duplicated])
		});
		return;
	}

	const errors = message.errors || [];
	const rows = errors.map(e => `
		<tr>
			<td>${e.idx || "-"}</td>
			<td>${frappe.utils.escape_html(e.customer || "")}</td>
			<td>${frappe.utils.escape_html(e.authorization_no || "")}</td>
			<td>${frappe.utils.escape_html(e.message || "")}</td>
		</tr>`).join("");

	frappe.msgprint({
		title: __("No se importó ninguna factura"),
		indicator: "red",
		message: `
			<p>${__("El lote es todo o nada: se encontraron {0} problema(s), así que no se creó ninguna factura. Corrija el archivo y vuelva a cargarlo.", [errors.length])}</p>
			<table class="table table-bordered">
				<thead>
					<tr>
						<th>${__("Fila")}</th>
						<th>${__("Paciente")}</th>
						<th>${__("Autorización")}</th>
						<th>${__("Problema")}</th>
					</tr>
				</thead>
				<tbody>${rows}</tbody>
			</table>`
	});
};

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
				// ojo: no llamar frappe.hide_msgprint aqui - ocultaba los propios
				// dialogos de error del import
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
				r => frm.reload_doc().then(() => {
					frappe.dom.unfreeze();
					show_import_summary(r.message);
				}),
				() => frappe.dom.unfreeze()   // on failure, always release the freeze
			);
		});
	}
});
