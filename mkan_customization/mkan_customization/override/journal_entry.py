import frappe
from frappe import _
from erpnext.accounts.doctype.journal_entry.journal_entry import (
	get_account_details_and_party_type as orig_get_account_details_and_party_type,
)
import erpnext.accounts.party as party_module
import erpnext.accounts.doctype.gl_entry.gl_entry as gl_entry_module

EMPLOYEE_TARGET_ACCOUNTS = {
	"1152001 - Employee Loans - CPC",
	"1152002 - Employees other deduction - CPC",
	"1157101 - Petty Cash (Business Advance) - CPC",
}

EMPLOYEE_TARGET_NUMBERS = {"1152001", "1152002", "1157101"}

EMPLOYEE_TARGET_NAMES = {
	"Employee Loans",
	"Employees other deduction",
	"Petty Cash (Business Advance)",
}


def is_employee_target_account(account):
	if not account:
		return False

	account_str = str(account).strip()
	if account_str in EMPLOYEE_TARGET_ACCOUNTS:
		return True

	# Match by account number prefix in name, e.g. "1152001 - ..."
	acc_num = account_str.split(" - ")[0].strip()
	if acc_num in EMPLOYEE_TARGET_NUMBERS:
		return True

	for target_name in EMPLOYEE_TARGET_NAMES:
		if target_name in account_str:
			return True

	# Fallback to Account doctype fields
	acc_details = frappe.get_cached_value(
		"Account", account_str, ["account_number", "account_name"], as_dict=True
	)
	if acc_details:
		if acc_details.account_number in EMPLOYEE_TARGET_NUMBERS:
			return True
		if acc_details.account_name in EMPLOYEE_TARGET_NAMES:
			return True

	return False


@frappe.whitelist()
def get_account_details_and_party_type(
	account, date, company, debit=None, credit=None, exchange_rate=None
):
	"""Override of erpnext.accounts.doctype.journal_entry.journal_entry.get_account_details_and_party_type.
	Automatically sets party_type to 'Employee' for the target accounts.
	"""
	res = orig_get_account_details_and_party_type(
		account, date, company, debit=debit, credit=credit, exchange_rate=exchange_rate
	)
	if is_employee_target_account(account):
		if not res:
			res = {}
		res["party_type"] = "Employee"

	return res


orig_validate_account_party_type = party_module.validate_account_party_type


def custom_validate_account_party_type(self):
	"""Monkey-patched validate_account_party_type to allow Employee party
	on employee accounts (e.g. loans, deductions, petty cash/custody).
	"""
	if self.is_cancelled:
		return

	if self.party_type and self.party:
		if self.party_type == "Employee" or is_employee_target_account(self.account):
			return

	return orig_validate_account_party_type(self)


def apply_monkey_patches():
	party_module.validate_account_party_type = custom_validate_account_party_type
	gl_entry_module.validate_account_party_type = custom_validate_account_party_type

