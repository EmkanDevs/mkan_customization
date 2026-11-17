import frappe

FLAG = "custom_party_required_employee"
TYPE = "custom_required_party_type"

# One-time seed from the previously hard-coded list. Afterwards the Account master is
# the only source of truth.
_SEED = (
	"1152001 - Employee Loans - CPC",
	"1152002 - Employees other deduction - CPC",
	"1157101 - Petty Cash (Business Advance) - CPC",
)
_DESC = "If checked, Journal Entry rows using this account must have a Party of the Required Party Type."


def execute():
	if not frappe.db.exists("Custom Field", f"Account-{FLAG}"):
		frappe.get_doc({
			"doctype": "Custom Field", "dt": "Account", "module": "Mkan Customization",
			"fieldname": FLAG, "label": "Require Party in Journal Entry", "fieldtype": "Check",
			"default": "0", "insert_after": "account_type", "description": _DESC,
		}).insert(ignore_permissions=True)
	if not frappe.db.exists("Custom Field", f"Account-{TYPE}"):
		frappe.get_doc({
			"doctype": "Custom Field", "dt": "Account", "module": "Mkan Customization",
			"fieldname": TYPE, "label": "Required Party Type", "fieldtype": "Link",
			"options": "Party Type", "insert_after": FLAG,
			"depends_on": f"eval:doc.{FLAG}", "mandatory_depends_on": f"eval:doc.{FLAG}",
		}).insert(ignore_permissions=True)
	frappe.clear_cache(doctype="Account")
	frappe.db.commit()

	for name in _SEED:
		if frappe.db.exists("Account", name) and not frappe.db.get_value("Account", name, FLAG):
			frappe.db.set_value("Account", name, {FLAG: 1, TYPE: "Employee"}, update_modified=False)
