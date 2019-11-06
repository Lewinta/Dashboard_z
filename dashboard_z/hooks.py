# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "dashboard_z"
app_title = "Dashboard Z"
app_publisher = "TZCODE"
app_description = "A Admin/Dashboard html app for ERPNext"
app_icon = "fa fa-tachometer"
app_color = "green"
app_email = "lewinvillar@tzcode.tech"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/dashboard_z/css/dashboard_z.css"
app_include_js = "/assets/js/reportview.js"

# include js, css files in header of web template
# web_include_css = "/assets/dashboard_z/css/dashboard_z.css"
# web_include_js = "/assets/dashboard_z/js/dashboard_z.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Sales Invoice" : "public/js/sales_invoice.js",
	"Physician" : "public/js/physician.js",
	"Patient Appointment" : "public/js/patient_appointment.js",
	"Patient" : "public/js/patient.js",
	"Item Price" : "public/js/item_price.js",
	"Customer" : "public/js/customer.js",
	"Item" : "public/js/item.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "dashboard_z.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
website_generators = ["Doctor Dashboard"]

# Installation
# ------------

# before_install = "dashboard_z.install.before_install"
# after_install = "dashboard_z.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "dashboard_z.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
on_session_creation = "dashboard_z.utils.api.on_session_creation"
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Sales Invoice": {
		"on_submit": "dashboard_z.hook.sales_invoice.on_submit",
		"on_cancel": "dashboard_z.hook.sales_invoice.on_cancel",
	},
	"Physician": {
		"autoname": "dashboard_z.hook.physician.autoname",
		"validate": "dashboard_z.hook.physician.validate",
		"after_insert": "dashboard_z.hook.physician.after_insert",
	},
	"Customer": {
		"after_insert": "dashboard_z.hook.customer.after_insert",
		"on_trash": "dashboard_z.hook.customer.on_trash",
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"dashboard_z.tasks.all"
# 	],
# 	"daily": [
# 		"dashboard_z.tasks.daily"
# 	],
# 	"hourly": [
# 		"dashboard_z.tasks.hourly"
# 	],
# 	"weekly": [
# 		"dashboard_z.tasks.weekly"
# 	]
# 	"monthly": [
# 		"dashboard_z.tasks.monthly"
# 	]
# }

# Testing
# -------

# before_tests = "dashboard_z.install.before_tests"

# Overriding Whitelisted Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "dashboard_z.event.get_events"
# }

