# -*- coding: utf-8 -*-
# Copyright (c) 2019, TZCODE and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import json
from frappe import _
from frappe.utils import nowdate
from frappe.model.document import Document
from dashboard_z.utils.api import invoice_to_claim


class PaymentProcessingTool(Document):
	def validate(self):
		if frappe.db.get_value("Sales Invoice", self.invoice, "docstatus") > 1:
			frappe.throw("No es posible recibir pagos a una factura cancelada!")
			
		self.calculate_totals()
		self.update_status()
	
	def update_status(self):
		if self.grand_total_paid == 0:
			self.status = "UNPAID"
		if self.grand_total_paid > 0:
			self.status = "PARTIALLY PAID"
		if self.grand_total_paid >= self.total_claimed:
			self.status = "PAID"

	def get_claims(self):
		if not self.invoice:
			return 

		filters = {
			"parent": self.invoice,
			"idx": 1
		}

		paid_invoices = frappe.db.get_value("Sales Invoice Item", filters, "paid_sales_invoices")

		if not paid_invoices:
			return
		# Let's clear the table first 
		self.claims = []
		
		paid_invoices = paid_invoices.split(',')
		
		for i in paid_invoices:
			self.append("claims", invoice_to_claim(i))
		
		self.calculate_totals()
	
	def calculate_totals(self):
		if len(self.claims) <= 0:
			return

		fee = self.claims[0].fee

		self.total_claimed = self.total_paid = \
			self.total_received = self.total_pending = self.grand_total_paid =.00		
		
		for row in self.claims:
			self.total_claimed += row.claimed_amount or .00
			self.total_paid += row.received_amount or .00
			
			self.total_received += row.received_amount or .00
			self.total_pending += row.pending_amount or .00
			
			self.grand_total_paid += row.paid_amount or .00
		
		self.total_to_receive = self.total_claimed * (1 - fee)
		self.total_fee = self.total_claimed * fee
		
		self.total_received = self.total_paid * (1 - fee)
		self.total_fee_paid = self.total_paid * fee

	@frappe.whitelist()
	def make_payment_entry(self):
		if self.total_received <= 0:
			frappe.throw(_("Received Amount must be greather than 0"))
		self.apply_payment_to_invoices()
		self.create_pe()
	
	def apply_payment_to_invoices(self):
		for claim in self.claims:
			dt = "Sales Invoice"
			if not frappe.db.exists(dt, claim.document):
				continue
			
			recvd = frappe.get_value(dt, claim.document, "received_amount")
			recvd +=  claim.received_amount
			frappe.db.sql("""
				UPDATE
					`tabSales Invoice`
				SET
					received_amount = %s
				where 
					name = %s
				""", (recvd, claim.document))
	def generate_payment_dict(self):
		inv_dict = []
		for claim in self.claims:
			inv_dict.append({
				"document": claim.document,
				"received_amount": claim.received_amount,
			})
		return json.dumps(inv_dict)

	def create_pe(self):
		pe = frappe.new_doc("Journal Entry")
		defaults = frappe.defaults.get_defaults()
		bank_acct, receivable_account, fee_account, discount_acct = frappe.db.get_value(
			"Company",
			defaults.company,
			[
				"default_bank_account",
				"default_receivable_account",
				"default_ars_fee_account",
				"default_ars_disc_account"
			]
		)
		pe.update({
			"voucher_type": "Bank Entry",
			"posting_date": self.posting_date,
			"physician": self.physician,
			"cheque_no": self.ncf,
			"reference_name": self.invoice,
			"invoice_dict": self.generate_payment_dict(),
			"cheque_date": self.posting_date,
			"cheque_no": "Pago Factura {} via Payment Processing Tool".format(self.ncf),
			"user_remark": "Received Through Payment Processing Tool",
		})
		
		if self.other_discounts < 0:
			frappe.throw("Other Discounts must be greater than 0")

		add_account(pe, bank_acct, self.total_paid - self.other_discounts - self.total_fee_paid, True)
		
		if self.other_discounts:
			add_account(pe, fee_account, self.other_discounts, True)
		
		if self.total_fee_paid:
			add_account(pe, discount_acct, self.total_fee_paid, True)

		add_account(pe, receivable_account, self.total_paid, False, "Customer", self.supplier, "Sales Invoice", self.invoice)
		
		pe.save()
		pe.submit()
		self.payment = pe.name

def add_account(doc, account, amount, debit=True, party_type=None, party=None, reference_type=None, reference_name=None):
		doc.append("accounts",{
		"account": account,
		"credit_in_account_currency": 0.000 if debit else amount,
		"debit_in_account_currency":  amount if debit else 0.000,
		"reference_type": reference_type,
		"reference_name": reference_name,
		"party_type": party_type,
		"party": party,
	})
