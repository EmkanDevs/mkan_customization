import frappe
from erpnext.accounts.doctype.journal_entry.journal_entry import (
	get_account_details_and_party_type as orig_get_account_details_and_party_type,
)
import erpnext.accounts.party as party_module
import erpnext.accounts.doctype.gl_entry.gl_entry as gl_entry_module

PARTY_REQUIRED_FLAG = "custom_party_required_employee"  # Account: "Require Party in Journal Entry"
PARTY_TYPE_FIELD = "custom_required_party_type"  # Account: "Required Party Type"


def get_required_party_type(account):
	"""Party Type Journal Entry rows must use for this account, or None when Party is
	optional. Driven entirely by the Account master (no hard-coded lists)."""
	if not account or not isinstance(account, str) or not getattr(frappe, "db", None):
		return None
	try:
		flag, party_type = frappe.get_cached_value(
			"Account", account.strip(), [PARTY_REQUIRED_FLAG, PARTY_TYPE_FIELD]
		) or (0, None)
	except Exception:
		return None
	return (party_type or "Employee") if flag else None


def is_employee_target_account(account):
	"""Kept for backward compatibility: True if Party is required for this account."""
	return bool(get_required_party_type(account))


@frappe.whitelist()
def get_party_required_accounts():
	"""{account: party_type} for every account that requires a Party (used by the form script)."""
	rows = frappe.get_all("Account", filters={PARTY_REQUIRED_FLAG: 1}, fields=["name", PARTY_TYPE_FIELD])
	return {r.name: (r.get(PARTY_TYPE_FIELD) or "Employee") for r in rows}


@frappe.whitelist()
def get_account_details_and_party_type(
	account, date, company, debit=None, credit=None, exchange_rate=None
):
	"""Override of erpnext's get_account_details_and_party_type.
	Sets party_type to the account's Required Party Type when one is configured.
	"""
	res = orig_get_account_details_and_party_type(
		account, date, company, debit=debit, credit=credit, exchange_rate=exchange_rate
	)
	required_type = get_required_party_type(account)
	if required_type:
		if not res:
			res = {}
		res["party_type"] = required_type

	return res


orig_validate_account_party_type = party_module.validate_account_party_type


def custom_validate_account_party_type(self):
	"""Monkey-patched validate_account_party_type: allow the account's Required Party Type
	(e.g. Employee on loan / petty cash accounts) even though it is not Receivable/Payable.
	"""
	if self.is_cancelled:
		return

	if self.party_type and self.party and self.party_type == get_required_party_type(self.account):
		return

	return orig_validate_account_party_type(self)


def apply_monkey_patches():
	party_module.validate_account_party_type = custom_validate_account_party_type
	gl_entry_module.validate_account_party_type = custom_validate_account_party_type
