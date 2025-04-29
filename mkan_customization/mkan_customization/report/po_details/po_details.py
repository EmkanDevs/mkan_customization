# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import formatdate

def execute(filters=None):
    """Main function to generate the tree report"""
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data

def get_columns():
    """Define the report columns"""

    return [
        {"label": "Purchase Order", "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 250},
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
        {"label": "Schedule Date", "fieldname": "schedule_date", "fieldtype": "Date", "width": 120},
        {"label": "Indent", "fieldname": "indent", "fieldtype": "Int", "width": 50,"hidden":1},
        {"label": "Purchase Receipt", "fieldname": "purchase_receipt", "fieldtype": "Link", "options": "Purchase Receipt", "width": 250},
        {"label": "Payment Request", "fieldname": "payment_request", "fieldtype": "Link", "options": "Payment Request", "width": 250},
        {"label": "Supplier Quotation", "fieldname": "supplier_quotation", "fieldtype": "Link", "options": "Supplier Quotation", "width": 250},
        {"label": "Material Request", "fieldname": "material_request", "fieldtype": "Link", "options": "Material Request", "width": 250},
        {"label": "Payment Entry", "fieldname": "payment_entry", "fieldtype": "Link", "options": "Payment Entry", "width": 250},
        {"label": "Purchase Invoice", "fieldname": "purchase_invoice", "fieldtype": "Link", "options": "Purchase Invoice", "width": 250},
       
        

    ]

def get_data(filters):
    """Fetches and organizes the report data in a tree format"""
    conditions = []
    values = {}

    if filters.get("id"):
        if isinstance(filters["id"], list):
            conditions.append("name IN %(ids)s")
            values["ids"] = tuple(filters["id"])
        else:
            conditions.append("name = %(id)s")
            values["id"] = filters["id"]

    # Handle project filtering
    if filters.get("project"):
        # Modify the query to ensure proper project filtering
        project_conditions = []
        if isinstance(filters["project"], list):
            project_conditions.append("EXISTS (SELECT 1 FROM `tabPurchase Order Item` mri WHERE mri.parent = mr.name AND mri.project IN %(projects)s)")
            values["projects"] = tuple(filters["project"])
        else:
            project_conditions.append("EXISTS (SELECT 1 FROM `tabPurchase Order Item` mri WHERE mri.parent = mr.name AND mri.project = %(project)s)")
            values["project"] = filters["project"]
        
        conditions.extend(project_conditions)

    condition_str = " AND ".join(conditions) if conditions else "1=1"

    parent_query = f"""
        SELECT 
            mr.name AS purchase_order,
            (select DATE_FORMAT(modification_time ,'%%d-%%m-%%Y %%H:%%i:%%s') from `tabState Change Items` sc
            where sc.parent = mr.name 
            and sc.docstatus = 1 and workflow_state = 'Approved') AS approval_date,
            mr.owner,
            # DATE_FORMAT(creation, '%%d-%%m-%%Y %%r') AS creation_date,
            DATE_FORMAT(creation, '%%d-%%m-%%Y %%H:%%i:%%s') AS creation_date,
            mr.workflow_state,
            mr.status,
            mr.transaction_date,
            (SELECT GROUP_CONCAT(DISTINCT pri.parent SEPARATOR ', ')
             FROM `tabPurchase Receipt Item` pri
             JOIN `tabPurchase Order Item` poi ON pri.purchase_order_item = poi.name
             WHERE poi.parent = mr.name) AS purchase_receipt,
             (select GROUP_CONCAT(DISTINCT PR.name SEPARATOR ', ')
          from `tabPayment Request` PR inner join `tabPurchase Order` PO on PO.name = PR.reference_name where mr.name = PR.reference_name) as payment_request,
          (select GROUP_CONCAT(DISTINCT PRI.supplier_quotation SEPARATOR ', ') 
            from `tabPurchase Order Item` PRI where PRI.parent = mr.name) as supplier_quotation,
            (select GROUP_CONCAT(DISTINCT PRI.material_request SEPARATOR ', ') 
            from `tabPurchase Order Item` PRI where PRI.parent = mr.name) as material_request,
            (select GROUP_CONCAT(DISTINCT PER.parent SEPARATOR ', ') 
            from `tabPayment Entry Reference` PER 
            where PER.reference_name = mr.name) as payment_entry,
             (select GROUP_CONCAT(DISTINCT PII.parent SEPARATOR ', ') 
             from `tabPurchase Invoice Item` PII where PII.purchase_order = mr.name) as purchase_invoice,
            NULL AS item_code,
            NULL AS item_name,
            NULL AS qty,
            NULL AS project,
            NULL AS schedule_date,
            0 AS indent  
        FROM `tabPurchase Order` mr
        WHERE {condition_str}
        ORDER BY mr.creation DESC
    """
    
    parent_rows = frappe.db.sql(parent_query, values, as_dict=True)
    
    data = []
    for parent in parent_rows:
        # Fetch Purchase Order Items (Child Rows)
        child_conditions = "mri.parent = %s"
        child_values = [parent["purchase_order"]]

        # Additional project filtering for child rows
        if filters.get("project"):
            if isinstance(filters["project"], list):
                child_conditions += " AND (mri.project IN %s OR mri.project IS NULL)"
                child_values.append(tuple(filters["project"]))
            else:
                child_conditions += " AND (mri.project = %s OR mri.project IS NULL)"
                child_values.append(filters["project"])

        child_query = f"""
            SELECT 
                NULL AS purchase_order,  
				NULL AS owner,
                NULL AS creation,
                NULL AS workflow_state,
                NULL AS status,
                Null AS transaction_date,
                mri.item_code,
                mri.item_name,
                mri.qty,
                IFNULL(CAST(mri.project AS CHAR), '') AS project,
                mri.schedule_date,
                %s AS parent_purchase_order,
                1 AS indent  
            FROM `tabPurchase Order Item` AS mri
            WHERE {child_conditions}
        """
        
        child_values.insert(0, parent["purchase_order"])
        child_rows = frappe.db.sql(child_query, child_values, as_dict=True)
        
        # Only add parent and children if there are child rows
        if child_rows:
            data.append(parent)
            data.extend(child_rows)

    return data