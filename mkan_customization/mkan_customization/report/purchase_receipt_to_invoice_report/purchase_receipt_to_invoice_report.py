# Copyright (c) 2026, Finbyz and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    filters = filters or {}

    columns = [
        {
            "label": "Purchase Receipt",
            "fieldname": "purchase_receipt",
            "fieldtype": "Link",
            "options": "Purchase Receipt",
            "width": 150,
        },
        {
            "label": "Date",
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": "Supplier Code",
            "fieldname": "supplier_code",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 150,
        },
        {
            "label": "Supplier Name",
            "fieldname": "supplier_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Project Code",
            "fieldname": "project_code",
            "fieldtype": "Link",
            "options": "Project",
            "width": 150,
        },
        {
            "label": "Purchase Receipt Amount",
            "fieldname": "purchase_receipt_amount",
            "fieldtype": "Currency",
            "width": 150,
        },
        {
            "label": "Purchase Receipt Status",
            "fieldname": "purchase_receipt_status",
            "fieldtype": "Data",
            "width": 150,
        },
        {
            "label": "No. of Invoices",
            "fieldname": "no_of_invoices",
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "label": "Purchase Invoices Amount",
            "fieldname": "purchase_invoices_amount",
            "fieldtype": "Currency",
            "width": 160,
        },
        {
            "label": "Pending Amount",
            "fieldname": "pending_amount",
            "fieldtype": "Currency",
            "width": 140,
        },
    ]

    conditions = [
        "pr.docstatus = 1",
        "pr.posting_date BETWEEN %(from_date)s AND %(to_date)s",
    ]

    if filters.get("purchase_receipt"):
        conditions.append("pr.name = %(purchase_receipt)s")

    if filters.get("supplier"):
        conditions.append("pr.supplier = %(supplier)s")

    if filters.get("project"):
        conditions.append("pr.project = %(project)s")

    query = f"""
        SELECT
            pr.name AS purchase_receipt,
            pr.posting_date AS date,
            pr.supplier AS supplier_code,
            pr.supplier_name AS supplier_name,
            pr.project AS project_code,
            pr.total AS purchase_receipt_amount,
            pr.workflow_state AS purchase_receipt_status,

            COUNT(DISTINCT pi.name) AS no_of_invoices,

            IFNULL(SUM(pii.net_amount), 0) AS purchase_invoices_amount,

            (
                pr.total - IFNULL(SUM(pii.net_amount), 0)
            ) AS pending_amount

        FROM `tabPurchase Receipt` pr

        INNER JOIN `tabPurchase Receipt Item` pri
            ON pri.parent = pr.name

        LEFT JOIN `tabPurchase Invoice Item` pii
            ON (
                pii.pr_detail = pri.name

                OR

                (
                    pii.pr_detail IS NULL
                    AND pii.purchase_order IS NOT NULL
                    AND pii.purchase_order = pri.purchase_order
                )
            )
            AND pii.docstatus = 1

        LEFT JOIN `tabPurchase Invoice` pi
            ON pi.name = pii.parent
            AND pi.docstatus = 1

        LEFT JOIN `tabProject` prj
            ON pr.project = prj.name

        WHERE {" AND ".join(conditions)}

        GROUP BY
            pr.name,
            pr.posting_date,
            pr.supplier,
            pr.supplier_name,
            pr.project,
            pr.total,
            pr.workflow_state

        ORDER BY pr.posting_date DESC
    """

    data = frappe.db.sql(
        query,
        {
            "from_date": filters.get("from_date"),
            "to_date": filters.get("to_date"),
            "purchase_receipt": filters.get("purchase_receipt"),
            "supplier": filters.get("supplier"),
            "project": filters.get("project"),
        },
        as_dict=True,
    )

    return columns, data