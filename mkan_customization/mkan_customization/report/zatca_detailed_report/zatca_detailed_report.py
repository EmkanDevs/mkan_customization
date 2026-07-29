import frappe

import frappe

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = []

    conditions = []
    if filters.get("from_date"):
        conditions.append("pi.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("pi.posting_date <= %(to_date)s")
    pi_condition = " AND " + " AND ".join(conditions) if conditions else ""

    purchase_invoices = frappe.db.sql(f"""
        SELECT
            'Private Sector' AS sector_type,
            'Inputs' AS transaction_type,
            pi.posting_date AS transaction_date,
            sup.supplier_code AS supplier_number,
            pi.supplier_name AS supplier_name,
            pi.bill_no AS invoice_number,
            sup.tax_id AS tax_number,
            pi.taxes_and_charges AS taxes_and_charges,
            pi.total AS amount_subject_to_tax,
            pi.total_taxes_and_charges AS tax
        FROM `tabPurchase Invoice` pi
        LEFT JOIN `tabSupplier` sup ON pi.supplier = sup.name
        WHERE pi.docstatus = 1 {pi_condition}
        ORDER BY pi.posting_date ASC
    """, filters, as_dict=True)

    if purchase_invoices:
        data.append({"sector_type": "=== PURCHASE INVOICES ==="})
        data.extend(purchase_invoices)

    # Sales Invoices conditions
    conditions = []
    if filters.get("from_date"):
        conditions.append("si.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("si.posting_date <= %(to_date)s")
    si_condition = " AND " + " AND ".join(conditions) if conditions else ""

    sales_invoices = frappe.db.sql(f"""
        SELECT
            cu.customer_group AS sector_type,
            'Inputs' AS transaction_type,
            si.posting_date AS transaction_date,
            cu.custom_customer_vendor_no AS customer_number,
            si.customer_name AS customer_name,
            si.name AS invoice_number,
            cmp.tax_id AS tax_number,
            si.taxes_and_charges AS taxes_and_charges,
            si.outstanding_amount AS amount_subject_to_tax,
            si.total_taxes_and_charges AS tax
        FROM `tabSales Invoice` si
        LEFT JOIN `tabCustomer` cu ON si.customer = cu.name
        LEFT JOIN `tabCompany` cmp ON si.company = cmp.name
        WHERE si.docstatus = 1 {si_condition}
        ORDER BY si.posting_date ASC
    """, filters, as_dict=True)

    if sales_invoices:
        data.append({"sector_type": "=== SALES INVOICES ==="})
        data.extend(sales_invoices)

    return columns, data


def get_columns():
    return [
        {"label": "Sector Type", "fieldname": "sector_type", "fieldtype": "Data", "width": 150},
        {"label": "Transaction Type", "fieldname": "transaction_type", "fieldtype": "Data", "width": 120},
        {"label": "Transaction Date", "fieldname": "transaction_date", "fieldtype": "Date", "width": 120},
        {"label": "Supplier/Customer Number", "fieldname": "supplier_number", "fieldtype": "Data", "width": 150},
        {"label": "Supplier/Customer Name", "fieldname": "supplier_name", "fieldtype": "Data", "width": 200},
        {"label": "Invoice Number", "fieldname": "invoice_number", "fieldtype": "Data", "width": 150},
        {"label": "Tax Number", "fieldname": "tax_number", "fieldtype": "Data", "width": 150},
        {"label": "Taxes and Charges", "fieldname": "taxes_and_charges", "fieldtype": "Data", "width": 200},
        {"label": "Amount Subject to Tax Rate (SAR)", "fieldname": "amount_subject_to_tax", "fieldtype": "Currency", "width": 180},
        {"label": "Tax (VAT 15%)", "fieldname": "tax", "fieldtype": "Currency", "width": 150},
    ]
