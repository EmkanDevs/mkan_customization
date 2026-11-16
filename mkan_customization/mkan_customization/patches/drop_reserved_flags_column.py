import frappe


def execute():
	"""`flags` is a reserved Frappe Document attribute, so the old column never held real text.
	Drop it; the migrate that follows adds `comparison_flags`. Re-run 'Fetch Comparison' on Draft logs."""
	dt = "PO Amendment Item Comparison"
	if frappe.db.table_exists(dt) and frappe.db.has_column(dt, "flags"):
		frappe.db.sql_ddl("alter table `tabPO Amendment Item Comparison` drop column `flags`")
