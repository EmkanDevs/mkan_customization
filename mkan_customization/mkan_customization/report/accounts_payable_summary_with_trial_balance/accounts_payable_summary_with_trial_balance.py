import frappe
from frappe import _
from frappe.utils import flt, nowdate

from erpnext.accounts.report.accounts_payable_summary.accounts_payable_summary import (
    execute as ap_summary_execute,
)


def execute(filters=None):
    filters = frappe._dict(filters or {})
    result = ap_summary_execute(filters)
    columns, data = result[0], result[1]
    rest = result[2:]

    company = filters.get("company")
    report_date = filters.get("report_date") or nowdate()

    parties = list({d.get("party") for d in data if d.get("party")})
    supplier_account = get_supplier_accounts(parties, company)

    with_account = [p for p in parties if supplier_account.get(p)]
    without_account = [p for p in parties if not supplier_account.get(p)]

    # (party_type, party, account) -> balance, for suppliers with an account set
    balance_in_account = get_party_account_balances(
        with_account, set(supplier_account.values()), company, report_date
    )
    # (party_type, party) -> balance, for suppliers without an account (all accounts)
    balance_all = get_party_balances(without_account, company, report_date)

    for row in data:
        party = row.get("party")
        if not party:
            continue

        party_type = row.get("party_type") or filters.get("party_type") or "Supplier"
        account = supplier_account.get(party)
        row["payable_account"] = account

        if account:
            # debit - credit of this supplier in its account; payable (credit) is negative
            tb = flt(balance_in_account.get((party_type, party, account)))
        else:
            # account not set: all GL entries of this supplier
            tb = flt(balance_all.get((party_type, party)))

        row["trial_balance"] = tb
        # credit balance vs actual outstanding (Total Amount Due from ageing)
        row["difference"] = flt(-tb) - flt(row.get("total_due"))

    new_cols = [
        {
            "label": _("Diff."),
            "fieldname": "difference",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "label": _("T.B"),
            "fieldname": "trial_balance",
            "fieldtype": "Currency",
            "options": "currency",
            "width": 120,
        },
        {
            "label": _("Payable Account"),
            "fieldname": "payable_account",
            "fieldtype": "Link",
            "options": "Account",
            "width": 180,
        },
    ]

    idx = next(
        (i for i, c in enumerate(columns) if c.get("fieldname") == "supplier_group"),
        len(columns),
    )
    columns[idx:idx] = new_cols

    return (columns, data, *rest)


def get_supplier_accounts(parties, company):
    """party -> account, only for suppliers that have an Accounts row for this company."""
    if not parties:
        return {}

    rows = frappe.get_all(
        "Party Account",
        filters={
            "parenttype": "Supplier",
            "parent": ["in", parties],
            "company": company,
        },
        fields=["parent", "account"],
    )
    return {r.parent: r.account for r in rows if r.account}


def get_party_account_balances(parties, accounts, company, report_date):
    """(party_type, party, account) -> SUM(debit - credit), filtered by party and account."""
    accounts = [a for a in accounts if a]
    if not parties or not accounts:
        return {}

    rows = frappe.db.sql(
        """
        SELECT party_type, party, account, SUM(debit - credit) AS balance
        FROM `tabGL Entry`
        WHERE is_cancelled = 0
          AND company = %s
          AND posting_date <= %s
          AND party IN %s
          AND account IN %s
        GROUP BY party_type, party, account
        """,
        (company, report_date, tuple(parties), tuple(accounts)),
        as_dict=True,
    )
    return {(r.party_type, r.party, r.account): flt(r.balance) for r in rows}


def get_party_balances(parties, company, report_date):
    """(party_type, party) -> SUM(debit - credit) over all accounts."""
    if not parties:
        return {}

    rows = frappe.db.sql(
        """
        SELECT party_type, party, SUM(debit - credit) AS balance
        FROM `tabGL Entry`
        WHERE is_cancelled = 0
          AND company = %s
          AND posting_date <= %s
          AND party IN %s
        GROUP BY party_type, party
        """,
        (company, report_date, tuple(parties)),
        as_dict=True,
    )
    return {(r.party_type, r.party): flt(r.balance) for r in rows}