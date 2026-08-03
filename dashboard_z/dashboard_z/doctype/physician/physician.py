# Copyright (c) 2026, TZCode and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Physician(Document):
	# Business logic (autoname / validate / after_insert) is handled via
	# doc_events in dashboard_z/hooks.py -> dashboard_z.hook.physician
	pass
