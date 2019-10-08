import os, re
import frappe
from frappe import _
from frappe.utils import nowdate, add_months
import frappe.sessions
from six import text_type


def get_context(context):
	if (frappe.session.user == "Guest" or
		frappe.db.get_value("User", frappe.session.user, "user_type")=="Website User"):
		frappe.throw(_("You are not permitted to access this page."), frappe.PermissionError)

	hooks = frappe.get_hooks()
	try:
		boot = frappe.sessions.get()
	except Exception as e:
		boot = frappe._dict(status='failed', error = str(e))
		print(frappe.get_traceback())

	# this needs commit
	csrf_token = frappe.sessions.get_csrf_token()

	frappe.db.commit()

	boot_json = frappe.as_json(boot)

	# remove script tags from boot
	boot_json = re.sub("\<script\>[^<]*\</script\>", "", boot_json)

	context.update({
		"no_cache": 1,
		"build_version": get_build_version(),
		"include_js": hooks["app_include_js"],
		"include_css": hooks["app_include_css"],
		"usr" : frappe.session.user,
		"usr_name" : frappe.get_value("User", frappe.session.user, "full_name"),
		"sounds": hooks["sounds"],
		"boot": boot if context.get("for_mobile") else boot_json,
		"csrf_token": csrf_token,
		"background_image": (boot.status != 'failed' and
			(boot.user.background_image or boot.default_background_image) or None),
		"google_analytics_id": frappe.conf.get("google_analytics_id"),
		"mixpanel_id": frappe.conf.get("mixpanel_id"),
	})
	# phy_context = get_physician_context(frappe.session.user)
	phy_context = get_physician_context('jenneramirez2@gmail.com')
	context.update(phy_context)

	return context
def get_physician_context(physician):
	context = {}
	fact_seg = get_invoices(physician, "Insurance Customers")
	fact_pri = get_invoices(physician, "Private Customers")
	fact_ttl = get_invoices(physician)
	amt_fact_seg = sum([a.grand_total for a in fact_seg] if fact_seg else 0.00)
	amt_auth_seg = sum([a.authorized_amount for a in fact_seg])
	amt_clai_seg = sum([a.claimed_amount for a in fact_seg])
	amt_diff_seg = sum([a.difference_amount for a in fact_seg])
	amt_fact_pri = sum([a.grand_total for a in fact_pri])
	amt_fact_ttl = sum([a.grand_total for a in fact_ttl])
	
	context.update({
		"cant_fact_seg": len(fact_seg) if fact_seg else 0,
		"amt_fact_seg": amt_fact_seg or .00,
		"amt_auth_seg": amt_auth_seg or .00,
		"amt_clai_seg": amt_clai_seg if amt_clai_seg else .00,
		"amt_diff_seg": amt_diff_seg or .00,
		"cant_fact_pri": len(fact_pri) or 0,
		"amt_fact_pri": amt_fact_pri or .00,
		"cant_fact_ttl": len(fact_ttl) or 0,
		"amt_fact_ttl": amt_fact_ttl or .00,
	})

	return context

def get_invoices(physician, invoice_type=None):
	invoices = 0
	physician = get_physician_id(physician)
	today = nowdate()
	month_start = today[:-2]+'01'
	filters = {
		"physician": physician,
		"docstatus": 0,
		"posting_date": ['>=', month_start],
	}

	fields = ["claimed_amount", "difference_amount", "authorized_amount", "grand_total"]

	if invoice_type:
		filters.update({
			"invoice_type": invoice_type
		})

	invoices = frappe.get_list("Sales Invoice", filters, fields)
	return invoices

@frappe.whitelist()
def get_last_6_months():
	# physician = get_physician_id(physician)

	physician = 'PHY-00003'
	today = nowdate()
	headers = []
	ins_amt = []
	pri_amt = []

	total_ins = get_invoices_by_type (physician, 'Insurance Customers')
	total_pri = get_invoices_by_type (physician, 'Private Customers')

	for r in range(0, 6):
		month = get_month(add_months(today, -r))
		ins_row = filter(lambda x, month=month: x.month == month, total_ins)
		pri_row = filter(lambda x, month=month: x.month == month, total_pri)

		ins = ins_row[0].grand_total  if ins_row else .000
		pri = pri_row[0].grand_total  if pri_row else .000
	 	
	 	headers.append(month_to_letter(month))
	 	ins_amt.append(ins)
	 	pri_amt.append(pri)

	headers.reverse()
	ins_amt.reverse()
	pri_amt.reverse()
	max_val = max(ins_amt + pri_amt)
	max_str = str(int(max_val))
	base = int(max_str[:2])
	limit = (base + 2) * pow(10 , len(max_str)-2)

	return {
		"headers": headers,
		"ins_amt": ins_amt,
		"pri_amt": pri_amt,
		"maximum": limit,
	}

def get_month(date):
	return int(date.split('-')[1])

def month_to_letter(month):
	months = {
		1 : _("Jan"), 2 : _("Feb"),
		3 : _("Mar"), 4 : _("Apr"),
		5 : _("May"), 6 : _("Jun"),
		7 : _("Jul"), 8 : _("Aug"),
		9 : _("Sep"), 10: _("Oct"),
		11: _("Nov"), 12: _("Dec"),
	}
	return months.get(month)

def get_physician_id(physician):
	return frappe.get_value("Physician", {"user_id": physician}, "name")

def get_invoices_by_type(physician, invoice_type):
	return frappe.db.sql("""
		SELECT
			SUM(grand_total) grand_total,
			invoice_type,
			MONTH(posting_date) month 
		FROM 
			`tabSales Invoice`
		WHERE
			physician = %s
		AND
			invoice_type = %s
		GROUP BY
			month
		ORDER BY 
			month  
		LIMIT 
			6;
	""", (physician, invoice_type), as_dict=True)

def get_build_version():
	return str(os.path.getmtime(os.path.join(frappe.local.sites_path, '.build')))
