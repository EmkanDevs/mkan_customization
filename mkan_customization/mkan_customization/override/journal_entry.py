import frappe
from frappe import _
from erpnext.accounts.doctype.journal_entry.journal_entry import (
	get_account_details_and_party_type as standard_get_account_details_and_party_type,
)

PARTY_REQUIRED_FLAG = "custom_party_required_employee"  # Account: "Require Party in Journal Entry"
PARTY_TYPE_FIELD = "custom_required_party_type"  # Account: "Required Party Type"


def get_required_party_type(account):
	"""Party Type that Journal Entry rows must use for this account, or None when
	Party is optional. Driven entirely by the Account master (no hard-coded lists)."""
	if not account or not getattr(frappe, "db", None):
		return None
	try:
		flag, party_type = frappe.get_cached_value(
			"Account", str(account).strip(), [PARTY_REQUIRED_FLAG, PARTY_TYPE_FIELD]
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
	rows = frappe.get_all(
		"Account", filters={PARTY_REQUIRED_FLAG: 1}, fields=["name", PARTY_TYPE_FIELD]
	)
	return {r.name: (r.get(PARTY_TYPE_FIELD) or "Employee") for r in rows}


def validate_required_party(row):
	"""Enforce the Account's required Party Type / Party on a Journal Entry row.
	Returns True if the account requires a party."""
	required_type = get_required_party_type(row.account)
	if not required_type:
		return False
	if not row.party_type:
		row.party_type = required_type
	elif row.party_type != required_type:
		frappe.throw(
			_("Row {0}: Party Type must be '{1}' for account {2}").format(
				row.idx, required_type, frappe.bold(row.account)
			),
			title=_("Invalid Party Type"),
		)
	# Employee accounting dimension mirrors the party for Employee rows
	if required_type == "Employee":
		if not row.party and row.get("employee"):
			row.party = row.get("employee")
	if not row.party:
		frappe.throw(
			_("Row {0}: Party is mandatory for account {1}").format(row.idx, frappe.bold(row.account)),
			title=_("Mandatory Field Missing"),
		)
	if required_type == "Employee" and hasattr(row, "employee") and not row.get("employee"):
		row.employee = row.party
	return True


@frappe.whitelist()
def get_account_details_and_party_type(
	account, date, company, debit=None, credit=None, exchange_rate=None
):
	"""Override for get_account_details_and_party_type.
	Returns party_type: 'Employee' when one of the target employee accounts is selected.
	"""
	res = standard_get_account_details_and_party_type(
		account=account,
		date=date,
		company=company,
		debit=debit,
		credit=credit,
		exchange_rate=exchange_rate,
	)
	if res is None:
		res = {}
	required_type = get_required_party_type(account)
	if required_type:
		res["party_type"] = required_type
	return res


_orig_validate_account_party_type = None
_orig_journal_entry_validate_party = None


def patched_validate_account_party_type(self):
	"""Monkey-patch for validate_account_party_type in GL Entry & party module.
	Allows party_type = 'Employee' for the designated employee accounts during submission,
	preventing 'Party Type and Party can only be set for Receivable / Payable account' errors.
	"""
	is_cancelled = getattr(self, "is_cancelled", 0)
	if is_cancelled:
		return
	party_type = getattr(self, "party_type", None) or (self.get("party_type") if isinstance(self, dict) else None)
	account = getattr(self, "account", None) or (self.get("account") if isinstance(self, dict) else None)
	if party_type and party_type == get_required_party_type(account):
		return
	if _orig_validate_account_party_type:
		return _orig_validate_account_party_type(self)


def patched_journal_entry_validate_party(self):
	"""Ensure Party Type and Party are mandatory ONLY for the 4 designated employee accounts.
	For all other accounts (Receivable / Payable / Customer / Supplier), Party is optional
	and saving/submitting is allowed without providing a Party.
	"""
	self.party_not_required = 1
	for d in self.get("accounts", []):
		account_type = frappe.get_cached_value("Account", d.account, "account_type")
		if validate_required_party(d):
			pass
		else:
			# Accounts without a required party: Party is optional.
			# Only check account type mismatch IF both party_type and party are provided.
			if d.party_type and d.party:
				if (
					account_type in ["Receivable", "Payable"]
					and frappe.db.get_value("Party Type", d.party_type, "account_type") != account_type
					and d.party_type != "Employee"
				):
					frappe.throw(
						_("Row {0}: Account {1} and Party Type {2} have different account types").format(
							d.idx, d.account, d.party_type
						)
					)


def apply_gl_entry_patch():
	"""Apply monkey patch to erpnext.accounts.party, gl_entry, and journal_entry."""
	global _orig_validate_account_party_type, _orig_journal_entry_validate_party
	import erpnext.accounts.party
	import erpnext.accounts.doctype.gl_entry.gl_entry
	import erpnext.accounts.doctype.journal_entry.journal_entry as je_module

	if _orig_validate_account_party_type is None:
		_orig_validate_account_party_type = erpnext.accounts.party.validate_account_party_type
	erpnext.accounts.party.validate_account_party_type = patched_validate_account_party_type
	erpnext.accounts.doctype.gl_entry.gl_entry.validate_account_party_type = (
		patched_validate_account_party_type
	)
	je_module.get_account_details_and_party_type = get_account_details_and_party_type
	if hasattr(je_module, "JournalEntry"):
		if _orig_journal_entry_validate_party is None:
			_orig_journal_entry_validate_party = je_module.JournalEntry.validate_party
		je_module.JournalEntry.validate_party = patched_journal_entry_validate_party


# Apply immediately when module is imported
apply_gl_entry_patch()

