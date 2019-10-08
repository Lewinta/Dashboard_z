# -*- coding: utf-8 -*-
# Copyright (c) 2019, TZCODE and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.jinja import render_template
from frappe.website.website_generator import WebsiteGenerator

class DoctorDashboard(WebsiteGenerator):
	website = frappe._dict(
		template = "templates/generators/dashboard.html"
	)
	def validate(self):
		self.page_name = self.name
