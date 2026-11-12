import frappe

# One-time seed of the flag from the previously hard-coded lists.
# After this patch, the Account master is the only source of truth.
_NUMBERS = ("1157101", "1152002", "1152001", "1152004")
_NAMES = (
	"petty cash (business advance)", "employee loans", "employee loan", "employees loan",
	"employee other deduction", "employee other deductions", "employees other deduction",
	"employees other deductions", "employee loans (e.o.s)", "employee loan (e.o.s)",
	"employees loan ( e.o.s", "employees loan (e.o.s)", "mega employee loan",
)
FIELD = "custom_party_required_employee"


def execute():
	if not frappe.db.exists("Custom Field", f"Account-{FIELD}"):
		frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Account",
			"module": "Mkan Customization",
			"fieldname": FIELD,
			"label": "Require Party in Journal Entry",
			"fieldtype": "Check",
			"default": "0",
			"insert_after": "account_type",
			"description": "If checked, Journal Entry rows using this account must have a Party of the Required Party Type.",
		}).insert(ignore_permissions=True)
		frappe.clear_cache(doctype="Account")

	for acc in frappe.get_all("Account", fields=["name", "account_number", "account_name", FIELD], filters={"is_group": 0}):
		if acc.get(FIELD):
			continue
		lname = (acc.account_name or "").strip().lower()
		if (acc.account_number or "") in _NUMBERS or any(n in lname for n in _NAMES):
			frappe.db.set_value("Account", acc.name, FIELD, 1, update_modified=False)
