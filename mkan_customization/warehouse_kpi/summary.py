"""Document summary for the side panel. Read permission is checked per document."""
import frappe
from frappe import _

# doctype -> (header fields, child table, child fields)
LAYOUT = {
	"Stock Entry": (
		["stock_entry_type", "purpose", "posting_date", "from_warehouse", "to_warehouse", "project", "remarks"],
		"items",
		["item_code", "item_name", "s_warehouse", "t_warehouse", "qty", "uom", "transfer_qty", "stock_uom"],
	),
	"Purchase Receipt": (
		["supplier", "posting_date", "is_return", "set_warehouse"],
		"items",
		["item_code", "item_name", "warehouse", "qty", "uom", "stock_qty", "stock_uom"],
	),
	"Material Request": (
		["material_request_type", "transaction_date", "workflow_state", "set_warehouse", "project"],
		"items",
		["item_code", "item_name", "warehouse", "qty", "uom", "stock_qty", "stock_uom"],
	),
	"Stock Reconciliation": (
		["purpose", "posting_date", "set_warehouse"],
		"items",
		["item_code", "item_name", "warehouse", "qty", "current_qty", "quantity_difference", "amount_difference"],
	),
	"Returned Material to Warehouse Request": (
		["date", "workflow_state", "reason_of_return", "return_condition", "default_target_warehouse", "project"],
		"returned_item_list",
		["item_code", "item_name", "quantity", "uom"],
	),
	"Equipment Log Register": (
		["transaction_type", "custody_no", "custody_holder_name", "receiving_date", "return_date"],
		"equipment_log_item",
		["item_code", "item_name", "fixed_asset", "asset", "quantity", "uom", "location", "condition", "asset_movement"],
	),
}

STATUS = {0: "Draft", 1: "Submitted", 2: "Cancelled"}


def get_summary(doctype, name):
	if doctype not in LAYOUT:
		frappe.throw(_("Document type {0} is not supported.").format(doctype))
	if not frappe.has_permission(doctype, "read", name):
		frappe.throw(_("You do not have permission to read this document."), frappe.PermissionError)

	header_fields, table, child_fields = LAYOUT[doctype]
	doc = frappe.get_doc(doctype, name)
	return {
		"doctype": doctype,
		"name": name,
		"status": STATUS.get(doc.docstatus),
		"owner": frappe.db.get_value("User", doc.owner, "full_name") or doc.owner,
		"fields": _labelled(doc, header_fields),
		"columns": [_label(frappe.get_meta(doc.meta.get_field(table).options), f) for f in child_fields],
		"items": [[_value(row, f) for f in child_fields] for row in doc.get(table)],
	}


def _labelled(doc, fieldnames):
	pairs = [(_label(doc.meta, f), _value(doc, f)) for f in fieldnames]
	return [[label, value] for label, value in pairs if value not in (None, "")]


def _label(meta, fieldname):
	return meta.get_label(fieldname) if meta.has_field(fieldname) else fieldname


def _value(doc, fieldname):
	value = doc.get(fieldname)
	return str(value) if value is not None else ""
