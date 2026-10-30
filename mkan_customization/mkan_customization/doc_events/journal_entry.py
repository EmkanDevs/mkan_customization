import frappe
from frappe import _
from mkan_customization.mkan_customization.override.journal_entry import is_employee_target_account


def validate(doc, method=None):
	for d in doc.get("accounts") or []:
		if is_employee_target_account(d.account):
			if not d.party_type:
				d.party_type = "Employee"
			elif d.party_type != "Employee":
				frappe.throw(
					_("Row {0}: Party Type must be 'Employee' for account {1}").format(d.idx, d.account)
				)

			if not d.party:
				frappe.throw(
					_("Row {0}: Party Type and Party are mandatory for account {1}").format(
						d.idx, d.account
					)
				)

