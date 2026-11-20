# Copyright (c) 2026, Finbyz Tech Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.accounts.party import get_party_account


@frappe.whitelist()
def get_tax_template_details(template_type, template_name):
	"""Fetches taxes list (account_head, rate, description) from the selected tax template."""
	if not template_type or not template_name:
		return []

	if template_type not in ["Purchase Taxes and Charges Template", "Sales Taxes and Charges Template"]:
		return []

	template = frappe.get_cached_doc(template_type, template_name)
	taxes = []
	for row in template.get("taxes") or []:
		taxes.append({
			"account_head": row.account_head,
			"rate": flt(row.rate),
			"description": row.description or template_name,
			"charge_type": row.charge_type or "On Net Total"
		})
	return taxes


def get_accounting_entry_settings():
	"""Fetches global defaults from Accounting Entry Settings Single DocType."""
	if frappe.db.exists("DocType", "Accounting Entry Settings"):
		return frappe.get_single("Accounting Entry Settings")
	return frappe._dict()


def get_mode_of_payment_for_account(account, company, account_type):
	"""Resolves the appropriate Mode of Payment based on linked account or account type."""
	# 1. Check if a Mode of Payment has this account explicitly configured for this company
	mop = frappe.db.get_value(
		"Mode of Payment Account",
		{"default_account": account, "company": company},
		"parent"
	)
	if mop and frappe.db.get_value("Mode of Payment", mop, "enabled"):
		return mop

	# 2. Check if a Mode of Payment matches the account_type ('Cash' or 'Bank')
	mop = frappe.db.get_value(
		"Mode of Payment",
		{"type": account_type, "enabled": 1},
		"name"
	)
	if mop:
		return mop

	# 3. Fallback to any enabled Mode of Payment
	return frappe.db.get_value("Mode of Payment", {"enabled": 1}, "name")


