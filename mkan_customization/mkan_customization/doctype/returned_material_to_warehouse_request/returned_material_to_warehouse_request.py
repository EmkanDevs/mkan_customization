# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe
from frappe import _

class ReturnedMaterialtoWarehouseRequest(Document):
	pass


@frappe.whitelist()
def create_stock_entry_from_rmwr(rmwr_name):
    rmwr_doc = frappe.get_doc("Returned Material to Warehouse Request", rmwr_name)

    if rmwr_doc.docstatus != 1:
        frappe.throw(_("Please submit the Returned Material to Warehouse Request before creating Stock Entry"))

    if not rmwr_doc.returned_item_list:
        frappe.throw(_("No items found in the returned item list"))

    # 🔍 Check existing Stock Entry linked with this RMWR
    existing_se = frappe.db.get_value(
        "Stock Entry",
        {
            "custom_return_material_ref_doc": rmwr_name,
            "docstatus": ["!=", 2]  # Not cancelled
        },
        ["name", "docstatus"],
        as_dict=True
    )

    if existing_se:
        frappe.throw(
            _("Stock Entry <b>{0}</b> is already linked with this request.").format(existing_se.name)
        )

    # ✅ Create new Stock Entry
    stock_entry = frappe.new_doc("Stock Entry")
    stock_entry.stock_entry_type = "Material Receipt"
    stock_entry.custom_return_material_ref_doc = rmwr_doc.name
    stock_entry.to_warehouse = rmwr_doc.default_target_warehouse
    stock_entry.posting_date = rmwr_doc.date or frappe.utils.today()
    stock_entry.company = (
        frappe.defaults.get_user_default("company")
        or frappe.db.get_single_value("Global Defaults", "default_company")
    )

    if rmwr_doc.project:
        stock_entry.project = rmwr_doc.project

    remarks = f"Material Receipt from {rmwr_doc.name}"
    if rmwr_doc.reason_of_return:
        remarks += f" - Reason: {rmwr_doc.reason_of_return}"
    if rmwr_doc.return_condition:
        remarks += f" - Condition: {rmwr_doc.return_condition}"
    stock_entry.remarks = remarks

    for item in rmwr_doc.returned_item_list:
        stock_entry.append("items", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "description": item.description or item.item_name,
            "qty": item.quantity,
            "uom": item.uom,
            "stock_uom": item.uom,
            "t_warehouse": rmwr_doc.default_target_warehouse,
            "project": rmwr_doc.project or "",
        })

    return stock_entry

def get_default_cost_center(company):
    """Get default cost center for the company"""
    cost_center = frappe.db.get_value("Company", company, "cost_center")
    return cost_center or ""