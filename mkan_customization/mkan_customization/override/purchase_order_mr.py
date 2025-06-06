import frappe
from frappe.model.mapper import get_mapped_doc
import json
from erpnext.stock.doctype.item.item import get_item_defaults
from frappe.utils import cint, cstr, flt, get_link_to_form, getdate, new_line_sep, nowdate


@frappe.whitelist()
def make_purchase_order(source_name, target_doc=None, args=None):
	if args is None:
		args = {}
	if isinstance(args, str):
		args = json.loads(args)

	valid_items_found = []

	def postprocess(source, target_doc):
		if frappe.flags.args and frappe.flags.args.default_supplier:
			# items only for given default supplier
			supplier_items = []
			for d in target_doc.items:
				default_supplier = get_item_defaults(d.item_code, target_doc.company).get("default_supplier")
				if frappe.flags.args.default_supplier == default_supplier:
					supplier_items.append(d)
			target_doc.items = supplier_items

		set_missing_values(source, target_doc)

	def select_item(d):
		filtered_items = args.get("filtered_children", [])
		child_filter = d.name in filtered_items if filtered_items else True

		# Step 1: Get related RFQ Items
		rfq_items = frappe.get_all(
			"Request for Quotation Item",
			filters={"material_request_item": d.name},
			fields=["parent"]
		)

		if not rfq_items:
			return False  # No RFQ found

		# Step 2: Check if Bid Tabulation Discussion exists for any of the RFQs
		rfq_names = list(set([item.parent for item in rfq_items]))

		has_bid_tab = frappe.get_all(
			"Bid Tabulation Discussion",
			filters={"request_for_quotation": ["in", rfq_names]},
			limit=1
		)

		qty = d.ordered_qty or d.received_qty

		is_valid = qty < d.stock_qty and child_filter and bool(has_bid_tab)
		if is_valid:
			valid_items_found.append(d.name)
		return is_valid

	doclist = get_mapped_doc(
		"Material Request",
		source_name,
		{
			"Material Request": {
				"doctype": "Purchase Order",
				"validation": {"docstatus": ["=", 1], "material_request_type": ["=", "Purchase"]},
			},
			"Material Request Item": {
				"doctype": "Purchase Order Item",
				"field_map": [
					["name", "material_request_item"],
					["parent", "material_request"],
					["uom", "stock_uom"],
					["uom", "uom"],
					["sales_order", "sales_order"],
					["sales_order_item", "sales_order_item"],
					["wip_composite_asset", "wip_composite_asset"],
				],
				"postprocess": update_item,
				"condition": select_item,
			},
		},
		target_doc,
		postprocess,
	)

	if not valid_items_found:
		frappe.throw("Cannot create Purchase Order: No linked Request for Quotation or Bid Tabulation Discussion found for any items.")

	doclist.set_onload("load_after_mapping", False)
	return doclist


def update_item(obj, target, source_parent):
	target.conversion_factor = obj.conversion_factor

	qty = obj.ordered_qty or obj.received_qty
	target.qty = flt(flt(obj.stock_qty) - flt(qty)) / target.conversion_factor
	target.stock_qty = target.qty * target.conversion_factor
	if getdate(target.schedule_date) < getdate(nowdate()):
		target.schedule_date = None
  
def set_missing_values(source, target_doc):
	if target_doc.doctype == "Purchase Order" and getdate(target_doc.schedule_date) < getdate(nowdate()):
		target_doc.schedule_date = None
	target_doc.run_method("set_missing_values")
	target_doc.run_method("calculate_taxes_and_totals")