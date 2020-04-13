// Copyright (c) 2019, TZCODE and contributors
// For license information, please see license.txt

frappe.ui.form.on('Payment Processing Tool', {
	refresh: frm => {
		events = ["set_queries", "add_custom_buttons"];
		$.map(events, event => {
			frm.trigger(event);
		});

		
		frm.add_fetch("physician", "full_name", "physician_name");
		frm.add_fetch("supplier", "customer_name", "supplier_name");
		frm.add_fetch("invoice", "ncf", "ncf");
	},
	add_custom_buttons: frm => {
		let buttons = ["pay_all_btn", "clear_from_btn", "make_payment_btn"];
		$.map(buttons, btn => {
			frm.trigger(btn);
		});
		
	},
	make_payment_btn: frm => {
		if (frm.is_dirty())
			return
		let label = __("Make Payment Entry");
		let group = __("Make");
		let ifyes = function(){
			frappe.run_serially([
				() => frappe.dom.freeze(__("Processing Payment!")),
				() => frm.call("make_payment_entry").done( message => {
					frappe.run_serially([
						console.log(message),
						frm.save_or_update(),
						() => {
							if (frm.doc.payment) 
								frappe.set_route(["Form", "Journal Entry", frm.doc.payment])
						}
					]);
				}),
				() => frappe.dom.unfreeze(),
				() => frappe.utils.play_sound("submit"),
				() => frappe.show_alert("Payment Created Successfully"),
			]);
		}
		let callback = function(){
			frappe.confirm(__("Are you sure you want to submit this payment!"), ifyes);
		}

		frm.add_custom_button(label, callback, group);
		frm.page.set_inner_btn_group_as_primary(group);
		
	},
	clear_from_btn: frm => {
		frm.add_custom_button(__("Clear Form"), function() {
			frm.trigger("clear_form");
		});
	},
	pay_all_btn: frm => {
		if (!frm.doc.invoice)
			return
		frm.add_custom_button(__("Receive All Payments"), function () {
			if (!frm.doc.invoice){
				frappe.msgprint(__("Please choose a valid invoice to proceed"), __("Invalid Invoice"));
				return
			}
			if (!frm.doc.claims || !frm.doc.claims.length > 0){
				frappe.msgprint(__("Please click on the Get Invoices to retrieve Invoices"), __("Invalid Invoice"));
				return
			}
			
			$.map(frm.doc.claims, claim => {
				frappe.model.set_value(
					claim.doctype,
					claim.name,
					"received_amount",
					claim.claimed_amount
				)
			});
			frappe.show_alert(__("Payments Allocated Successfully"))
		});
	},
	clear_form: frm => {
		let fields = [
			"physician",
			"total_claimed",
			"total_to_receive",
			"total_fee",
			"total_paid",
			"total_received",
			"total_fee_paid",
			"grand_total_paid",
			"total_pending",
			"status",
		]
		$.map(fields, field => {
			frm.set_value(field, "");
		});
		frm.clear_table("claims");
		frm.refresh();
	},
	set_queries: frm => {
		frm.set_query("supplier", e => {
			return {
				"filters": {
					"customer_group": "ARS",
					"disabled": 0,
				}
			}
		})

		frm.set_query("invoice", e => {
			return {
				"filters": {
					"invoice_type": "Suppliers",
					"customer": frm.doc.supplier,
					"physician": frm.doc.physician,
					"docstatus": 1,
				}
			}
		})
	},
	physician: frm => {
		frm.set_value("supplier", "");
		frm.set_value("invoice", "");
		frm.trigger("set_queries");
	},
	supplier: frm => {
		const {supplier} = frm.doc;
		if(!supplier)
			return
		frm.set_value("invoice", "");
		frm.set_query("invoice", e => {
			return {
				"filters": {
					"invoice_type": "Suppliers",
					"customer": supplier,
				}
			}
		});
		frm.trigger("set_queries");
	},
	invoice: frm => {
		frm.trigger("get_invoices");
	},
	get_invoices: frm => {
		if (!frm.doc.invoice)
			return
		frappe.run_serially([
			frappe.dom.freeze(__("Please Wait...")),
			frm.call("get_claims"),
			frappe.dom.unfreeze(),
			frm.refresh(),
			frappe.show_alert("Fetched Invoices Successfully")	

		])
	},
	calculate_totals: frm => {
		if (frm.doc.claims.length <= 0)
			return
		let total_claimed = 0;
		let total_paid = 0;
		let total_received = 0;
		let total_pending = 0;
		let fee = frm.doc.claims[0].fee;
		
		$.map(frm.doc.claims, row => {
			total_claimed += flt(row.claimed_amount);
			total_paid += flt(row.paid_amount);
			total_received += flt(row.received_amount);
			total_pending += flt(row.pending_amount);
		});
		frm.set_value("total_claimed", total_claimed);
		frm.set_value("total_to_receive", total_claimed * (1 - fee));
		frm.set_value("total_fee", total_claimed * fee);
		
		frm.set_value("total_paid", total_received);
		frm.set_value("total_received", total_received * (1 - fee));
		frm.set_value("total_fee_paid", total_received * fee);

		frm.set_value("grand_total_paid", total_paid);
		frm.set_value("total_pending", total_pending);
	}	
});

frappe.ui.form.on("Claim", {
	received_amount: (frm, cdt, cdn) => {
		row = frappe.model.get_doc(cdt,cdn);
		amount = flt(row.claimed_amount) - flt(row.received) - flt(row.paid_amount);
		frappe.model.set_value(cdt, cdn, "pending_amount", amount);
		frm.trigger("calculate_totals");
	}
});
