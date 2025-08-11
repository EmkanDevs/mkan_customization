# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        return [], [], None, None, []

    columns = get_columns()
    data = get_data(filters)
    summary = get_number_cards(filters)

    return columns, data, None, None, summary


def get_columns():
    return [
        {"fieldname": "sales_invoice", "label": _("Sales Invoice"), "fieldtype": "Link", "options": "Sales Invoice", "width": 150},
        {"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "width": 140},
        {"fieldname": "grand_total", "label": _("Invoice Amount"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "posting_date", "label": _("Sales Invoice Date"), "fieldtype": "Date", "width": 120},
        {"fieldname": "sales_orders", "label": _("Related Sales Orders"), "fieldtype": "Data", "width": 200},
        {"fieldname": "sales_order_date", "label": _("Sales Order Date"), "fieldtype": "Date", "width": 120},
        {"fieldname": "sales_order_amount", "label": _("Sales Order Amount"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "retention_amount", "label": _("Retention Amount"), "fieldtype": "Currency", "width": 150},
        {"fieldname": "retention_percentage", "label": _("Retention %"), "fieldtype": "Percent", "width": 100},
        {"fieldname": "invoice_status", "label": _("Invoice Status"), "fieldtype": "Data", "width": 100}
    ]


def get_conditions(filters):
    # Removed customer filter logic
    return ""


def get_data(filters):
    conditions = ""
    if filters.get("sales_order"):
        conditions += """ AND EXISTS (
            SELECT 1 FROM `tabSales Invoice Item` sii2
            WHERE sii2.parent = si.name AND sii2.sales_order = %(sales_order)s
        )"""

    query = f"""
        SELECT
			si.name as sales_invoice,
			si.customer,
			si.grand_total,
			si.posting_date,
			si.status as invoice_status,
			GROUP_CONCAT(DISTINCT so.name) as sales_orders,
			MIN(so.transaction_date) as sales_order_date,
			(
				SELECT SUM(DISTINCT so2.grand_total)
				FROM `tabSales Invoice Item` sii2
				LEFT JOIN `tabSales Order` so2 ON so2.name = sii2.sales_order
				WHERE sii2.parent = si.name
			) as sales_order_amount,
			COALESCE(si.retention_amount, 0) as retention_amount,
			CASE WHEN si.grand_total > 0
				THEN (COALESCE(si.retention_amount, 0) / si.total) * 100
				ELSE 0 END as retention_percentage
		FROM
			`tabSales Invoice` si
		LEFT JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		LEFT JOIN `tabSales Order` so ON so.name = sii.sales_order
		WHERE 1=1 {conditions}
		GROUP BY si.name
		ORDER BY si.name DESC
    """

    data = frappe.db.sql(query, filters, as_dict=1)

    for row in data:
        row["grand_total"] = flt(row["grand_total"], 2)
        row["retention_amount"] = flt(row["retention_amount"], 2)
        row["retention_percentage"] = flt(row["retention_percentage"], 2)
        row["sales_order_amount"] = flt(row.get("sales_order_amount", 0), 2)

    return data


def get_number_cards(filters):
    conditions = ""

    if filters.get("sales_order"):
        conditions += """ AND EXISTS (
            SELECT 1 FROM `tabSales Invoice Item` sii2
            WHERE sii2.parent = si.name AND sii2.sales_order = %(sales_order)s
        )"""

    summary_query = f"""
        SELECT
            COUNT(DISTINCT si.name) as total_invoices,
            SUM(si.grand_total) as total_amount,
            SUM(COALESCE(si.retention_amount, 0)) as total_retention
        FROM `tabSales Invoice` si
        WHERE 1=1 {conditions}
    """

    result = frappe.db.sql(summary_query, filters, as_dict=1)[0]

    return [
        {
            "value": result.get("total_invoices") or 0,
            "label": _("Total Invoices"),
            "datatype": "Int",
            "indicator": "Blue"
        },
        {
            "value": flt(result.get("total_amount") or 0, 2),
            "label": _("Total Invoice Amount"),
            "datatype": "Currency",
            "indicator": "Green"
        },
        {
            "value": flt(result.get("total_retention") or 0, 2),
            "label": _("Total Retention"),
            "datatype": "Currency",
            "indicator": "Red"
        }
    ]
