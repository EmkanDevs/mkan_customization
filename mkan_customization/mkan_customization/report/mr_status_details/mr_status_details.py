# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate


def execute(filters=None):
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns():
    return [
        {"label": "Material Request", "fieldname": "material_request", "fieldtype": "Link", "options": "Material Request", "width": 250},
        {"label": "Created By", "fieldname": "owner", "fieldtype": "Data", "width": 150},
        {"label": "Created On", "fieldname": "creation_date", "fieldtype": "Data", "width": 150},
        {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 150},
        {"label": "Approval Date", "fieldname": "approval_date", "fieldtype": "Data", "width": 150},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "Transaction Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 150},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 150},
        {"label": "Quantity", "fieldname": "qty", "fieldtype": "Float", "width": 100},
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 150},
        {"label": "Project Name", "fieldname": "project_name", "fieldtype": "Data", "width": 200},
        {"label": "Schedule Date", "fieldname": "schedule_date", "fieldtype": "Date", "width": 120},
        {"label": "Indent", "fieldname": "indent", "fieldtype": "Int", "width": 50, "hidden": 1},
        {"label": "Purchase Order", "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 250},
        {"label": "Purchase Receipt", "fieldname": "purchase_receipt", "fieldtype": "Link", "options": "Purchase Receipt", "width": 250},
        {"label": "Payment Request", "fieldname": "payment_request", "fieldtype": "Link", "options": "Payment Request", "width": 250},
        {"label": "Payment Entry", "fieldname": "payment_entry", "fieldtype": "Link", "options": "Payment Entry", "width": 250},
        {"label": "Purchase Invoice", "fieldname": "purchase_invoice", "fieldtype": "Link", "options": "Purchase Invoice", "width": 250},
    ]


def get_data(filters):
    conditions = []
    values = {}

    # Filter by ID
    if filters.get("id"):
        if isinstance(filters["id"], list):
            conditions.append("mr.name IN %(ids)s")
            values["ids"] = tuple(filters["id"])
        else:
            conditions.append("mr.name = %(id)s")
            values["id"] = filters["id"]

    # Filter by Project
    if filters.get("project"):
        if isinstance(filters["project"], list):
            conditions.append(
                """EXISTS (
                    SELECT 1 FROM `tabMaterial Request Item` mri
                    WHERE mri.parent = mr.name AND mri.project IN %(projects)s
                )"""
            )
            values["projects"] = tuple(filters["project"])
        else:
            conditions.append(
                """EXISTS (
                    SELECT 1 FROM `tabMaterial Request Item` mri
                    WHERE mri.parent = mr.name AND mri.project = %(project)s
                )"""
            )
            values["project"] = filters["project"]

    # Filter by Date Range
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append(
            """EXISTS (
                SELECT 1 FROM `tabMaterial Request Item` mri
                WHERE mri.parent = mr.name
                AND mri.schedule_date BETWEEN %(from_date)s AND %(to_date)s
            )"""
        )
        values["from_date"] = filters["from_date"]
        values["to_date"] = filters["to_date"]

    condition_str = " AND ".join(conditions) if conditions else "1=1"

    # Parent (MR) Query
    parent_query = f"""
        SELECT 
            mr.name AS material_request,
            (SELECT DATE_FORMAT(modification_time ,'%%d-%%m-%%Y %%H:%%i:%%s')
             FROM `tabState Change Items` sc
             WHERE sc.parent = mr.name AND sc.docstatus = 1 
             AND workflow_state = 'Approved') AS approval_date,
            mr.owner,
            DATE_FORMAT(mr.creation, '%%d-%%m-%%Y %%H:%%i:%%s') AS creation_date,
            mr.workflow_state,
            mr.status,
            mr.transaction_date,
            (SELECT GROUP_CONCAT(DISTINCT po.parent SEPARATOR ', ')
             FROM `tabPurchase Order Item` po
             WHERE po.material_request = mr.name) AS purchase_order,
            (SELECT GROUP_CONCAT(DISTINCT pr.parent SEPARATOR ', ')
             FROM `tabPurchase Receipt Item` pr
             WHERE pr.material_request = mr.name) AS purchase_receipt,
            (SELECT GROUP_CONCAT(DISTINCT pay.name SEPARATOR ', ')
             FROM `tabPayment Request` pay
             WHERE pay.reference_name = mr.name) AS payment_request,
            (SELECT GROUP_CONCAT(DISTINCT pe.parent SEPARATOR ', ')
             FROM `tabPayment Entry Reference` pe
             WHERE pe.reference_name = mr.name) AS payment_entry,
            (SELECT GROUP_CONCAT(DISTINCT pi.parent SEPARATOR ', ')
             FROM `tabPurchase Invoice Item` pi
             WHERE pi.material_request = mr.name) AS purchase_invoice,
            NULL AS item_code,
            NULL AS item_name,
            NULL AS qty,
            NULL AS project,
            NULL AS project_name,
            NULL AS schedule_date,
            0 AS indent
        FROM `tabMaterial Request` mr
        WHERE {condition_str}
        ORDER BY mr.creation DESC
    """

    parent_rows = frappe.db.sql(parent_query, values, as_dict=True)

    data = []
    for parent in parent_rows:
        # Child Items
        child_conditions = "mri.parent = %s"
        child_values = [parent["material_request"]]

        if filters.get("project"):
            if isinstance(filters["project"], list):
                child_conditions += " AND (mri.project IN %s OR mri.project IS NULL)"
                child_values.append(tuple(filters["project"]))
            else:
                child_conditions += " AND (mri.project = %s OR mri.project IS NULL)"
                child_values.append(filters["project"])

        child_query = f"""
            SELECT 
                NULL AS material_request,
                NULL AS owner,
                NULL AS creation_date,
                NULL AS workflow_state,
                NULL AS approval_date,
                NULL AS status,
                NULL AS transaction_date,
                NULL AS purchase_order,
                NULL AS purchase_receipt,
                NULL AS payment_request,
                NULL AS payment_entry,
                NULL AS purchase_invoice,
                mri.item_code,
                mri.item_name,
                mri.qty,
                mri.project,
                p.project_name,
                mri.schedule_date,
                %s AS parent_material_request,
                1 AS indent
            FROM `tabMaterial Request Item` mri
            LEFT JOIN `tabProject` p ON mri.project = p.name
            WHERE {child_conditions}
        """

        child_values.insert(0, parent["material_request"])
        child_rows = frappe.db.sql(child_query, child_values, as_dict=True)

        if child_rows:
            data.append(parent)
            data.extend(child_rows)

    return data
