# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Stock Entry No", "fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 180},
        {"label": "Stock Entry Type", "fieldname": "stock_entry_type", "fieldtype": "Data", "width": 160},
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 110},
        {"label": "Source Warehouse", "fieldname": "source_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
        {"label": "Target Warehouse", "fieldname": "target_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
        {"label": "Subcontractor Code", "fieldname": "supplier_code", "fieldtype": "Link", "options": "Supplier", "width": 140},
        {"label": "Subcontractor Name", "fieldname": "supplier_name", "fieldtype": "Data", "width": 180},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 140},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 200},
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 150},
        {"label": "Qty", "fieldname": "qty", "fieldtype": "Float", "width": 100},
        {"label": "UOM", "fieldname": "uom", "fieldtype": "Link", "options": "UOM", "width": 80},
        {"label": "Basic Rate (as per Stock UOM)", "fieldname": "basic_rate", "fieldtype": "Currency", "width": 150},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 130},
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 160},
        {"label": "Project Name", "fieldname": "project_name", "fieldtype": "Data", "width": 200},
    ]


def get_data(filters):
    filters = filters or {}

    conditions = ""

    if filters.get("project"):
        conditions += " AND se.project = %(project)s"

    if filters.get("supplier"):
        conditions += " AND se.custom_supplier_code = %(supplier)s"

    if filters.get("from_date"):
        conditions += " AND se.posting_date >= %(from_date)s"

    if filters.get("to_date"):
        conditions += " AND se.posting_date <= %(to_date)s"


    data = frappe.db.sql(f"""
        SELECT
            se.name AS stock_entry,
            se.stock_entry_type,
            se.posting_date,
            sed.s_warehouse AS source_warehouse,
            sed.t_warehouse AS target_warehouse,
            se.custom_supplier_code AS supplier_code,
            se.custom_suppliers_name AS supplier_name,
            sed.item_code,
            sed.item_name,
            i.item_group,
            sed.qty,
            sed.stock_uom AS uom,
            sed.basic_rate,
            sed.amount,
            se.project,
            p.project_name

        FROM `tabStock Entry` se

        LEFT JOIN `tabStock Entry Detail` sed
            ON sed.parent = se.name

        LEFT JOIN `tabItem` i
            ON i.name = sed.item_code

        LEFT JOIN `tabProject` p
            ON p.name = se.project

        WHERE
            se.docstatus = 1
            AND se.stock_entry_type = 'Send to Subcontractor'
            {conditions}

        ORDER BY se.posting_date DESC
    """, filters, as_dict=True)

    return data