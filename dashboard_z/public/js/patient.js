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
	tax_id: frm => {
		frm.set_value("tax_id", mask_ced_pas_rnc(frm.doc.tax_id));
	},
	phone: frm => {
		frm.set_value("phone", mask_phone(frm.doc.phone));
	},
	mobile: frm => {
		frm.set_value("mobile", mask_phone(frm.doc.mobile));
	}
});


function valida_cedula(ced) {
    var c = ced.replace(/-/g, '');
    var Cedula = c.substr(0, c.length - 1);
    var Verificador = c.substr(c.length - 1, 1);
    var suma = 0;

    if (c.length < 11) {
        frappe.msgprint("La Cedula ingresada no es valida!")
        return undefined
    }

    for (i = 0; i < Cedula.length; i++) {
        mod = "";
        /*
            se evaluan la posicion en la que esta cada digito, si esta en una
            posicion par el multiplicador sera 1 de lo contrario el 
            multiplicador sera 2
            Ex. 12121212121
            223-0087201-1
        */
        if ((i % 2) == 0) {
            mod = 1
        } else {
            mod = 2
        }
        //luego se multiplica el valor de la posicion con su multiplicador
        res = Cedula.substr(i, 1) * mod;
        /* en caso de que el multiplicador sea mayor que 9 se suman ambos 
            digitos
            Ex. res = 14 entonces sumamos 1 + 4 = 5
            luego acumulamos el reultado
         */
        if (res > 9) {
            res = res.toString();
            uno = res.substr(0, 1);
            dos = res.substr(1, 1);
            res = eval(uno) + eval(dos);
        }
        suma += eval(res);
    }
    /*
        luego a 10 le restamos el modulo del acumulativo, 
    */
    el_numero = (10 - (suma % 10)) % 10;
    if (el_numero == Verificador && Cedula.substr(0, 3) != "000") {
        return "{0}{1}{2}-{3}{4}{5}{6}{7}{8}{9}-{10}".format(c)
    } else {
        frappe.msgprint("La Cedula ingresada no es valida!")
        return undefined
    }
}

function mask_ced_pas_rnc(input)
{
    if (!input)
    	return
    
    input = input.trim().replace(/-/g,"")
    
    if (input.length == 11)
        return ("{0}{1}{2}-{3}{4}{5}{6}{7}{8}{9}-{10}".format(input));

    if (input.length == 9)
        return ("{0}-{1}{2}-{3}{4}{5}{6}{7}-{8}".format(input));
    
    return valida_cedula(input)
}

function mask_phone(phone)
{
    temp = phone.trim().replace(/-/g,"")

    if (temp.length == 10)
        return ("({0}{1}{2}) {3}{4}{5}-{6}{7}{8}{9}".format(temp));
    else
        return phone;

    /*var pattern = new RegExp("((^[0-9]{3})[0-9]{3}[0-9]{4})$");
    var pattern1 = new RegExp("([(][0-9]{3}[)] [0-9]{3}-[0-9]{4})$");
    var pattern2 = new RegExp("([(][0-9]{3}[)][0-9]{3}-[0-9]{4})$");

    if(pattern.test(phone))
        return ("({0}{1}{2}) {3}{4}{5}-{6}{7}{8}{9}".format(phone));
    else if(pattern1.test(phone))
        return phone;
    else if(pattern2.test(phone))
        return ("{0}{1}{2}{3}{4} {5}{6}{7}{8}{9}{10}{11}{12}".format(phone));*/
}

String.prototype.format = function () {
    "use strict";

    var formatted = this;
    for (var prop in arguments[0]) {
        if (arguments[0].hasOwnProperty(prop)) {
            var regexp = new RegExp("\\{" + prop + "\\}", "gi");
            formatted = formatted.replace(regexp, arguments[0][prop]);
        }
    }
    return formatted;
};