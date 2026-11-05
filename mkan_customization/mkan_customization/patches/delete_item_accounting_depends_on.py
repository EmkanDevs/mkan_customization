import frappe


def execute():
	if frappe.db.exists("Property Setter", "Item-accounting-depends_on"):
		frappe.delete_doc("Property Setter", "Item-accounting-depends_on", force=True)
		frappe.clear_cache(doctype="Item")

