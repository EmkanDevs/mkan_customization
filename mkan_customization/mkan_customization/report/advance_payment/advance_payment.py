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
		{"fieldname": "total_advance", "label": _("Advance Recovered"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "advance_percentage", "label": _("Advance Recovery %"), "fieldtype": "Percent", "width": 140},
		{"fieldname": "invoice_status", "label": _("Invoice Status"), "fieldtype": "Data", "width": 100},
	]


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
			COALESCE(si.total_advance, 0) as total_advance,
			COALESCE(si.advance_payment, 0) as advance_percentage
		FROM
			`tabSales Invoice` si
		LEFT JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		LEFT JOIN `tabSales Order` so ON so.name = sii.sales_order
		WHERE si.docstatus < 2 {conditions}
		GROUP BY si.name
		ORDER BY si.name DESC
	"""

	data = frappe.db.sql(query, filters, as_dict=1)

	for row in data:
		row["grand_total"] = flt(row["grand_total"], 2)
		row["total_advance"] = flt(row["total_advance"], 2)
		row["advance_percentage"] = flt(row["advance_percentage"], 2)
		row["sales_order_amount"] = flt(row.get("sales_order_amount", 0), 2)

	return data


def get_number_cards(filters):
	conditions = ""

	if filters.get("sales_order"):
		conditions += """ AND EXISTS (
			SELECT 1 FROM `tabSales Invoice Item` sii2
			WHERE sii2.parent = si.name AND sii2.sales_order = %(sales_order)s
		)"""

	# F05: Only submitted invoices (docstatus = 1) must enter posted totals
	summary_query = f"""
		SELECT
			COUNT(DISTINCT si.name) as total_invoices,
			SUM(si.grand_total) as total_amount,
			SUM(COALESCE(si.total_advance, 0)) as total_advance_payment
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1 {conditions}
	"""

	result = frappe.db.sql(summary_query, filters, as_dict=1)[0]
	total_advance_recovered = flt(result.get("total_advance_payment") or 0, 2)

	cards = [
		{
			"value": result.get("total_invoices") or 0,
			"label": _("Total Invoices"),

			"datatype": "Int",
			"indicator": "Blue",
		},
		{
			"value": flt(result.get("total_amount") or 0, 2),
			"label": _("Total Invoice Amount"),
			"datatype": "Currency",
			"indicator": "Green",
		},
		{
			"value": total_advance_recovered,
			"label": _("Total Advance Recovered"),
			"datatype": "Currency",
			"indicator": "Red",
		},
	]

	if filters.get("sales_order"):
		advance_received = flt(frappe.db.get_value("Sales Order", filters.get("sales_order"), "advance_paid") or 0, 2)
		available_advance = max(0.0, advance_received - total_advance_recovered)
		cards.append({
			"value": advance_received,
			"label": _("Advance Received (SO)"),
			"datatype": "Currency",
			"indicator": "Blue",
		})
		cards.append({
			"value": available_advance,
			"label": _("Available Advance"),
			"datatype": "Currency",
			"indicator": "Green" if available_advance > 0 else "Grey",
		})

	return cards

