import frappe
from frappe.utils import flt

def item_by_ars(doctype, txt, searchfield, start, page_len, filters):

	if not filters.get("ars"): 
		return frappe.get_list("Item", filters={
			"item_code": ["not in", "Consultas, ALQUILER"]
		}, fields=["item_code"], as_list=True)

	result = frappe.db.sql("""
		SELECT
			item_code AS item,
			item_name,
			ars_name AS ars,
			physician_name AS physician,
			currency,
			price_list_rate AS price
		FROM
			`tabItem Price` AS price 
		WHERE
			price_list = '{1}'
		AND
			physician = '{2}'
		AND
			(item_code LIKE '%{0}%' OR item_name LIKE '%{0}%')
		AND
			item_code != 'Reclamaciones'
		ORDER BY item_code LIMIT 20
	""".format("%".join(txt.split()), filters.get("ars"), filters.get("physician")), as_dict=True)

	return [[row.item, "{1} $ {0}".format(flt(row.price, 2), row.currency), row.item_name] for row in result]

def customer_query(doctype, txt, searchfield, start, page_len, filters):
	txt = "%".join(txt.split())

	customer_list = frappe.get_list("Customer", {
		"name": ["like", "%{}%".format(txt) if txt else "%"],
		"customer_group": filters.get("customer_group") or "Clientes",
	}, ["distinct name", "customer_group"], order_by="name")

	return [[row.name, row.customer_group] for row in customer_list]
