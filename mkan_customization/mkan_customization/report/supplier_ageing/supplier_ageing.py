import frappe
from frappe.utils import flt, date_diff


def execute(filters=None):
    filters = frappe._dict(filters or {})
    raw = filters.get("range") or "30,60,90,120"
    filters.ranges = [int(x) for x in raw.split(",") if x.strip().isdigit()]
    return get_columns(filters), get_data(filters)


def get_data(filters):
    from_date = filters.from_date
    to_date = filters.to_date
    company = filters.company

    suppliers = frappe.db.sql(
        """
        SELECT DISTINCT g.party, s.supplier_name, s.supplier_group
        FROM `tabGL Entry` g
        LEFT JOIN `tabSupplier` s ON s.name = g.party
        WHERE g.party_type='Supplier'
          AND g.is_cancelled=0
          AND g.company=%s
          AND g.posting_date <= %s
        """,
        (company, to_date),
        as_dict=True,
    )

    rows = []

    for s in suppliers:
        supplier = s.party
        supplier_name = s.supplier_name
        supplier_group = s.supplier_group

        opening = flt(
            frappe.db.sql(
                """
                SELECT SUM(debit - credit)
                FROM `tabGL Entry`
                WHERE party_type='Supplier'
                  AND party=%s
                  AND is_cancelled=0
                  AND posting_date < %s
                  AND company=%s
                """,
                (supplier, from_date, company),
            )[0][0]
        )

        invoiced = flt(
            frappe.db.sql(
                """
                SELECT SUM(debit)
                FROM `tabGL Entry`
                WHERE party_type='Supplier'
                  AND party=%s
                  AND voucher_type='Purchase Invoice'
                  AND debit > 0
                  AND is_cancelled=0
                  AND posting_date BETWEEN %s AND %s
                  AND company=%s
                """,
                (supplier, from_date, to_date, company),
            )[0][0]
        )

        paid = flt(
            frappe.db.sql(
                """
                SELECT SUM(credit)
                FROM `tabGL Entry`
                WHERE party_type='Supplier'
                  AND party=%s
                  AND voucher_type='Payment Entry'
                  AND credit > 0
                  AND is_cancelled=0
                  AND posting_date BETWEEN %s AND %s
                  AND company=%s
                """,
                (supplier, from_date, to_date, company),
            )[0][0]
        )

        debit_note = flt(
            frappe.db.sql(
                """
                SELECT SUM(debit)
                FROM `tabGL Entry`
                WHERE party_type='Supplier'
                  AND party=%s
                  AND voucher_type='Purchase Invoice'
                  AND debit > 0
                  AND credit = 0
                  AND is_cancelled=0
                  AND posting_date BETWEEN %s AND %s
                  AND company=%s
                """,
                (supplier, from_date, to_date, company),
            )[0][0]
        )

        closing = opening + invoiced - paid - debit_note

        ageing = get_ageing(filters, supplier)

        if closing:
            rows.append(
                [supplier, supplier_name, supplier_group, opening, invoiced, paid, debit_note, closing, *ageing]
            )

    return rows


def get_ageing(filters, supplier):
    fifo = []

    gls = frappe.db.sql(
        """
        SELECT posting_date, (debit - credit) AS amt
        FROM `tabGL Entry`
        WHERE party_type='Supplier'
          AND party=%s
          AND is_cancelled=0
          AND posting_date <= %s
          AND company=%s
        ORDER BY posting_date, creation
        """,
        (supplier, filters.to_date, filters.company),
        as_dict=True,
    )

    for g in gls:
        if flt(g.amt) > 0:
            fifo.append([flt(g.amt), g.posting_date])
        else:
            consume_fifo(fifo, abs(flt(g.amt)))

    buckets = [0] * (len(filters.ranges) + 1)

    for amt, dt in fifo:
        age = date_diff(filters.to_date, dt)
        for i, limit in enumerate(filters.ranges):
            if age <= limit:
                buckets[i] += amt
                break
        else:
            buckets[-1] += amt

    return buckets


def consume_fifo(queue, credit):
    while credit and queue:
        if queue[0][0] <= credit:
            credit -= queue[0][0]
            queue.pop(0)
        else:
            queue[0][0] -= credit
            credit = 0


def get_columns(filters):
    columns = [
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 180},
        {"label": "Supplier Name", "fieldname": "supplier_name", "width": 200},
        {"label": "Supplier Group", "fieldname": "supplier_group", "width": 180},
        {"label": "Opening Balance", "fieldname": "opening", "fieldtype": "Currency", "width": 140},
        {"label": "Invoiced Amount", "fieldname": "invoiced", "fieldtype": "Currency", "width": 140},
        {"label": "Paid Amount", "fieldname": "paid", "fieldtype": "Currency", "width": 140},
        {"label": "Debit Note", "fieldname": "debit_note", "fieldtype": "Currency", "width": 140},
        {"label": "Closing Balance", "fieldname": "closing", "fieldtype": "Currency", "width": 140},
    ]

    prev = 0
    for i, r in enumerate(filters.ranges):
        columns.append({"label": f"{prev}-{r}", "fieldname": f"b{i}", "fieldtype": "Currency", "width": 120})
        prev = r + 1

    columns.append({"label": f"{prev}+", "fieldname": f"b{len(filters.ranges)}", "fieldtype": "Currency", "width": 120})

    return columns
