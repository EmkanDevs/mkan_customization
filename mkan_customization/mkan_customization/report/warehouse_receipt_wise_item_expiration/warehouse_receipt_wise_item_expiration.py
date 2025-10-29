# Copyright (c) 2025, Your Company
# For license information, please see license.txt

import frappe
from frappe.utils import nowdate, date_diff, getdate

def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 180},
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 150},
        {"label": "Shelf Life In Days", "fieldname": "shelf_life_in_days", "fieldtype": "Int", "width": 130},
        {"label": "Purchase Receipt", "fieldname": "purchase_receipt", "fieldtype": "Link", "options": "Purchase Receipt", "width": 160},
        {"label": "Purchase Receipt Date", "fieldname": "purchase_receipt_date", "fieldtype": "Date", "width": 150},
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"label": "No. Of Item Per Request", "fieldname": "qty", "fieldtype": "Float", "width": 180},
        {"label": "Days Till Expire", "fieldname": "days_till_expire", "fieldtype": "Data", "width": 130},
    ]


def get_data(filters):
    conditions = []
    values = {}

    # Existing filters
    if filters.get("warehouse"):
        conditions.append("pri.warehouse = %(warehouse)s")
        values["warehouse"] = filters["warehouse"]

    if filters.get("item"):
        conditions.append("pri.item_code = %(item)s")
        values["item"] = filters["item"]

    if filters.get("item_group"):
        conditions.append("i.item_group = %(item_group)s")
        values["item_group"] = filters["item_group"]

    # 🆕 Date filters
    if filters.get("from_date"):
        conditions.append("pr.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("pr.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    where_clause = " AND ".join(conditions)
    if where_clause:
        where_clause = "WHERE " + where_clause

    query = f"""
        SELECT
            pri.item_code,
            pri.item_name,
            i.item_group,
            i.shelf_life_in_days,
            pr.name AS purchase_receipt,
            pr.posting_date AS purchase_receipt_date,
            pri.warehouse,
            pri.qty
        FROM
            `tabPurchase Receipt Item` AS pri
        INNER JOIN
            `tabPurchase Receipt` AS pr ON pri.parent = pr.name
        INNER JOIN
            `tabItem` AS i ON pri.item_code = i.name
        {where_clause}
    """

    results = frappe.db.sql(query, values, as_dict=True)
    today = getdate(nowdate())

    for row in results:
        if row.get("shelf_life_in_days"):
            days_since_purchase = date_diff(today, row.get("purchase_receipt_date"))
            days_till_expire = row["shelf_life_in_days"] - days_since_purchase

            if days_till_expire < 0:
                row["days_till_expire"] = "Item Expired"
            else:
                row["days_till_expire"] = days_till_expire
        else:
            row["days_till_expire"] = None

    # Optional filter for days_till_expire
    if filters.get("days_till_expire") is not None:
        results = [
            r for r in results
            if isinstance(r["days_till_expire"], int) and r["days_till_expire"] <= filters["days_till_expire"]
        ]

    return results
