import os, re
import frappe
from frappe import _
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
		"mixpanel_id": frappe.conf.get("mixpanel_id")
	})

	return context

def get_build_version():
	return str(os.path.getmtime(os.path.join(frappe.local.sites_path, '.build')))
