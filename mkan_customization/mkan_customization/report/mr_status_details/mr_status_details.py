# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe

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
        {"label": "Material Request", "fieldname": "material_request", "fieldtype": "Link", "options": "Material Request", "width": 250},
        {"label": "Created By", "fieldname": "owner", "fieldtype": "Data", "width": 150},
        {"label": "Workflow State", "fieldname": "workflow_state", "fieldtype": "Data", "width": 150},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "Transaction Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 150},
        {"label": "Purpose", "fieldname": "material_request_type", "fieldtype": "Select", "width": 150},
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 150},
        {"label": "Quantity", "fieldname": "qty", "fieldtype": "Float", "width": 100},
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 150},
        {"label": "Schedule Date", "fieldname": "schedule_date", "fieldtype": "Date", "width": 120},
        {"label": "Indent", "fieldname": "indent", "fieldtype": "Int", "width": 50,"hidden":1},
        {"label": "Purchase Order", "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 250},
        {"label": "Request for Quotation", "fieldname": "request_for_quotation", "fieldtype": "Link", "options": "Request for Quotation", "width": 250},
        {"label": "Supplier Quotation", "fieldname": "supplier_quotation", "fieldtype": "Link", "options": "Supplier Quotation", "width": 250},
    ]

def get_data(filters): 
    conditions = []
    values = {}
    if filters.get("id"):
        if isinstance(filters["id"], list):
            conditions.append("name IN %(ids)s")
            values["ids"] = tuple(filters["id"])
        else:
            conditions.append("name = %(id)s")
            values["id"] = filters["id"]

    if filters.get("project"):
        if isinstance(filters["project"], list):
            values["projects"] = tuple(filters["project"])
        else:
            values["project"] = filters["project"]
                
    if filters.get("from_date") and filters.get("to_date"):
        values["schedule_date"] = ["between", [filters["from_date"], filters["to_date"]]]

    parent_rows = frappe.db.get_values(
        "Material Request",
        filters=values,
        fieldname=[
            "name",
            "owner",
            "workflow_state",
            "status",
            "transaction_date",
            "material_request_type",
            "docstatus"
        ],
        as_dict=True
    )
    null_values = {
        "item_code": None,
        "item_name": None,
        "qty": None,
        "project": None,
        "schedule_date": None,
        "parent_material_request": None,
        "indent": 0
    }
    new_list = []
    for parent in parent_rows:
        parent.update(null_values)
        purchase_rows = frappe.db.get_values(
            "Purchase Order Item",
            filters={"material_request": parent["name"]},   
            fieldname=[
                "parent",
                "cost_center",
                "amount"
            ],
        )
        if not purchase_rows:
            parent["purchase_order"] = None
            parent["date"] = parent["schedule_date"]
            parent["cost_center"] = None
            parent["grant_total"] = 0
        else:
            for i in purchase_rows:
                parent["purchase_order"] = i[0]
                parent["date"] = parent["schedule_date"]
                parent["cost_center"] = i[1]
                parent["grant_total"] = i[2]
                print(parent)
        supplier_quotation = frappe.db.get_values(
            "Supplier Quotation Item",
            filters={"material_request": parent["name"]},   
            fieldname=["parent"],
        )
        if not supplier_quotation:
            parent["supplier_quotation"] = None
        else:
            for i in supplier_quotation:
                parent["supplier_quotation"] = i[0]
        rfq = frappe.db.get_values(
            "Request for Quotation Item",
            filters={"material_request": parent["name"]},   
            fieldname=["parent"],
        )
        if not rfq:
            parent["request_for_quotation"] = None
        else:
            for i in rfq:
                parent["request_for_quotation"] = i[0]
        new_list.append(parent)
  
    data = []
    for parent in new_list:
        # Fetch Material Request Items (Child Rows)
        child_conditions = "mri.parent = %s"
        child_values = [parent["name"]]

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
                NULL AS material_request,  
                NULL AS Owner,
                NULL AS workflow_state,
                NULL AS status,
                Null AS transaction_date,
                Null AS material_request_type,
                mri.item_code,
                mri.item_name,
                mri.qty,
                IFNULL(CAST(mri.project AS CHAR), '') AS project,
                mri.schedule_date,
                %s AS parent_material_request,
                1 AS indent  
            FROM `tabMaterial Request Item` AS mri
            WHERE {child_conditions}
        """
        print(child_conditions)
        child_values.insert(0, parent["name"])
        print(child_values)
        child_rows = frappe.db.sql(child_query, child_values, as_dict=True)
        
        # Only add parent and children if there are child rows
        if child_rows:
            data.append(parent)
            data.extend(child_rows)

    return data