import frappe
from frappe.utils import flt, money_in_words

def on_update(self, method=None):
	if self.references:
		for reference in self.references:
			if reference.reference_doctype == "Purchase Order":
				self.db_set("custom_ref_name_for_purchase_order", "Purchase Order")


def on_submit(self, method=None):
	update_invoices_current_due(self)


def on_cancel(self, method=None):
	update_invoices_current_due(self)


def update_invoices_current_due(self):
	if not self.get("references"):
		return
	for ref in self.references:
		if ref.reference_doctype == "Sales Invoice" and ref.reference_name:
			si_data = frappe.db.get_value(
				"Sales Invoice",
				ref.reference_name,
				["outstanding_amount", "retention_amount", "currency"],
				as_dict=True,
			)
			if si_data:
				outstanding = flt(si_data.outstanding_amount)
				retention = flt(si_data.retention_amount)
				current_due = max(0.0, round(outstanding - retention, 2))
				currency = si_data.get("currency")
				frappe.db.set_value(
					"Sales Invoice",
					ref.reference_name,
					{
						"custom_outstanding_value_": current_due,
						"custom_outstanding_amount_in_words": money_in_words(current_due, currency),
					},
					update_modified=False,
				)