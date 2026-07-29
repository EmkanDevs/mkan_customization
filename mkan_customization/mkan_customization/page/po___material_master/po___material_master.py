# Copyright (c) 2025, Finbyz
# For license information, please see license.txt

import frappe

@frappe.whitelist()
def get_data(filters=None):
    if isinstance(filters, str):
        import json
        filters = json.loads(filters)

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
