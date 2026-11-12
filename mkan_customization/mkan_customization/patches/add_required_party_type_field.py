import frappe

FLAG = "custom_party_required_employee"
TYPE = "custom_required_party_type"


def execute():
	frappe.db.set_value("Custom Field", f"Account-{FLAG}", {
		"label": "Require Party in Journal Entry",
		"description": "If checked, Journal Entry rows using this account must have a Party of the Required Party Type.",
	})
	if not frappe.db.exists("Custom Field", f"Account-{TYPE}"):
		frappe.get_doc({
			"doctype": "Custom Field",
			"dt": "Account",
			"module": "Mkan Customization",
			"fieldname": TYPE,
			"label": "Required Party Type",
			"fieldtype": "Link",
			"options": "Party Type",
			"insert_after": FLAG,
			"depends_on": f"eval:doc.{FLAG}",
			"mandatory_depends_on": f"eval:doc.{FLAG}",
		}).insert(ignore_permissions=True)
	# previously flagged accounts were all Employee accounts
	for name in frappe.get_all("Account", filters={FLAG: 1, TYPE: ["is", "not set"]}, pluck="name"):
		frappe.db.set_value("Account", name, TYPE, "Employee", update_modified=False)
	frappe.clear_cache(doctype="Account")
