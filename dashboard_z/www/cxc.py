import os, re
import frappe
from frappe import _
from frappe.utils import nowdate, add_months
import frappe.sessions
from six import text_type
from api import get_physician_id


def get_context(context):
	frappe.errprint(frappe.session.user)
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
	user_name = frappe.get_value("User", frappe.session.user, "full_name") if frappe.session.user != "Administrator" else "Lewin Villar"
	physician = 'PHY-00006' if frappe.session.user == "Administrator" else get_physician_id(frappe.session.user)
	fact_fiscal = get_fiscal_invoices(physician)
	context.update({
		"no_cache": 1,
		"build_version": get_build_version(),
		"include_js": hooks["app_include_js"],
		"include_css": hooks["app_include_css"],
		"usr" : frappe.session.user,
		"usr_name" : user_name,
		"sounds": hooks["sounds"],
		"boot": boot if context.get("for_mobile") else boot_json,
		"csrf_token": csrf_token,
		"background_image": (boot.status != 'failed' and
			(boot.user.background_image or boot.default_background_image) or None),
		"google_analytics_id": frappe.conf.get("google_analytics_id"),
		"mixpanel_id": frappe.conf.get("mixpanel_id"),
		"facturas_fiscal": fact_fiscal,
		"total_fact_fiscal":sum(i.grand_total for i in fact_fiscal),
		"paid_fact_fiscal":sum(i.paid_amount for i in fact_fiscal),
	})

def get_fiscal_invoices(physician):
	return frappe.db.sql("""
		SELECT
			`tabSales Invoice`.name,
			`tabSales Invoice`.ncf,
			`tabSales Invoice`.customer_name,
			`tabSales Invoice`.posting_date as send_date,
			`tabJournal Entry`.voucher_type,
			`tabSales Invoice`.grand_total,
			`tabSales Invoice`.grand_total - outstanding_amount as paid_amount,
			`tabJournal Entry`.posting_date as paid_on
		FROM 
			`tabSales Invoice`
		LEFT JOIN
			`tabJournal Entry`
		ON
			`tabSales Invoice`.name = `tabJournal Entry`.reference_name
		AND
			`tabJournal Entry`.docstatus = 1
		WHERE
			`tabSales Invoice`.physician = %s
		AND
			`tabSales Invoice`.invoice_type = 'Suppliers'

		AND
			`tabSales Invoice`.docstatus = 1
		ORDER BY 
			`tabSales Invoice`.posting_date
		""", physician, as_dict=True)

def get_build_version():
	return str(os.path.getmtime(os.path.join(frappe.local.sites_path, '.build')))