import frappe
from frappe import _

from erpnext.accounts.report.general_ledger.general_ledger import execute as standard_gl_execute


def execute(filters=None):
    if not filters:
        return [], []

    filters = frappe._dict(filters)
    standard_columns, data = standard_gl_execute(filters)
    if data:
        enrich_data(data)
    return get_columns(standard_columns), data


def get_columns(standard_columns):
    columns = list(standard_columns)
    custom_columns = [
        {"label": _("Reference Date"), "fieldname": "reference_date", "fieldtype": "Date", "width": 110},
        {"label": _("Supplier Invoice Date"), "fieldname": "bill_date", "fieldtype": "Date", "width": 140},
        {"label": _("Account Number"), "fieldname": "account_number", "fieldtype": "Data", "width": 120},
        {"label": _("Account Name"), "fieldname": "account_name", "fieldtype": "Data", "width": 140},
    ]
    account_index = next((i for i, column in enumerate(columns) if column.get("fieldname") == "account"), None)
    if account_index is not None:
        columns[account_index:account_index] = custom_columns
    else:
        columns.extend(custom_columns)

    columns.append({"label": _("Reference Number"), "fieldname": "reference_no", "fieldtype": "Data", "width": 130})
    return columns


def enrich_data(data):
    if not data:
        return

    accounts = set()
    vouchers = {"Purchase Invoice": set(), "Payment Entry": set(), "Journal Entry": set()}

    for row in data:
        if not row:
            continue
        if account := row.get("account"):
            accounts.add(account)
        voucher_type = row.get("voucher_type")
        if voucher_type in vouchers and (voucher_no := row.get("voucher_no")):
            vouchers[voucher_type].add(voucher_no)

    account_details = _get_account_map(accounts)
    invoice_details = _get_batched_voucher_map("Purchase Invoice", vouchers["Purchase Invoice"], ["bill_date"])
    payment_details = _get_batched_voucher_map("Payment Entry", vouchers["Payment Entry"], ["reference_no", "reference_date"])
    journal_details = _get_batched_voucher_map("Journal Entry", vouchers["Journal Entry"], ["cheque_no", "cheque_date"])

    for row in data:
        if not row:
            continue

        if account := account_details.get(row.get("account")):
            row["account_name"] = account.account_name
            row["account_number"] = account.account_number

        voucher_no = row.get("voucher_no")
        if not voucher_no:
            continue

        voucher_type = row.get("voucher_type")
        if voucher_type == "Purchase Invoice" and (inv := invoice_details.get(voucher_no)):
            row["bill_date"] = inv.bill_date
        elif voucher_type == "Payment Entry" and (pe := payment_details.get(voucher_no)):
            row["reference_no"] = pe.reference_no
            row["reference_date"] = pe.reference_date
        elif voucher_type == "Journal Entry" and (je := journal_details.get(voucher_no)):
            row["reference_no"] = je.cheque_no
            row["reference_date"] = je.cheque_date


def _get_account_map(accounts):
    if not accounts:
        return {}

    acc_list = list(accounts)
    details = {}
    for i in range(0, len(acc_list), 1000):
        chunk = acc_list[i : i + 1000]
        records = frappe.db.get_values(
            "Account",
            {"name": ("in", tuple(chunk))},
            ["name", "account_name", "account_number"],
            as_dict=True,
        )
        for row in (records or []):
            details[row.name] = row
    return details


def _get_batched_voucher_map(doctype, names, fields):
    if not names:
        return {}

    name_list = list(names)
    voucher_map = {}
    for i in range(0, len(name_list), 1000):
        chunk = name_list[i : i + 1000]
        records = frappe.db.get_values(
            doctype,
            {"name": ("in", tuple(chunk))},
            ["name", *fields],
            as_dict=True,
        )
        for row in (records or []):
            voucher_map[row.name] = row
    return voucher_map



def add_account_details(data):
    if not data:
        return
    accounts = {row.get("account") for row in data if row.get("account")}
    account_details = _get_account_map(accounts)
    for row in data:
        if not row:
            continue
        if account := account_details.get(row.get("account")):
            row["account_name"] = account.account_name
            row["account_number"] = account.account_number


def add_voucher_details(data):
    if not data:
        return
    vouchers = {"Purchase Invoice": set(), "Payment Entry": set(), "Journal Entry": set()}
    for row in data:
        if not row:
            continue
        voucher_type = row.get("voucher_type")
        if voucher_type in vouchers and (voucher_no := row.get("voucher_no")):
            vouchers[voucher_type].add(voucher_no)

    invoice_details = _get_batched_voucher_map("Purchase Invoice", vouchers["Purchase Invoice"], ["bill_date"])
    payment_details = _get_batched_voucher_map("Payment Entry", vouchers["Payment Entry"], ["reference_no", "reference_date"])
    journal_details = _get_batched_voucher_map("Journal Entry", vouchers["Journal Entry"], ["cheque_no", "cheque_date"])

    for row in data:
        if not row:
            continue
        voucher_no = row.get("voucher_no")
        if not voucher_no:
            continue
        voucher_type = row.get("voucher_type")
        if voucher_type == "Purchase Invoice" and (inv := invoice_details.get(voucher_no)):
            row["bill_date"] = inv.bill_date
        elif voucher_type == "Payment Entry" and (pe := payment_details.get(voucher_no)):
            row["reference_no"] = pe.reference_no
            row["reference_date"] = pe.reference_date
        elif voucher_type == "Journal Entry" and (je := journal_details.get(voucher_no)):
            row["reference_no"] = je.cheque_no
            row["reference_date"] = je.cheque_date


def get_voucher_map(doctype, names, fields):
    return _get_batched_voucher_map(doctype, names, fields)
