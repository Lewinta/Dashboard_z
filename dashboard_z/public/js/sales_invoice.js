frappe.provide("dashboard_z.sales_invoice");

frappe.ui.form.on("Sales Invoice", {
    refresh: frm => {
        // const events = ["set_physician_query"];
        const events = ["add_fetch_events"];
        let show = frm.doc.invoice_type == "Suppliers";
        $.map(events, event => {
            frm.trigger(event);
        });
        frm.toggle_reqd("patient", !show);
        frm.toggle_display("patient", !show);
        frm.toggle_display("customer", show);

    },
    validate: frm => {
        const no_verif = ["Private Customers", "Insurance Customers"]
        const {
            paid_amount,
            grand_total,
            invoice_type,
            authorization_no
        } = frm.doc;
        frappe.run_serially([
            frm.trigger("refresh_outside_amounts"),
            ()=> {
                    if (paid_amount != grand_total && no_verif.includes(invoice_type)){
                        frappe.msgprint("Favor verificar que el monto recibido $"+ paid_amount +" sea igual al facturado $"+ grand_total)
                        validated = false;
                    }
                },
            ()=> {
                    if (invoice_type == "Insurance Customers" && !authorization_no){
                        frappe.msgprint("Favor ingresar el numero de autorizacion para facturas con seguro")
                        validated = false;
                    }
            }
        ])
        frm.set_value("title", frm.doc.customer_name);
    },
    add_fetch_events: frm => {
        frm.add_fetch("physician", "hospital", "clinic");
        frm.add_fetch("patient", "ars", "ars");
        frm.add_fetch("patient", "nombre_ars", "ars_name");
        frm.add_fetch("patient", "nss", "nss");
    },
    set_item_queries: frm => {
        const {invoice_type, ars, physician, selling_price_list} = frm.doc;
        let pl = selling_price_list;
        
        if(invoice_type == "Insurance Customers")
            pl = ars;

        if(invoice_type == "Private Customers")
            pl = physician;
             
        frm.set_query("item_code", "items", () => {
                if ( ["Insurance Customers", "Private Customers"].includes(invoice_type)) {
                    return {
                        "query": "dashboard_z.queries.item_by_ars",
                        "filters": {
                            "ars": pl,
                            "physician": physician
                        }
                    }
                }
                else{
                    return{
                        "filters":{
                            "item_name": "Reclamaciones"
                        }
                    }
                }
            });
    },
    invoice_type: frm => {
        const {physician, customer, invoice_type} = frm.doc;

        let show = invoice_type == "Suppliers";
        frm.trigger("set_customer_query");
        frm.trigger("set_default_serie");
        frm.toggle_reqd("patient", !show);
        frm.toggle_display("patient", !show);
        frm.toggle_display("customer", show);

        frm.set_value("is_pos", !show);

        if (customer && physician && invoice_type == "Private Customers")
            frm.set_value("selling_price_list", physician)
    },
    patient: frm => {
        const {patient} = frm.doc;

        if(!patient){
            let fields = ["customer", "ars", "ars_name", "nss"]
            $.map(fields, field => {
                frm.set_value(field, "");
            })
            return
        }

        frappe.db.get_value("Patient", patient, "customer", ({customer}) => {
            if(!customer)
                frappe.throw("Favor asociar el paciente seleccionado a un cliente!");
            
            frm.set_value("customer", customer);
        });
    },
    customer: frm => {
        let price_list = frm.doc.invoice_type == "Insurance Customers" ? frm.doc.ars : frm.doc.physician
        frappe.run_serially([
            () => frm.trigger("set_item_queries"),
            () => frm.set_value("selling_price_list", price_list),
            () => frm.set_value("title", frm.doc.customer_name),
            () => frappe.timeout(2.5),
            () => {
                if(frm.doc.invoice_type != "Suppliers")
                    return
 
                frm.add_custom_button("Cargar Facturas", () => {
                    let d = new frappe.ui.form.MultiSelectDialog({
                        "doctype": "Sales Invoice",
                        "target": frm,
                        "date_field": "posting_date",
                        "page_length": 10000,
                        "setters": {
                            "ars": frm.doc.customer,
                        },
                        "get_query": () => {
                            let filters = {
                                "filters": {
                                    "customer_group": "Customers",
                                    "invoice_type": "Insurance Customers",
                                    "clinic": frm.doc.clinic,
                                    "physician": frm.doc.physician,
                                    "payment_status": frm.doc.is_return == 1 ? "PAID": "UNPAID",
                                    "docstatus": ["<", "2"],
                                }
                            };
                            
                            if (frm.doc.clinic)
                                filters.clinic = frm.doc.clinic
                            
                            return filters
                        },
                        "action": (selections, args) => {

                            if (selections.length == 0) {
                                frappe.throw("Favor de seleccionar las facturas!");
                            }

                            d.dialog.hide();
                            dashboard_z.sales_invoice.add_row_and_update_sales_invoices(frm, selections, args);
                        }
                    });

                    d.dialog.fields_dict.ars.df.get_query = () => {
                        return {
                            "query": "dashboard_z.queries.customer_query",
                            "filters": {
                                "customer_group": "ARS"
                            }
                        };
                    };
                });
            }
        ]);
    },
    set_default_serie: frm => {
        const {invoice_type} = frm.doc;
        let serie = invoice_type == "Suppliers" ? "B01.########" : "B02.########";
        frm.set_value("naming_series", serie);
    },
    set_physician_query: frm => {
       // Let's set physician Query
        frm.set_query("physician", event => {
            return {
                "filters": {
                    "supplier_group": "Individual"
                }
            }
        });
    },
    set_customer_query: frm => {
        // Let's set Customers Query
        frm.set_query("customer", event => {
            let {invoice_type, physician} = frm.doc;
            let customer_group = invoice_type == "Suppliers" ? "ARS" : "Customers" ;
            let condition = ["in", "Customers"]
            let filters = {}
            filters.customer_group = condition
            filters.physician = physician

            if (invoice_type == "Suppliers") {
                condition = ["in", "ARS"]
                filters = {}
                filters.customer_group = condition
            } 

            if (invoice_type != "Suppliers") {
                filters.physician = physician
            } 
            console.log(filters);
            return {
                "query": "erpnext.controllers.queries.customer_query",  
                "filters": filters
            }
        });
    },
    physician: frm => {
        if (!frm.doc.physician){
            frm.set_value("coverage", 0.00);
            
            return
        }
        frm.trigger("get_coverage");
        frm.set_value("customer", "");
        frm.set_value("patient", "");
        frm.trigger("set_customer_query");
    },
    coverage: frm => {
        const {coverage, items} = frm.doc;
        
        if (!coverage)
            return
        
        $.map(items, item => {
            frappe.model.set_value(
                item.doctype,
                item.name,
                "coverage",
                coverage
            );
        });
    },
    get_coverage: frm => {
        frappe.db.get_value(
            "Physician Defaults",
            frm.doc.physician,
            "default_coverage",
            ({default_coverage})=> {
                frm.set_value("coverage", default_coverage)
            }
        );
    },
    calculate_payments: frm => {
        var paid_amount = 0.0;
        var base_paid_amount = 0.0;
        if(frm.doc.is_pos) {
            $.each(frm.doc['payments'] || [], (index, data) => {
                data.base_amount = flt(data.amount * frm.doc.conversion_rate, precision("base_amount"));
                paid_amount += data.amount;
                base_paid_amount += data.base_amount;
            });
        } else if(!frm.doc.is_return){
            frm.doc.payments = [];
        }

        frm.set_value("paid_amount", flt(paid_amount, precision("paid_amount")));
        frm.set_value("base_paid_amount", flt(base_paid_amount, precision("base_paid_amount")));
    },
    item_table_update: (frm, cdt, cdn) => {
        frappe.run_serially([
            () => row = frappe.get_doc(cdt, cdn),
            () => console.log(row),
            () => frappe.timeout(0.5),
            () => {if(row && !row.item_code) return},
            () => row.difference_amount = isNaN(row.difference_amount) ? 0.00 : row.difference_amount,
            () => row.rate = isNaN(row.rate) ? 0.00 : row.rate,
            // () => apply_percent = apply_percent(row),
            // () => row.authorized_amount = apply_percent ? row.rate * coverage : 0,
            () => row.price_list_rate = row.price_list_rate && !row.rate ? row.price_list_rate : row.rate,
            () => calculate_totals(frm, cdt, cdn),
            // () => row.difference_amount += row.margin_rate_or_amount,
            // () => row.amount += row.adjustment,
            () => refresh_field("items"),
            () => frm.trigger("refresh_outside_amounts"),
        ])

    },
    calculate_pending_amount: frm => {
        const {grand_total, paid_amount} = frm.doc;
        frm.set_value("outstanding_amount", grand_total - paid_amount); 
    },
    refresh_outside_amounts: frm => {
        let total_authorized_amount = 0.000;
        let total_claimed_amount = 0.000;
        let total_difference_amount = 0.000;
        let total_copago_amount = 0.000;
        let total_adjustment = 0.000;
        let total_taxes = 0.000;
        let {invoice_type, total_taxes_and_charges} = frm.doc;

        $.map(frm.doc.items, row => {
            let adj_percentage = row.price_list_rate * (row.adjustment_percentage / 100.0)
            total_authorized_amount += row.authorized_amount;
            total_claimed_amount += row.claimed_amount;
            total_difference_amount += row.difference_amount;
            // total_copago_amount += row.copago;
            total_adjustment += row.adjustment_type == "Amount" ? row.adjustment_amount : adj_percentage;
        });
        frappe.run_serially([
            frm.set_value("claimed_amount", total_claimed_amount),
            frm.set_value("authorized_amount", total_authorized_amount),
            frm.set_value("difference_amount", total_difference_amount),
            frm.set_value("total_adjustment", total_adjustment),
            // frm.set_value("copago", total_copago_amount),
            total_taxes = invoice_type == "Alquiler" ? flt(total_taxes_and_charges) : 0.00,
            update_payment_table(frm, {
                "total_authorized_amount": total_authorized_amount, 
                "total_copago": total_copago_amount, 
                "total_difference_amount": total_difference_amount + total_taxes }),
            // frm.set_value("grand_total", frm.doc.grand_total += frm.doc.total_adjustment),
            frm.trigger("calculate_payments"),
            // () => frappe.timeout(0.5),
            // frm.trigger("calculate_pending_amount"),
            // frm.refresh(),
            refresh_field("items"),
        ])
    }
});

