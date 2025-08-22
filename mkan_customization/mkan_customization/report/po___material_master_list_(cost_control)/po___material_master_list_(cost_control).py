# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt
import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {"label": "PO No.", "fieldname": "po_no", "fieldtype": "Link", "options": "Purchase Order", "width": 120},
        {"label": "Project Code", "fieldname": "project_code", "fieldtype": "Link", "options": "Project", "width": 120},
        {"label": "Project Name", "fieldname": "project_name", "fieldtype": "Data", "width": 180},
        {"label": "PO Date", "fieldname": "po_date", "fieldtype": "Date", "width": 100},
        {"label": "Supplier Code", "fieldname": "supplier_code", "fieldtype": "Link", "options": "Supplier", "width": 120},
        {"label": "Supplier Name", "fieldname": "supplier_name", "fieldtype": "Data", "width": 180},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
        {"label": "Rate", "fieldname": "rate", "fieldtype": "Currency", "width": 100},
    ]


def get_data(filters):
    conditions = []
    values = {}

    if filters.get("project"):
        conditions.append("po.project = %(project)s")
        values["project"] = filters["project"]

    if filters.get("supplier"):
        conditions.append("po.supplier = %(supplier)s")
        values["supplier"] = filters["supplier"]

    if filters.get("item"):
        conditions.append("poi.item_code = %(item)s")
        values["item"] = filters["item"]

    if filters.get("from_date"):
        conditions.append("po.transaction_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("po.transaction_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    where_clause = " AND ".join(conditions)
    if where_clause:
        where_clause = " AND " + where_clause

    query = f"""
        SELECT
            po.name AS po_no,
            po.project AS project_code,
            proj.project_name AS project_name,
            po.transaction_date AS po_date,
            po.supplier AS supplier_code,
            sup.supplier_name AS supplier_name,
            poi.item_code,
            poi.item_name,
            poi.uom,
            poi.rate
        FROM `tabPurchase Order` po
        JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
        LEFT JOIN `tabProject` proj ON proj.name = po.project
        LEFT JOIN `tabSupplier` sup ON sup.name = po.supplier
        WHERE po.docstatus = 1
        {where_clause}
        ORDER BY po.transaction_date DESC
    """

    return frappe.db.sql(query, values, as_dict=True)
