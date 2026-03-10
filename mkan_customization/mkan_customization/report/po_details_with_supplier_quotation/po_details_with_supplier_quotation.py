import frappe
from frappe import _

def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": _("PO No"), "fieldname": "po_no", "fieldtype": "Link", "options": "Purchase Order", "width": 160},
        {"label": _("PO Date"), "fieldname": "po_date", "fieldtype": "Date", "width": 110},
        {"label": _("PO Net Total"), "fieldname": "net_total", "fieldtype": "Currency", "width": 130},
        {"label": _("PO Grand Total"), "fieldname": "grand_total", "fieldtype": "Currency", "width": 140},
		{"label": _("Supplier Quotation"), "fieldname": "supplier_quotation", "fieldtype": "Link", "options": "Supplier Quotation", "width": 180},
        {"label": _("Supplier Code"), "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 140},
        {"label": _("Supplier Name"), "fieldname": "supplier_name", "fieldtype": "Data", "width": 180},
        {"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 150},
        {"label": _("Workflow State"), "fieldname": "workflow_state", "fieldtype": "Data", "width": 140},
    ]


def get_data(filters):
    conditions = []

    if filters.get("supplier"):
        conditions.append("po.supplier = %(supplier)s")

    if filters.get("project"):
        conditions.append("po.project = %(project)s")

    if filters.get("purchase_order"):
        conditions.append("po.name = %(purchase_order)s")

    if filters.get("from_date"):
        conditions.append("po.transaction_date >= %(from_date)s")

    if filters.get("to_date"):
        conditions.append("po.transaction_date <= %(to_date)s")

    where_conditions = " AND ".join(conditions)
    if where_conditions:
        where_conditions = " AND " + where_conditions

    return frappe.db.sql(f"""
        SELECT DISTINCT
            po.name AS po_no,
            po.transaction_date AS po_date,
            po.net_total,
            po.grand_total,
            po.supplier,
            po.supplier_name,
            sq.name AS supplier_quotation,
            po.project,
            po.workflow_state
        FROM `tabPurchase Order` po

        INNER JOIN `tabBid Tabulation Discussion` bt
            ON bt.name = po.bid_tabulation

        INNER JOIN `tabRequest for Quotation` rfq
            ON rfq.name = bt.request_for_quotation

        INNER JOIN `tabRequest for Quotation Item` rfqi
            ON rfqi.parent = rfq.name

        INNER JOIN `tabSupplier Quotation Item` sqi
            ON sqi.request_for_quotation_item = rfqi.name

        INNER JOIN `tabSupplier Quotation` sq
            ON sq.name = sqi.parent

        WHERE
            po.docstatus != 2
            AND sq.docstatus = 1
            AND sq.grand_total = 0
            {where_conditions}

        ORDER BY po.transaction_date DESC
    """, filters, as_dict=True)