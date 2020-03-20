# -*- coding: utf-8 -*-
# Copyright (c) 2019, TZCODE and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Claim(Document):
	def validate(self):
		self.update_status()
	
	def update_status(self):
		status = 'Pending'

		if self.paid_amount > 0:
			status = 'Partially Paid'
		if self.paid_amount >= self.claimed_amount:
			status = 'Paid'


