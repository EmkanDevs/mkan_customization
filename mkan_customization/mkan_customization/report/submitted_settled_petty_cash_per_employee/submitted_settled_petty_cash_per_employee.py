# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    if not filters:
        filters = {}

    # Default to logged in employee if none provided
    if not filters.get("employee"):
        emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if emp:
            filters["employee"] = emp

    columns = [
        {"label": "Employee No", "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": "Employee Name", "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
        {"label": "No. of Claims", "fieldname": "no_of_claims", "fieldtype": "Int", "width": 120},
        {"label": "Project Name", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 150},
        {"label": "Sum of Total Amount", "fieldname": "total_amount", "fieldtype": "Currency", "width": 150},
    ]

    # Build where clauses
    parent_where = "docstatus = 1"
    child_where = "ec.docstatus = 1"
    values = {}

    if filters.get("employee"):
        parent_where += " AND employee = %(employee)s"
        child_where += " AND ec.employee = %(employee)s"
        values["employee"] = filters["employee"]

    if filters.get("project"):
        parent_where += " AND project = %(project)s"
        child_where += " AND ec.project = %(project)s"
        values["project"] = filters["project"]

    # Handle Date Range filter
    if filters.get("date_range"):
        from_date, to_date = filters["date_range"]
        parent_where += " AND posting_date BETWEEN %(from_date)s AND %(to_date)s"
        child_where += " AND ec.posting_date BETWEEN %(from_date)s AND %(to_date)s"
        values["from_date"] = from_date
        values["to_date"] = to_date

    data = frappe.db.sql(f"""
        SELECT
            p.employee,
            p.employee_name,
            COALESCE(c.no_of_claims, 0) AS no_of_claims,
            p.project,
            p.total_amount
        FROM (
            SELECT
                employee,
                employee_name,
                project,
                COALESCE(SUM(grand_total), 0) AS total_amount
            FROM `tabExpense Claim`
            WHERE {parent_where}
            GROUP BY employee, employee_name, project
        ) p
        LEFT JOIN (
            SELECT
                ec.employee,
                ec.project,
                COUNT(ecd.name) AS no_of_claims
            FROM `tabExpense Claim` ec
            JOIN `tabExpense Claim Detail` ecd
                ON ec.name = ecd.parent
            WHERE {child_where}
            GROUP BY ec.employee, ec.project
        ) c
        ON p.employee = c.employee AND COALESCE(p.project, '') = COALESCE(c.project, '')
        ORDER BY p.employee
    """, values, as_dict=True)

    return columns, data
