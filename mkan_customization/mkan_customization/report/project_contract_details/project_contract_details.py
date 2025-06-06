# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    project = filters.get("project")
    project_sub_contract = filters.get("project_sub_contract")

    columns = get_columns()
    data = get_data(project, project_sub_contract)

    return columns, data

def get_columns():
    return [
        {"label": "Name", "fieldname": "name", "fieldtype": "Link", "options": "Project Sub-Contracts", "width": 250},
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 150},
        {"label": "Party Type", "fieldname": "party_type", "fieldtype": "Data", "width": 100},
        {"label": "Party Name", "fieldname": "party_name", "fieldtype": "Data", "width": 220},
        {"label": "Start Date", "fieldname": "start_date", "fieldtype": "Date", "width": 120},
        {"label": "End Date", "fieldname": "end_date", "fieldtype": "Date", "width": 120},
        {"label": "Project Number", "fieldname": "project_number", "fieldtype": "Data", "width": 150},
        {"label": "DocType", "fieldname": "doc_type", "fieldtype": "Data", "width": 130},
        {"label": "Reference", "fieldname": "ref_name", "fieldtype": "Data", "width": 160},
        {"label": "Details", "fieldname": "details", "fieldtype": "Data", "width": 300},
        {"label": "Amount", "fieldname": "amount", "fieldtype": "Currency", "width": 120},
    ]

def get_data(project, project_sub_contract=None):
    conditions = ""
    values = {}

    if project:
        conditions += " AND ps.project = %(project)s"
        values["project"] = project

    if project_sub_contract:
        conditions += " AND ps.name = %(project_sub_contract)s"
        values["project_sub_contract"] = project_sub_contract

    subcontract_data = frappe.db.sql(f"""
        SELECT
            ps.name,
            ps.project,
            ps.party_type,
            ps.party_name,
            ps.start_date,
            ps.end_date,
            ps.project_number
        FROM `tabProject Sub-Contracts` ps
        WHERE ps.docstatus < 2 {conditions}
        ORDER BY ps.project
    """, values, as_dict=True)

    full_data = []

    for sc in subcontract_data:
        # Parent row
        sc_row = sc.copy()
        sc_row.update({"doc_type": "", "ref_name": "", "details": "", "amount": None})
        full_data.append(sc_row)

        # Purchase Orders
        purchase_orders = frappe.get_all("Purchase Order",
            filters={"custom_project_sub_contract": sc["name"]},
            fields=["name", "grand_total", "workflow_state", "per_billed"]
        )
        for po in purchase_orders:
            full_data.append({
                "name": "",
                "project": "",
                "party_type": "",
                "party_name": "",
                "start_date": "",
                "end_date": "",
                "project_number": "",
                "doc_type": "→ Purchase Order",
                "ref_name": po["name"],
                "details": f"Status: {po.workflow_state}, Paid: {po.grand_total * po.per_billed}",
                "amount": po["grand_total"]
            })

        # Work Progress Reports
        wprs = frappe.get_all("Work Progress Report",
            filters={"project_sub_contracts": sc["name"]},
            fields=["name", "business_type", "start_date", "end_date"]
        )
        for wpr in wprs:
            full_data.append({
                "name": "",
                "project": "",
                "party_type": "",
                "party_name": "",
                "start_date": "",
                "end_date": "",
                "project_number": "",
                "doc_type": "→ Work Progress Report",
                "ref_name": wpr["name"],
                "details": f"{wpr.business_type} ({wpr.start_date} to {wpr.end_date})",
                "amount": None
            })

        # Invoice Released Memos
        invoices = frappe.get_all("Invoice released Memo",
            filters={"project_sub_contracts": sc["name"]},
            fields=["name", "invoice_no", "invoice_date", "vendor"]
        )
        for inv in invoices:
            full_data.append({
                "name": "",
                "project": "",
                "party_type": "",
                "party_name": "",
                "start_date": "",
                "end_date": "",
                "project_number": "",
                "doc_type": "→ Invoice Memo",
                "ref_name": inv["name"],
                "details": f"Invoice No: {inv.invoice_no}, Vendor: {inv.vendor}, Date: {inv.invoice_date}",
                "amount": None
            })

    return full_data
