import frappe


def execute(filters=None):
    filters = frappe._dict(filters or {})

    validate_filters(filters)

    columns = get_columns()
    data = get_data(filters)

    return columns, data


def validate_filters(filters):
    if not filters.get("from_date"):
        frappe.throw("From Date is required")

    if not filters.get("to_date"):
        frappe.throw("To Date is required")

    if filters.from_date > filters.to_date:
        frappe.throw("From Date cannot be greater than To Date")


def get_columns():
    return [
        {
            "label": "Posting Date",
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 110,
        },
        {
            "label": "Year",
            "fieldname": "year",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": "Quarter Name",
            "fieldname": "quarter_name",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": "Month Number",
            "fieldname": "month_number",
            "fieldtype": "Int",
            "width": 100,
        },
        {
            "label": "Month Name",
            "fieldname": "month_name",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": "Voucher Type",
            "fieldname": "voucher_type",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Voucher Sub-Type",
            "fieldname": "voucher_subtype",
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "label": "Account Type",
            "fieldname": "root_type",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": "Account",
            "fieldname": "account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 300,
        },
        {
            "label": "Debit (SAR)",
            "fieldname": "debit",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": "Credit (SAR)",
            "fieldname": "credit",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": "Net",
            "fieldname": "net",
            "fieldtype": "Currency",
            "width": 120,
        },
        {
            "label": "Balance (SAR)",
            "fieldname": "balance",
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "label": "Voucher No",
            "fieldname": "voucher_no",
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "label": "Project",
            "fieldname": "project",
            "fieldtype": "Link",
            "options": "Project",
            "width": 150,
        },
        {
            "label": "Project Name",
            "fieldname": "project_name",
            "fieldtype": "Data",
            "width": 300,
        },
        {
            "label": "Department",
            "fieldname": "department",
            "fieldtype": "Link",
            "options": "Department",
            "width": 300,
        },
        {
            "label": "Remark",
            "fieldname": "remarks",
            "fieldtype": "Data",
            "width": 300,
        },
    ]


def get_data(filters):
    conditions = [
        "gle.is_cancelled = 0",
        "acc.root_type IN ('Income', 'Expense')",
        "gle.posting_date BETWEEN %(from_date)s AND %(to_date)s",
    ]

    if filters.get("voucher_type"):
        conditions.append(
            "gle.voucher_type = %(voucher_type)s"
        )

    if filters.get("voucher_subtype"):
        conditions.append(
            "gle.voucher_subtype = %(voucher_subtype)s"
        )

    if filters.get("account_type"):
        conditions.append(
            "acc.root_type = %(account_type)s"
        )

    if filters.get("voucher_no"):
        conditions.append(
            "gle.voucher_no = %(voucher_no)s"
        )

    if filters.get("project"):
        conditions.append(
            "gle.project = %(project)s"
        )

    if filters.get("department"):
        conditions.append(
            "gle.department = %(department)s"
        )

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            gle.posting_date AS posting_date,
            YEAR(gle.posting_date) AS year,
            CONCAT('Q', QUARTER(gle.posting_date)) AS quarter_name,
            MONTH(gle.posting_date) AS month_number,
            MONTHNAME(gle.posting_date) AS month_name,

            gle.voucher_type AS voucher_type,
            gle.voucher_subtype AS voucher_subtype,

            acc.root_type AS root_type,
            gle.account AS account,

            gle.debit AS debit,
            gle.credit AS credit,
            (gle.credit - gle.debit) AS net,

            (
                SELECT SUM(g2.debit - g2.credit)
                FROM `tabGL Entry` g2
                WHERE
                    g2.account = gle.account
                    AND g2.posting_date <= gle.posting_date
                    AND g2.is_cancelled = 0
            ) AS balance,

            gle.voucher_no AS voucher_no,
            gle.project AS project,
            prj.project_name AS project_name,
            gle.department AS department,
            gle.remarks AS remarks

        FROM `tabGL Entry` gle

        LEFT JOIN `tabProject` prj
            ON prj.name = gle.project

        INNER JOIN `tabAccount` acc
            ON acc.name = gle.account

        WHERE {where_clause}

        ORDER BY
            YEAR(gle.posting_date),
            MONTH(gle.posting_date),
            gle.posting_date,
            acc.root_type,
            gle.account
    """

    return frappe.db.sql(
        query,
        filters,
        as_dict=True
    )