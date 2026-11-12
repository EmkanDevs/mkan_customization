import frappe
from frappe import _
from mkan_customization.mkan_customization.override.journal_entry import (
	apply_gl_entry_patch,
	validate_required_party,
)

# Ensure patch is active when module loads
apply_gl_entry_patch()


def before_validate(doc, method=None):
	"""Set party_not_required = 1 before validations run so standard ERPNext
	does not require Party on non-employee accounts (e.g. Accounts Receivable / Payable).
	"""
	apply_gl_entry_patch()
	_force_party_not_required(doc)


def _force_party_not_required(doc):
	"""party_not_required is not allow_on_submit, so on submitted docs changing it
	on the doc would raise "Not allowed to change ... after submission".
	Persist it directly in the DB instead, then mirror it on the doc (unchanged vs DB)."""
	if doc.docstatus == 1 and not doc.is_new():
		if not frappe.db.get_value(doc.doctype, doc.name, "party_not_required"):
			frappe.db.set_value(
				doc.doctype, doc.name, "party_not_required", 1, update_modified=False
			)
			if getattr(doc, "_doc_before_save", None):
				doc._doc_before_save.party_not_required = 1
	doc.party_not_required = 1


def validate(doc, method=None):
	"""Server validation hook for Journal Entry.
	- Ensures party_not_required = 1 so ERPNext standard does NOT force Party
	  on non-employee accounts.
	- For every row whose Account has "Require Party in Journal Entry" ticked:
	  * Verifies party_type equals the account's Required Party Type.
	  * Throws an error if party is not filled.
	"""
	apply_gl_entry_patch()
	_force_party_not_required(doc)
	for row in doc.get("accounts", []):
		validate_required_party(row)
