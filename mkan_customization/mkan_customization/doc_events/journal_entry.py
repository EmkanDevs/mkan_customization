import frappe
from frappe import _
from mkan_customization.mkan_customization.override.journal_entry import get_required_party_type


def before_validate(doc, method=None):
	for row in doc.get("accounts") or []:
		required_type = get_required_party_type(row.account)
		if required_type and not row.party_type:
			row.party_type = required_type


def validate(doc, method=None):
	for d in doc.get("accounts") or []:
		required_type = get_required_party_type(d.account)
		if not required_type:
			continue
		if d.party_type != required_type:
			frappe.throw(
				_("Row {0}: Party Type must be '{1}' for account {2}").format(
					d.idx, required_type, d.account
				)
			)
		if not d.party:
			frappe.throw(
				_("Row {0}: Party Type and Party are mandatory for account {1}").format(d.idx, d.account)
			)
