frappe.listview_settings['Payment Processing Tool'] = {
    "add_fields": ["status", "docstatus"],
    "onload": (listview) => {
        
    },
    "get_indicator": (doc) => {
        if (doc.status === "UNPAID") {
            return ["UNPAID", "red", "status,=,UNPAID"]
        } else if (doc.status === "PARTIALLY PAID") {
            return ["PARTIALLY PAID", "blue", "status,=,PARTIALLY PAID"]
        } else if (doc.status === "PAID") {
            return ["PAID", "blue", "status,=,PAID"]
        } 
    }
}