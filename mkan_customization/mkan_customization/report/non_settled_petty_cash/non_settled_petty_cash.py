# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe


def execute(filters):
    columns = [
        {"label": "Workflow Status", "fieldname": "workflow_status", "fieldtype": "Data", "width": 120},
        {"label": "Expense Claim Amount", "fieldname": "expense_claim_amount", "fieldtype": "Currency", "width": 180},
        {"label": "Purchase Receipt Amount", "fieldname": "purchase_receipt_amount", "fieldtype": "Currency", "width": 180},
        {"label": "Total Taxes and Charges", "fieldname": "total_taxes_charges", "fieldtype": "Currency", "width": 180},
        {"label": "TOTAL Un-Settled Amount", "fieldname": "unsettled_amount", "fieldtype": "Currency", "width": 200},
    ]
    data = get_grouped_data(filters)
    summary = get_summary(filters)
    return columns, data, None, None, summary

def save_data(status, filters, data, filters_purchase_receipt):
    filters["docstatus"] = status
    expense_claim = frappe.db.get_values("Expense Claim", filters=filters, fieldname=["grand_total"], as_dict=True)
    if filters_purchase_receipt:
        filters_purchase_receipt["docstatus"] = status
        print(filters_purchase_receipt)
        purchase_receipt = frappe.db.get_values("Purchase Receipt", filters=filters_purchase_receipt, fieldname=["grand_total"], as_dict=True)
    else:
        purchase_receipt = frappe.db.get_values("Purchase Receipt", filters=filters, fieldname=["grand_total"], as_dict=True)
    data[status][1] = expense_claim[0].get("grand_total", 0) if expense_claim else 0
    data[status][2] = purchase_receipt[0].get("grand_total", 0) if purchase_receipt else 0
    return data

def get_data(data, filters, filters_purchase_receipt):
    for status in [0, 1, 2]:
        filters["docstatus"] = status
        if status == 0:
            data = save_data(status, filters, data, filters_purchase_receipt)
        elif status == 1:
            data = save_data(status, filters, data, filters_purchase_receipt)
        elif status == 2:
            data = save_data(status, filters, data, filters_purchase_receipt)
    data[0][4] = data[0][1] + data[0][2]
    data[1][4] = data[1][1] + data[1][2] 
    return data
    
def get_grouped_data(filters):
    data = [
        ["Draft", 0, 0, 0, 0],
        ["Approved", 0, 0, 0, 0],
        ["Cancelled", 0, 0, 0, 0]
    ]
    if filters.get("department") and filters.get("employee"):
        department = filters.get("department")
        petty_cash_requests = frappe.db.get_values("Petty Cash Request", filters=filters, fieldname=["employee_id"], as_dict=True)
        filters.pop("department")
        filters_purchase_receipt = filters.copy()
        filters_purchase_receipt.pop("employee")
        filters_purchase_receipt["custom_petty_cash_holder"] = filters["employee"]
        data = get_data(data, filters, filters_purchase_receipt)
    if filters.get("department"):
        department = filters.get("department")
        filters.pop("department")
        petty_cash_requests = frappe.db.get_values("Petty Cash Request", filters={"department": department}, fieldname=["employee_id"], as_dict=True)
        for employee in petty_cash_requests:
            print(employee)
            filters_purchase_receipt = filters.copy()
            filters_purchase_receipt["custom_petty_cash_holder"] = employee["employee_id"]
            data = get_data(data, filters, filters_purchase_receipt)      
    if filters.get("employee"):
        filters_purchase_receipt = filters.copy()
        filters_purchase_receipt.pop("employee")
        filters_purchase_receipt["custom_petty_cash_holder"] = filters["employee"]
        data = get_data(data, filters, filters_purchase_receipt)

    else:
        data = get_data(data, filters, None) 
    return data

def get_summary(filters):
    # Get all requests for the project
    conditions = ""
    if filters.get("project"):
        conditions += " AND project = %(project)s"
    requests = frappe.db.sql(f"""
        SELECT received_amount
        FROM `tabPetty Cash Request`
        WHERE docstatus = 1 {conditions}
    """, filters, as_dict=True)
    total_received = sum(r["received_amount"] or 0 for r in requests)
    project_name = frappe.db.get_value("Project",filters.get("project"),"project_name")
    return [
        {
            "label": "TOTAL Received Amount",
            "value": total_received,
            "indicator": "Green",
            "datatype":"Currency"
        },
        {
            "label": "Project Name",
            "value": project_name,
            "indicator": "Red",
            "datatype":"Data",
        }
    ]