class AccountingEntry(Document):
	def validate(self):
		self.validate_mandatory()
		self.set_company_currency()
		self.set_party_and_template_types()
		self.set_row_currencies_and_exchange_rates()
		self.validate_accounts()
		self.validate_cash_bank_account()
		self.validate_party_account()
		self.sync_auto_tax_rows()
		self.calculate_totals()

	def on_submit(self):
		self.create_and_submit_invoice()

	def on_cancel(self):
		self.cancel_linked_invoices()

	def on_trash(self):
		self.delete_linked_invoices()

	def validate_mandatory(self):
		if not self.company:
			frappe.throw(_("Company is mandatory"))
		if not self.posting_date:
			frappe.throw(_("Posting Date is mandatory"))
		if not self.accounts:
			frappe.throw(_("Please add at least one row in Accounting Entries table"))

	def set_company_currency(self):
		if self.company and not self.company_currency:
			self.company_currency = frappe.get_cached_value("Company", self.company, "default_currency")

	def set_party_and_template_types(self):
		# Sync Party Type based on Tax Type
		if self.tax_type == "Inward":
			self.party_type = "Supplier"
			template_type = "Purchase Taxes and Charges Template"
		else:
			self.party_type = "Customer"
			template_type = "Sales Taxes and Charges Template"

		# Sync tax_template_type in all child rows
		for row in self.accounts:
			row.tax_template_type = template_type

	def set_row_currencies_and_exchange_rates(self):
		company_currency = self.company_currency or "SAR"

		for row in self.accounts:
			# Auto fetch account currency if missing
			if not row.account_currency and row.account:
				row.account_currency = frappe.db.get_value("Account", row.account, "account_currency") or company_currency

			if not row.currency:
				row.currency = row.account_currency or company_currency

			if not row.exchange_rate:
				row.exchange_rate = 1.0

			if row.currency == company_currency:
				row.exchange_rate = 1.0

			# Calculate company currency amounts
			row.debit_in_company_currency = flt(flt(row.debit) * flt(row.exchange_rate), 2)
			row.credit_in_company_currency = flt(flt(row.credit) * flt(row.exchange_rate), 2)

	def validate_accounts(self):
		is_inward = self.tax_type == "Inward"

		for idx, row in enumerate(self.accounts, 1):
			if not row.account:
				frappe.throw(_("Row #{0}: Account is required").format(idx))

			# Ensure account belongs to this company and is not a group
			account_details = frappe.db.get_value(
				"Account",
				row.account,
				["company", "is_group", "account_type", "root_type", "disabled"],
				as_dict=1
			)
			if account_details:
				if account_details.company != self.company:
					frappe.throw(
						_("Row #{0}: Account {1} does not belong to Company {2}").format(
							idx, frappe.bold(row.account), frappe.bold(self.company)
						)
					)
				if account_details.is_group:
					frappe.throw(
						_("Row #{0}: Account {1} cannot be a group account").format(
							idx, frappe.bold(row.account)
						)
					)
				if account_details.disabled:
					frappe.throw(
						_("Row #{0}: Account {1} is disabled").format(idx, frappe.bold(row.account))
					)
				# Same rule as the Purchase / Sales Invoice item account filters
				blocked_root_type = "Income" if is_inward else "Expense"
				if account_details.root_type == blocked_root_type:
					frappe.throw(
						_("Row #{0}: {1} entries cannot use {2} account {3}").format(
							idx,
							_("Inward") if is_inward else _("Outward"),
							_(blocked_root_type),
							frappe.bold(row.account),
						)
					)

			# Each row becomes an invoice line, so it must sit on the invoice side:
			# Inward (Purchase) rows are debits, Outward (Sales) rows are credits.
			if is_inward and flt(row.credit) > 0:
				frappe.throw(
					_("Row #{0}: Inward entries take Debit amounts only. Remove the Credit amount on account {1}.").format(
						idx, frappe.bold(row.account)
					)
				)
			if not is_inward and flt(row.debit) > 0:
				frappe.throw(
					_("Row #{0}: Outward entries take Credit amounts only. Remove the Debit amount on account {1}.").format(
						idx, frappe.bold(row.account)
					)
				)

	def validate_cash_bank_account(self):
		if not self.is_paid:
			self.cash_bank_account = None
			return

		if not self.cash_bank_account:
			frappe.throw(_("Cash/Bank Account is mandatory when Is Paid is checked"))

		account = frappe.db.get_value(
			"Account",
			self.cash_bank_account,
			["company", "is_group", "account_type", "disabled"],
			as_dict=1,
		)
		if not account:
			frappe.throw(_("Cash/Bank Account {0} does not exist").format(frappe.bold(self.cash_bank_account)))
		if account.company != self.company:
			frappe.throw(
				_("Cash/Bank Account {0} does not belong to Company {1}").format(
					frappe.bold(self.cash_bank_account), frappe.bold(self.company)
				)
			)
		if account.is_group or account.disabled:
			frappe.throw(
				_("Cash/Bank Account {0} cannot be a group or disabled account").format(
					frappe.bold(self.cash_bank_account)
				)
			)
		if account.account_type not in ("Cash", "Bank"):
			frappe.throw(
				_("Cash/Bank Account {0} must have Account Type Cash or Bank").format(
					frappe.bold(self.cash_bank_account)
				)
			)

	def validate_party_account(self):
		# Inward creates a Purchase Invoice (Credit To, Payable),
		# Outward creates a Sales Invoice (Debit To, Receivable).
		if self.tax_type == "Inward":
			self.debit_to = None
			fieldname, account_type, label = "credit_to", "Payable", _("Credit To")
		else:
			self.credit_to = None
			fieldname, account_type, label = "debit_to", "Receivable", _("Debit To")

		# Shown only when a party is chosen, and defaults to that party's account
		if not self.party:
			self.debit_to = self.credit_to = None
			return

		if not self.get(fieldname):
			self.set(fieldname, get_party_account(self.party_type, self.party, self.company))

		account = self.get(fieldname)
		if not account:
			return

		details = frappe.db.get_value(
			"Account", account, ["company", "is_group", "account_type", "disabled"], as_dict=1
		)
		if not details:
			frappe.throw(_("{0} account {1} does not exist").format(label, frappe.bold(account)))
		if details.company != self.company:
			frappe.throw(
				_("{0} account {1} does not belong to Company {2}").format(
					label, frappe.bold(account), frappe.bold(self.company)
				)
			)
		if details.is_group or details.disabled:
			frappe.throw(
				_("{0} account {1} cannot be a group or disabled account").format(label, frappe.bold(account))
			)
		if details.account_type != account_type:
			frappe.throw(
				_("{0} account {1} must have Account Type {2}").format(
					label, frappe.bold(account), _(account_type)
				)
			)

	def sync_auto_tax_rows(self):
		"""Dynamically calculates taxes based on the selected tax templates (no hardcoded rate)."""
		if self.docstatus != 0:
			return

		if self.tax_method != "Auto":
			# Manually mode: remove any auto-generated tax rows
			self.accounts = [r for r in self.accounts if not r.is_auto_tax_row]
			return

		manual_rows = [r for r in self.accounts if not r.is_auto_tax_row and (flt(r.debit) > 0 or flt(r.credit) > 0)]
		is_inward = (self.tax_type == "Inward")
		template_type = "Purchase Taxes and Charges Template" if is_inward else "Sales Taxes and Charges Template"
		company_currency = self.company_currency or "SAR"

		# Map to accumulate tax amounts by account_head
		tax_summary = {}  # { account_head: { "amount": flt, "rate": flt, "description": str } }

		for r in manual_rows:
			base_amount = flt(r.debit_in_company_currency if is_inward else r.credit_in_company_currency)
			if base_amount <= 0:
				continue

			if r.tax_category:
				taxes = get_tax_template_details(template_type, r.tax_category)
				for tax in taxes:
					account_head = tax.get("account_head")
					rate = flt(tax.get("rate"))
					if account_head and rate > 0:
						calculated_tax = flt(base_amount * (rate / 100.0), 2)
						if account_head not in tax_summary:
							tax_summary[account_head] = {
								"amount": 0.0,
								"rate": rate,
								"description": tax.get("description", "")
							}
						tax_summary[account_head]["amount"] += calculated_tax

		# Preserve manual rows, remove old auto tax rows
		new_account_rows = [r for r in self.accounts if not r.is_auto_tax_row]

		# Append computed dynamic tax rows
		for account_head, data in tax_summary.items():
			tax_amount = flt(data["amount"], 2)
			if tax_amount > 0:
				new_account_rows.append(self.new_auto_tax_row(
					account_head=account_head,
					tax_amount=tax_amount,
					is_inward=is_inward,
					company_currency=company_currency,
					template_type=template_type
				))

		self.accounts = new_account_rows

	def new_auto_tax_row(self, account_head, tax_amount, is_inward, company_currency, template_type):
		row = self.append("accounts", {})
		row.account = account_head
		row.account_currency = company_currency
		row.currency = company_currency
		row.exchange_rate = 1.0
		row.debit = tax_amount if is_inward else 0.0
		row.debit_in_company_currency = tax_amount if is_inward else 0.0
		row.credit = 0.0 if is_inward else tax_amount
		row.credit_in_company_currency = 0.0 if is_inward else tax_amount
		row.tax_template_type = template_type
		row.is_auto_tax_row = 1
		return row

	def calculate_totals(self):
		total_debit = 0.0
		total_debit_cc = 0.0
		total_credit = 0.0
		total_credit_cc = 0.0

		for r in self.accounts:
			total_debit += flt(r.debit)
			total_debit_cc += flt(r.debit_in_company_currency)
			total_credit += flt(r.credit)
			total_credit_cc += flt(r.credit_in_company_currency)

		self.total_debit = flt(total_debit, 2)
		self.total_debit_company_currency = flt(total_debit_cc, 2)
		self.total_credit = flt(total_credit, 2)
		self.total_credit_company_currency = flt(total_credit_cc, 2)
		self.difference = flt(self.total_debit_company_currency - self.total_credit_company_currency, 2)

	def _linked_invoice_pairs(self):
		"""Returns [(fieldname, doctype), ...] for whichever invoices this
		Accounting Entry actually generated."""
		return [
			("purchase_invoice", "Purchase Invoice"),
			("sales_invoice", "Sales Invoice"),
		]

	def cancel_linked_invoices(self):
		for fieldname, doctype in self._linked_invoice_pairs():
			docname = self.get(fieldname)
			if not docname or not frappe.db.exists(doctype, docname):
				continue
			doc = frappe.get_doc(doctype, docname)
			if doc.docstatus == 1:
				doc.flags.ignore_permissions = True
				doc.cancel()


	def delete_linked_invoices(self):
		"""Called on_trash: cancels (if still submitted) and permanently
		deletes any Purchase/Sales Invoice this Accounting Entry generated,
		so deleting an Accounting Entry doesn't leave an orphaned invoice behind."""
		for fieldname, doctype in self._linked_invoice_pairs():
			docname = self.get(fieldname)
			if not docname or not frappe.db.exists(doctype, docname):
				continue
			doc = frappe.get_doc(doctype, docname)
			if doc.docstatus == 1:
				doc.flags.ignore_permissions = True
				doc.cancel()
			# docstatus is now 0 (draft, shouldn't normally happen) or 2 (cancelled)
			frappe.delete_doc(
				doctype, docname,
				ignore_permissions=True,
				force=True,
			)

	def _propagate_accounting_dimensions(self, invoice):
		"""Copy every enabled Accounting Dimension field value from this
		Accounting Entry header to the target invoice header, so that
		ERPNext can stamp them on the auto-created AP/AR GL entry."""
		try:
			dimensions = frappe.get_all(
				"Accounting Dimension",
				filters={"disabled": 0},
				fields=["fieldname"],
			)
		except Exception:
			return

		for dim in dimensions:
			fn = dim.fieldname
			val = self.get(fn)
			if val:
				try:
					invoice.set(fn, val)
				except Exception:
					pass

	def get_mode_of_payment(self):
		"""Mode of Payment for the header Cash/Bank Account (only when Is Paid)."""
		if not (self.is_paid and self.cash_bank_account):
			return None
		acc_type = frappe.db.get_value("Account", self.cash_bank_account, "account_type")
		return get_mode_of_payment_for_account(self.cash_bank_account, self.company, acc_type)

	def get_invoice_project(self, amount_field):
		"""First project found on a non-tax row, used on the invoice header."""
		for row in self.accounts:
			if not row.is_auto_tax_row and flt(row.get(amount_field)) > 0 and row.project:
				return row.project
		return None

	def make_purchase_invoice(self):
		"""Generates a standard ERPNext Purchase Invoice marked as Paid from this Accounting Entry."""
		settings = get_accounting_entry_settings()

		# 1. Resolve Supplier
		supplier = self.party or settings.get("default_supplier")
		if not supplier:
			frappe.throw(
				_("Supplier is required. Please specify a Supplier in the Accounting Entry or set Default Supplier in Accounting Entry Settings.")
			)

		# 2. Resolve Default Purchase Item
		default_item = settings.get("default_purchase_item")
		if not default_item:
			default_item = frappe.db.get_value("Item", {"is_purchase_item": 1, "disabled": 0}, "name")
		if not default_item:
			frappe.throw(
				_("Default Purchase Item is required. Please configure Default Purchase Item in Accounting Entry Settings.")
			)

		# 3. Mode of Payment for the header Cash/Bank Account (only when Is Paid)
		mode_of_payment = self.get_mode_of_payment()

		# 3b. Batch-fetch account_type for every distinct account on this entry,
		# so we can detect tax rows even when is_auto_tax_row wasn't set upstream.
		account_names = list({row.account for row in self.accounts if row.account})
		account_type_map = {
			d["name"]: d["account_type"]
			for d in frappe.get_all(
				"Account",
				filters={"name": ["in", account_names]},
				fields=["name", "account_type"],
			)
		}

		def _is_tax_row(row):
			return bool(row.is_auto_tax_row) or account_type_map.get(row.account) == "Tax"

		# Resolve a project to propagate to the invoice header (needed for accounts with mandatory project)
		invoice_project = self.get_invoice_project("debit")

		# 4. Instantiate Purchase Invoice Doc
		pi = frappe.new_doc("Purchase Invoice")
		pi.company = self.company
		pi.supplier = supplier
		if self.credit_to:
			pi.credit_to = self.credit_to
		pi.posting_date = self.posting_date
		pi.currency = self.company_currency
		pi.bill_no = self.ref_number or ""
		pi.bill_date = self.ref_date or self.posting_date
		pi.remarks = self.user_remark or _("Generated from Accounting Entry {0}").format(self.name)
		if invoice_project:
			pi.project = invoice_project

		# Propagate all accounting dimensions to the PI header so ERPNext
		# stamps them on the auto-created AP GL / Payment Ledger Entry.
		self._propagate_accounting_dimensions(pi)

		# Payment Details (Standard ERPNext is_paid flow). Amount is set after
		# totals are calculated below. Unpaid entries stay outstanding on the supplier.
		if self.is_paid:
			pi.is_paid = 1
			pi.cash_bank_account = self.cash_bank_account
			if mode_of_payment:
				pi.mode_of_payment = mode_of_payment

		# 5. Populate Items: Each separate non-tax debit row -> separate item row with its expense_account
		for row in self.accounts:
			if _is_tax_row(row):
				continue
			if flt(row.debit) <= 0:
				continue

			item_row = pi.append("items", {})
			item_row.item_code = default_item
			item_row.qty = 1.0
			item_row.rate = flt(row.debit)
			item_row.amount = flt(row.debit)
			item_row.expense_account = row.account
			if row.project:
				item_row.project = row.project
			if row.department:
				item_row.department = row.department
			# Propagate per-row accounting dimensions (task, employee, etc.)
			for _dim_field in ["task", "employee", "region_location", "asset"]:
				_val = row.get(_dim_field) or self.get(_dim_field)
				if _val:
					try:
						item_row.set(_dim_field, _val)
					except Exception:
						pass

		# 6. Populate Taxes: from Auto Tax rows OR rows on a Tax-type account
		for row in self.accounts:
			if _is_tax_row(row) and flt(row.debit) > 0:
				tax_row = pi.append("taxes", {})
				tax_row.charge_type = "Actual"
				tax_row.account_head = row.account
				tax_row.tax_amount = flt(row.debit)
				tax_row.description = frappe.db.get_value("Account", row.account, "account_name") or row.account
				tax_row.category = "Total"
				tax_row.add_deduct_tax = "Add"

		# Trigger standard ERPNext calculation
		# Clear taxes_and_charges so set_missing_values does not auto-apply a
		# supplier default template (which would add 0-rate rows and fail validation)
		# Save expense_account per item index — set_missing_values() resets it
		# to the item master default, overriding our Accounting Entry accounts.
		_saved_expense_accounts = [r.expense_account for r in pi.items]
		# Set the Purchase Taxes and Charges Template from the Accounting Entry's tax
		# category (required by KSA/ZATCA compliance and for tax table population).
		_first_tax_category = None
		for r in self.accounts:
			if r.tax_category and not _is_tax_row(r):
				_first_tax_category = r.tax_category
				break
		if _first_tax_category:
			pi.taxes_and_charges = _first_tax_category
		pi.run_method("set_missing_values")
		if self.credit_to:
			pi.credit_to = self.credit_to
		pi.run_method("calculate_taxes_and_totals")
		if self.is_paid:
			pi.paid_amount = flt(pi.rounded_total or pi.grand_total)
			pi.base_paid_amount = flt(pi.base_rounded_total or pi.base_grand_total)
		# Restore expense accounts overridden by set_missing_values
		for _idx, _item in enumerate(pi.items):
			if _idx < len(_saved_expense_accounts) and _saved_expense_accounts[_idx]:
				_item.expense_account = _saved_expense_accounts[_idx]

		return pi

	def make_sales_invoice(self):
		"""Generates a standard ERPNext Sales Invoice marked as Paid from this Accounting Entry."""
		settings = get_accounting_entry_settings()

		# 1. Resolve Customer
		customer = self.party or settings.get("default_customer")
		if not customer:
			frappe.throw(
				_("Customer is required. Please specify a Customer in the Accounting Entry or set Default Customer in Accounting Entry Settings.")
			)

		# 2. Resolve Default Sales Item
		default_item = settings.get("default_sales_item")
		if not default_item:
			default_item = frappe.db.get_value("Item", {"is_sales_item": 1, "disabled": 0}, "name")
		if not default_item:
			frappe.throw(
				_("Default Sales Item is required. Please configure Default Sales Item in Accounting Entry Settings.")
			)

		# 3. Mode of Payment for the header Cash/Bank Account (only when Is Paid)
		mode_of_payment = self.get_mode_of_payment()
		if self.is_paid and not mode_of_payment:
			frappe.throw(
				_("No enabled Mode of Payment found for Cash/Bank Account {0}.").format(
					frappe.bold(self.cash_bank_account)
				)
			)

		# 3b. Batch-fetch account_type for every distinct account on this entry,
		# so we can detect tax rows even when is_auto_tax_row wasn't set upstream.
		account_names = list({row.account for row in self.accounts if row.account})
		account_type_map = {
			d["name"]: d["account_type"]
			for d in frappe.get_all(
				"Account",
				filters={"name": ["in", account_names]},
				fields=["name", "account_type"],
			)
		}

		def _is_tax_row(row):
			return bool(row.is_auto_tax_row) or account_type_map.get(row.account) == "Tax"

		# Resolve a project to propagate to the invoice header (needed for accounts with mandatory project)
		invoice_project = self.get_invoice_project("credit")

		# 4. Instantiate Sales Invoice Doc
		si = frappe.new_doc("Sales Invoice")
		si.company = self.company
		si.customer = customer
		if self.debit_to:
			si.debit_to = self.debit_to
		si.posting_date = self.posting_date
		si.due_date = self.posting_date
		si.currency = self.company_currency
		si.remarks = self.user_remark or _("Generated from Accounting Entry {0}").format(self.name)
		if invoice_project:
			si.project = invoice_project

		# Propagate all accounting dimensions to the SI header so ERPNext
		# stamps them on the auto-created AR GL / Payment Ledger Entry.
		self._propagate_accounting_dimensions(si)

		# Payment Details (Standard ERPNext is_pos flow with payments table).
		# The payments row is built after totals are calculated below.
		# Unpaid entries stay outstanding on the customer.
		if self.is_paid:
			si.is_pos = 1

		# 5. Populate Items: Each separate non-tax credit row -> separate item row with its income_account
		for row in self.accounts:
			if _is_tax_row(row):
				continue
			if flt(row.credit) <= 0:
				continue

			item_row = si.append("items", {})
			item_row.item_code = default_item
			item_row.qty = 1.0
			item_row.rate = flt(row.credit)
			item_row.amount = flt(row.credit)
			item_row.income_account = row.account
			if row.project:
				item_row.project = row.project
			if row.department:
				item_row.department = row.department
			# Propagate per-row accounting dimensions (task, employee, etc.)
			for _dim_field in ["task", "employee", "region_location", "asset"]:
				_val = row.get(_dim_field) or self.get(_dim_field)
				if _val:
					try:
						item_row.set(_dim_field, _val)
					except Exception:
						pass

		# 6. Populate Taxes: from Auto Tax rows OR rows on a Tax-type account
		for row in self.accounts:
			if _is_tax_row(row) and flt(row.credit) > 0:
				tax_row = si.append("taxes", {})
				tax_row.charge_type = "Actual"
				tax_row.account_head = row.account
				tax_row.tax_amount = flt(row.credit)
				tax_row.description = frappe.db.get_value("Account", row.account, "account_name") or row.account
				tax_row.category = "Total"
				tax_row.add_deduct_tax = "Add"

		# Trigger standard ERPNext calculation
		# Clear taxes_and_charges so set_missing_values does not auto-apply a
		# customer default template (which would add 0-rate rows and fail validation)
		# Save income_account per item index — set_missing_values() resets it
		# to the item master default, overriding our Accounting Entry accounts.
		_saved_income_accounts = [r.income_account for r in si.items]
		# Set the Sales Taxes and Charges Template from the Accounting Entry's tax
		# category (required by KSA/ZATCA compliance). Without this ZATCA rejects
		# the invoice with: "Please Include Sales Taxes and Charges Template on invoice"
		_first_tax_category = None
		for r in self.accounts:
			if r.tax_category and not _is_tax_row(r):
				_first_tax_category = r.tax_category
				break
		if _first_tax_category:
			si.taxes_and_charges = _first_tax_category
		si.run_method("set_missing_values")
		if self.debit_to:
			si.debit_to = self.debit_to
		si.run_method("calculate_taxes_and_totals")
		# Restore income accounts overridden by set_missing_values
		for _idx, _item in enumerate(si.items):
			if _idx < len(_saved_income_accounts) and _saved_income_accounts[_idx]:
				_item.income_account = _saved_income_accounts[_idx]

		if not self.is_paid:
			return si

		# Build the payments table after set_missing_values and
		# calculate_taxes_and_totals, because set_missing_values (via set_pos_data)
		# rebuilds the payments child table using the Mode of Payment's *default*
		# account for this company, not our Cash/Bank Account. Clearing and
		# appending the single correct row guarantees the right bank account is used.
		paid_amount = flt(si.rounded_total or si.grand_total)
		base_paid_amount = flt(si.base_rounded_total or si.base_grand_total)
		si.set("payments", [])
		payment_row = si.append("payments", {})
		payment_row.mode_of_payment = mode_of_payment
		payment_row.amount = paid_amount
		payment_row.base_amount = base_paid_amount
		payment_row.account = self.cash_bank_account
		si.paid_amount = paid_amount
		si.base_paid_amount = base_paid_amount

		# Carry the correct account on the doc so create_and_submit_invoice can
		# patch it after insert() (before_save wipes it via set_account_for_mode_of_payment).
		si._correct_payment_account = self.cash_bank_account
		return si

	@frappe.whitelist()
	def create_and_submit_invoice(self):
		"""Generates, saves, submits the standard invoice on submit and links it to Accounting Entry."""
		self.check_permission("write")
		if self.tax_type == "Inward":
			frappe.has_permission("Purchase Invoice", "create", throw=True)
			frappe.has_permission("Purchase Invoice", "submit", throw=True)
			if self.purchase_invoice:
				return {"doctype": "Purchase Invoice", "name": self.purchase_invoice}
			invoice = self.make_purchase_invoice()
			invoice.insert(ignore_permissions=True)
			invoice.submit()
			self._backfill_actual_tax_rate(invoice)
			frappe.db.set_value("Accounting Entry", self.name, "purchase_invoice", invoice.name)
			self.purchase_invoice = invoice.name
			frappe.msgprint(
				_("Purchase Invoice {0} created and submitted.").format(
					f'<a href="/app/purchase-invoice/{invoice.name}">{invoice.name}</a>'
				),
				indicator="green",
				alert=True
			)
			return {"doctype": "Purchase Invoice", "name": invoice.name}
		else:
			frappe.has_permission("Sales Invoice", "create", throw=True)
			frappe.has_permission("Sales Invoice", "submit", throw=True)
			if self.sales_invoice:
				return {"doctype": "Sales Invoice", "name": self.sales_invoice}
			invoice = self.make_sales_invoice()
			invoice.insert(ignore_permissions=True)
			# ERPNext's before_save() calls set_account_for_mode_of_payment() during
			# insert(), which overwrites our payment account with the Mode of Payment's
			# default account for the company. Patch the correct account directly in DB
			# BEFORE submit() so GL entries are created against the right bank account.
			correct_payment_account = getattr(invoice, "_correct_payment_account", None)
			if correct_payment_account and invoice.payments:
				payment_child = invoice.payments[0]
				frappe.db.set_value(
					payment_child.doctype,
					payment_child.name,
					"account",
					correct_payment_account,
				)
				payment_child.account = correct_payment_account
			invoice.submit()
			self._backfill_actual_tax_rate(invoice)
			frappe.db.set_value("Accounting Entry", self.name, "sales_invoice", invoice.name)
			self.sales_invoice = invoice.name
			frappe.msgprint(
				_("Sales Invoice {0} created and submitted.").format(
					f'<a href="/app/sales-invoice/{invoice.name}">{invoice.name}</a>'
				),
				indicator="green",
				alert=True
			)
			return {"doctype": "Sales Invoice", "name": invoice.name}


	def _backfill_actual_tax_rate(self, invoice):
		"""Cosmetic-only fix: charge_type='Actual' tax rows don't derive `rate`
		from anything, so ERPNext leaves it at 0. Must run AFTER insert()/submit(),
		via direct db.set_value, because ERPNext's own calculate_taxes_and_totals()
		(triggered during insert()) would otherwise overwrite any rate we set
		in-memory before that point. Does not touch tax_amount or GL entries —
		purely updates the displayed percentage.
		"""
		net_total = flt(invoice.net_total)
		if not net_total:
			return
		for t in invoice.get("taxes") or []:
			if t.charge_type == "Actual" and flt(t.tax_amount) > 0:
				rate = flt(flt(t.tax_amount) / net_total * 100, 2)
				frappe.db.set_value(t.doctype, t.name, "rate", rate)

@frappe.whitelist()
def make_invoice(docname):
	"""Returns the mapped Purchase Invoice or Sales Invoice doc as dict for client-side routing/preview."""
	frappe.has_permission("Accounting Entry", "read", doc=docname, throw=True)
	doc = frappe.get_doc("Accounting Entry", docname)
	doc.check_permission("read")
	if doc.tax_type == "Inward":
		frappe.has_permission("Purchase Invoice", "create", throw=True)
		invoice = doc.make_purchase_invoice()
	else:
		frappe.has_permission("Sales Invoice", "create", throw=True)
		invoice = doc.make_sales_invoice()
	return invoice.as_dict()