$.extend(dashboard_z.sales_invoice, {
    "add_row_and_update_sales_invoices": (frm, selections, args) => {
        let opts = {
            "method": "dashboard_z.utils.api.update_sales_invoice"
        };

        opts.args = {
            "doc": frm.doc,
            "selections": selections.join(","),
            "args": args
        };

        frappe.call(opts).done((response) =>{
            let doc = response.message;

            if (doc) {
                frappe.model.sync(doc) && frm.refresh();
            }
        }).fail(() => frappe.msgprint("¡Ha ocurrido un error!"));
    },
});

frappe.ui.form.on("Sales Invoice Item", {
    item_code: (frm, cdt, cdn) => {
        const {tipo_de_factura} = frm.doc;
        const not_allowed = ["Alquiler", "Suppliers"];

        let condition = !not_allowed.includes(tipo_de_factura) ? true : false
        
        frappe.run_serially([
            () => frappe.timeout(0.3),
            () => condition && frm.events.item_table_update(frm, cdt, cdn),
            () => frm.refresh_fields()
        ]);

        frm.trigger("refresh_outside_amounts");
    },
    adjustment_amount: (frm, cdt, cdn) => {
       frappe.run_serially([
            () => frappe.timeout(0.3),
            () => frm.events.item_table_update(frm, cdt, cdn),
        ]);

    },
    adjustment_percentage: (frm, cdt, cdn) => {
       frappe.run_serially([
            () => frappe.timeout(0.3),
            () => frm.events.item_table_update(frm, cdt, cdn),
        ]);
    },
    margin_rate_or_amount: (frm, cdt, cdn) => {
        row = frappe.model.get_doc(cdt,cdn);

        frappe.run_serially([
            () => frappe.timeout(0.3),
            () => frm.events.item_table_update(frm, cdt, cdn),
        ]);
    },
    rate: (frm, cdt, cdn) => {
        let condition = frm.doc.tipo_de_factura != "Alquiler" && frm.doc.tipo_de_factura != "Proveedores" ? true : false
        frappe.run_serially([
            () => frappe.timeout(0.3),
            () => condition && frm.events.item_table_update(frm, cdt, cdn),
        ]);
    },
    coverage: (frm, cdt, cdn) => {
        frappe.run_serially([
            () => frappe.timeout(0.3),
            () => frm.events.item_table_update(frm, cdt, cdn),
        ]);
    },
    items_add: (frm, cdt, cdn) => {
        row = frappe.model.get_doc(cdt,cdn);
        row.coverage = frm.doc.coverage;
        row.rate = row.coverage * row.rate;
    },
    items_remove: (frm, cdt, cdn) => {
        // frm.trigger("refresh_outside_amounts");
    }

});

