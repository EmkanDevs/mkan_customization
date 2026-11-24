"""Copy workflow_state into workflow_status on existing PO Amendment Logs.

Logs with no workflow_state keep their old workflow_status. Writes only that one column.
"""
import frappe


def execute():
	frappe.reload_doc("mkan_customization", "doctype", "po_amendment_log")
	frappe.db.sql(
		"""update `tabPO Amendment Log` set workflow_status = workflow_state
		where ifnull(workflow_state, '') != '' and ifnull(workflow_status, '') != workflow_state"""
	)
