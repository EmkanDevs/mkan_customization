"""Fill project and po_date_gap_days on existing logs from their linked POs.

Writes only these two columns. The comparison is not re-run.
"""
import frappe

from mkan_customization.mkan_customization.doctype.po_amendment_log import po_context


def execute():
	frappe.reload_doc("mkan_customization", "doctype", "po_amendment_log")
	logs = frappe.get_all("PO Amendment Log", fields=["name", "cancelled_po_number", "new_po_number"])
	for log in logs:
		frappe.db.set_value("PO Amendment Log", log.name, {
			"project": po_context.project_of(log.cancelled_po_number),
			"po_date_gap_days": po_context.date_gap(log.cancelled_po_number, log.new_po_number),
		}, update_modified=False)