function update_payment_table(frm, opts){

        $.grep(frm.doc.payments, (payment) => {
            return payment.mode_of_payment == "Efectivo";
        }).map((payment) => {
            payment.amount = opts.total_difference_amount;
        });

        $.grep(frm.doc.payments, (payment) => {
            return payment.mode_of_payment == "Co-Pago";
        }).map((payment) => {
            payment.amount = opts.total_copago;
        });

        $.grep(frm.doc.payments, (payment) => {
            return payment.mode_of_payment == "Seguro";
        }).map((payment) => {
            payment.amount = opts.total_authorized_amount;
        });

        $.grep(frm.doc.payments, (payment) => {
            return payment.mode_of_payment == "Meds";
        }).map((payment) => {
            payment.amount = opts.total_authorized_amount;
        });

        $.grep(frm.doc.payments, (payment) => {
            return payment.mode_of_payment == "Servimerd";
        }).map((payment) => {
            payment.amount = opts.total_difference_amount;
        });

        refresh_field("payments");
    }

function calculate_totals(frm, cdt, cdn){
    let row = frappe.get_doc(cdt, cdn);
    let coverage = eval(row.coverage) ? row.coverage  : frm.doc.coverage;
    let adj_percentage = row.price_list_rate * (flt(row.adjustment_percentage) / 100.0)
    console.log("Let's Cal totals")
    if (frm.doc.invoice_type == "Insurance Customers")
        row.authorized_amount = row.price_list_rate * flt(coverage / 100.00)
    else
        row.authorized_amount = 0.00;

    
    if (frm.doc.invoice_type == "Insurance Customers") 
        row.claimed_amount = row.price_list_rate;
    else
        row.claimed_amount = 0.00;

    if (frm.doc.invoice_type == "Insurance Customers") 
        row.difference_amount = row.price_list_rate - row.authorized_amount;
    
    if (frm.doc.invoice_type == "Private Customers") 
        row.difference_amount = row.price_list_rate;
    
    if (!row.adjustment_type)
        return
    console.log("****************\n");
    console.log(row);
    row.difference_amount += row.adjustment_type == "Amount" ? flt(row.adjustment_amount)  : flt(adj_percentage);
    row.amount            += row.adjustment_type == "Amount" ? flt(row.adjustment_amount)  : flt(adj_percentage);
    row.rate            += row.adjustment_type == "Amount" ? flt(row.adjustment_amount)  : flt(adj_percentage);
    console.log(row);
    console.log("****************\n");
}

function apply_percent(row){

    if (row && row.item_name)
        return row.item_name.substring(0,10) != "Diferencia";
}