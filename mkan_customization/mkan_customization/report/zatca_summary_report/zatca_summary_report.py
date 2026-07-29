import frappe

def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = []

    # ---------------------------
    # PURCHASE INVOICE RETURNS / DEBIT NOTES
    # ---------------------------
    pi_conditions = []
    if filters.get("from_date"):
        pi_conditions.append("pi.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        pi_conditions.append("pi.posting_date <= %(to_date)s")
    pi_condition = " AND " + " AND ".join(pi_conditions) if pi_conditions else ""

    purchase_returns = frappe.db.sql(f"""
        SELECT
            pi.taxes_and_charges AS buying_tax_template,
            pi.total AS amount_subject_to_tax,
            pi.name AS return_debit_note,
            pi.net_total AS net_amount,
            pi.total_taxes_and_charges AS vat_amount
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus = 1 AND pi.is_return = 1 {pi_condition}
        ORDER BY pi.posting_date ASC
    """, filters, as_dict=True)

    if purchase_returns:
        data.append({"buying_tax_template": "=== PURCHASE RETURNS / DEBIT NOTES ==="})
        data.extend(purchase_returns)

    # ---------------------------
    # SALES INVOICE RETURNS / CREDIT NOTES
    # ---------------------------
    si_conditions = []
    if filters.get("from_date"):
        si_conditions.append("si.posting_date >= %(from_date)s")
    if filters.get("to_date"):
        si_conditions.append("si.posting_date <= %(to_date)s")
    si_condition = " AND " + " AND ".join(si_conditions) if si_conditions else ""

    sales_returns = frappe.db.sql(f"""
        SELECT
            si.taxes_and_charges AS sales_tax_template,
            si.total AS amount_subject_to_tax,
            si.name AS return_credit_note,
            si.net_total AS net_amount,
            si.total_taxes_and_charges AS vat_amount
        FROM `tabSales Invoice` si
        WHERE si.docstatus = 1 AND si.is_return = 1 {si_condition}
        ORDER BY si.posting_date ASC
    """, filters, as_dict=True)

    if sales_returns:
        data.append({"buying_tax_template": "=== SALES RETURNS / CREDIT NOTES ==="})
        data.extend(sales_returns)

    return columns, data


def get_columns():
    return [
        {"label": "Buying Tax Template", "fieldname": "buying_tax_template", "fieldtype": "Data", "width": 200},
        {"label": "Sales Tax Template", "fieldname": "sales_tax_template", "fieldtype": "Data", "width": 200},
        {"label": "Amount Subject to Tax Rate (SAR)", "fieldname": "amount_subject_to_tax", "fieldtype": "Currency", "width": 180},
        {"label": "Return / Debit Note", "fieldname": "return_debit_note", "fieldtype": "Data", "width": 180},
        {"label": "Return / Credit Note", "fieldname": "return_credit_note", "fieldtype": "Data", "width": 180},
        {"label": "Net Amount", "fieldname": "net_amount", "fieldtype": "Currency", "width": 150},
        {"label": "VAT Amount", "fieldname": "vat_amount", "fieldtype": "Currency", "width": 150},
    ]
