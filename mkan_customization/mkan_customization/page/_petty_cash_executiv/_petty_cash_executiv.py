import frappe
from frappe import _
from frappe.utils import fmt_money, getdate, today

@frappe.whitelist()
def get_dashboard_data(company=None, year=None, month=None, from_date=None, to_date=None, custodian=None, project=None):
    """
    Returns all dashboard data: KPIs, charts, and grid data.
    Called from the Petty Cash Executive Dashboard page.
    """
    conditions = ["pr.is_petty_cash = 1", "pr.docstatus != 2"]
    params = {}

    if company:
        conditions.append("pr.company = %(company)s")
        params["company"] = company
    if from_date:
        conditions.append("pr.posting_date >= %(from_date)s")
        params["from_date"] = from_date
    if to_date:
        conditions.append("pr.posting_date <= %(to_date)s")
        params["to_date"] = to_date
    if custodian and custodian != "All":
        conditions.append("pr.petty_cash_employee = %(custodian)s")
        params["custodian"] = custodian
    if project and project != "All":
        conditions.append("pr.project = %(project)s")
        params["project"] = project
    if year:
        conditions.append("YEAR(pr.posting_date) = %(year)s")
        params["year"] = int(year)
    if month and month != "All":
        conditions.append("MONTH(pr.posting_date) = %(month)s")
        params["month"] = int(month)

    where_clause = " AND ".join(conditions)

    # ── KPIs ──
    kpi_sql = """
        SELECT 
            IFNULL(SUM(pr.grand_total), 0) AS total_spent,
            IFNULL(SUM(pr.total_taxes_and_charges), 0) AS total_tax,
            COUNT(*) AS total_receipts,
            IFNULL(AVG(pr.grand_total), 0) AS avg_receipt,
            COUNT(DISTINCT pr.petty_cash_employee) AS active_custodians
        FROM `tabPurchase Receipt` pr
        WHERE {where}
    """.format(where=where_clause)
    kpis = frappe.db.sql(kpi_sql, params, as_dict=True)[0]

    # ── Pending ──
    pending_sql = """
        SELECT 
            COUNT(*) AS pending_count,
            IFNULL(SUM(pr.grand_total), 0) AS pending_amount
        FROM `tabPurchase Receipt` pr
        WHERE {where} AND pr.workflow_state = 'Pending Approval'
    """.format(where=where_clause)
    pending = frappe.db.sql(pending_sql, params, as_dict=True)[0]

    # ── Top Custodian ──
    top_custodian_sql = """
        SELECT 
            COALESCE(pr.custom_petty_cash_holder_name, pr.petty_cash_employee) AS custodian,
            IFNULL(SUM(pr.grand_total), 0) AS amount
        FROM `tabPurchase Receipt` pr
        WHERE {where}
        GROUP BY pr.petty_cash_employee
        ORDER BY amount DESC
        LIMIT 1
    """.format(where=where_clause)
    top_custodian = frappe.db.sql(top_custodian_sql, params, as_dict=True)
    top_custodian = top_custodian[0] if top_custodian else {"custodian": "—", "amount": 0}

    # ── Total Quantity ──
    qty_sql = """
        SELECT IFNULL(SUM(pri.qty), 0) AS total_qty
        FROM `tabPurchase Receipt` pr
        LEFT JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
        WHERE {where}
    """.format(where=where_clause)
    qty_result = frappe.db.sql(qty_sql, params, as_dict=True)[0]

    # ── Custodian Chart ──
    custodian_sql = """
        SELECT 
            COALESCE(pr.custom_petty_cash_holder_name, pr.petty_cash_employee) AS label,
            IFNULL(SUM(pr.grand_total), 0) AS value
        FROM `tabPurchase Receipt` pr
        WHERE {where}
        GROUP BY pr.petty_cash_employee
        ORDER BY value DESC
    """.format(where=where_clause)
    custodian_chart = frappe.db.sql(custodian_sql, params, as_dict=True)

    # ── Project Chart ──
    project_sql = """
        SELECT 
            COALESCE(prj.project_name, pr.project) AS label,
            IFNULL(SUM(pr.grand_total), 0) AS value
        FROM `tabPurchase Receipt` pr
        LEFT JOIN `tabProject` prj ON prj.name = pr.project
        WHERE {where}
        GROUP BY pr.project
        ORDER BY value DESC
    """.format(where=where_clause)
    project_chart = frappe.db.sql(project_sql, params, as_dict=True)

    # ── Vendor Chart ──
    vendor_sql = """
        SELECT 
            COALESCE(pr.supplier_name, pr.supplier) AS label,
            IFNULL(SUM(pr.grand_total), 0) AS value
        FROM `tabPurchase Receipt` pr
        WHERE {where}
        GROUP BY pr.supplier
        ORDER BY value DESC
        LIMIT 10
    """.format(where=where_clause)
    vendor_chart = frappe.db.sql(vendor_sql, params, as_dict=True)

    # ── Monthly Trend ──
    trend_sql = """
        SELECT 
            DATE_FORMAT(pr.posting_date, '%%b %%Y') AS label,
            IFNULL(SUM(pr.grand_total), 0) AS value
        FROM `tabPurchase Receipt` pr
        WHERE {where}
        GROUP BY YEAR(pr.posting_date), MONTH(pr.posting_date)
        ORDER BY YEAR(pr.posting_date), MONTH(pr.posting_date)
    """.format(where=where_clause)
    trend_chart = frappe.db.sql(trend_sql, params, as_dict=True)

    # ── Workflow Status ──
    status_sql = """
        SELECT 
            pr.workflow_state AS label,
            COUNT(*) AS value
        FROM `tabPurchase Receipt` pr
        WHERE {where}
        GROUP BY pr.workflow_state
    """.format(where=where_clause)
    status_chart = frappe.db.sql(status_sql, params, as_dict=True)

    return {
        "kpis": {
            "total_spent": float(kpis.get("total_spent", 0)),
            "total_tax": float(kpis.get("total_tax", 0)),
            "total_receipts": int(kpis.get("total_receipts", 0)),
            "avg_receipt": float(kpis.get("avg_receipt", 0)),
            "active_custodians": int(kpis.get("active_custodians", 0)),
            "net_total": float(kpis.get("total_spent", 0)) - float(kpis.get("total_tax", 0)),
            "pending_count": int(pending.get("pending_count", 0)),
            "pending_amount": float(pending.get("pending_amount", 0)),
            "top_custodian": top_custodian,
            "total_qty": float(qty_result.get("total_qty", 0))
        },
        "custodian_chart": custodian_chart,
        "project_chart": project_chart,
        "vendor_chart": vendor_chart,
        "trend_chart": trend_chart,
        "status_chart": status_chart
    }


@frappe.whitelist()
def get_receipts_grid(company=None, year=None, month=None, from_date=None, to_date=None, 
                       custodian=None, project=None, search_term=None, start=0, page_length=50):
    """
    Returns paginated Purchase Receipt data for the Live Log grid.
    """
    conditions = ["pr.is_petty_cash = 1", "pr.docstatus != 2"]
    params = {"start": int(start), "page_length": int(page_length)}

    if company:
        conditions.append("pr.company = %(company)s")
        params["company"] = company
    if from_date:
        conditions.append("pr.posting_date >= %(from_date)s")
        params["from_date"] = from_date
    if to_date:
        conditions.append("pr.posting_date <= %(to_date)s")
        params["to_date"] = to_date
    if custodian and custodian != "All":
        conditions.append("pr.petty_cash_employee = %(custodian)s")
        params["custodian"] = custodian
    if project and project != "All":
        conditions.append("pr.project = %(project)s")
        params["project"] = project
    if year:
        conditions.append("YEAR(pr.posting_date) = %(year)s")
        params["year"] = int(year)
    if month and month != "All":
        conditions.append("MONTH(pr.posting_date) = %(month)s")
        params["month"] = int(month)

    where_clause = " AND ".join(conditions)

    search_condition = ""
    if search_term:
        search_condition = """ AND (
            pr.name LIKE %(search)s 
            OR pr.custom_petty_cash_holder_name LIKE %(search)s
            OR pr.supplier_name LIKE %(search)s
            OR pr.project LIKE %(search)s
            OR prj.project_name LIKE %(search)s
        )"""
        params["search"] = f"%{search_term}%"

    sql = """
        SELECT 
            pr.name AS purchase_receipt,
            pr.posting_date,
            pr.custom_petty_cash_holder_name AS custody_employee,
            pr.supervisor AS custody_manager,
            pr.supplier_name,
            COALESCE(prj.project_name, pr.project) AS project_name,
            pr.total_taxes_and_charges AS tax_amount,
            pr.grand_total,
            pr.workflow_state
        FROM `tabPurchase Receipt` pr
        LEFT JOIN `tabProject` prj ON prj.name = pr.project
        WHERE {where} {search}
        ORDER BY pr.posting_date DESC, pr.creation DESC
        LIMIT %(page_length)s OFFSET %(start)s
    """.format(where=where_clause, search=search_condition)

    data = frappe.db.sql(sql, params, as_dict=True)

    # Fetch items for each receipt
    for row in data:
        items = frappe.db.sql("""
            SELECT GROUP_CONCAT(description SEPARATOR ', ') AS items
            FROM `tabPurchase Receipt Item`
            WHERE parent = %(parent)s
            LIMIT 1
        """, {"parent": row.purchase_receipt}, as_dict=True)
        row["items"] = items[0]["items"] if items and items[0]["items"] else "—"
        row["posting_date"] = frappe.format_value(row["posting_date"], {"fieldtype": "Date"})

    # Total count for pagination
    count_sql = """
        SELECT COUNT(*) AS total
        FROM `tabPurchase Receipt` pr
        LEFT JOIN `tabProject` prj ON prj.name = pr.project
        WHERE {where} {search}
    """.format(where=where_clause, search=search_condition)
    total = frappe.db.sql(count_sql, params, as_dict=True)[0].get("total", 0)

    return {"data": data, "total": int(total)}


@frappe.whitelist()
def get_filter_options():
    """
    Returns dropdown options for filters.
    """
    custodians = frappe.db.sql("""
        SELECT name, employee_name 
        FROM `tabPetty Cash Authorized Employees`
        WHERE status = 'Active'
        ORDER BY employee_name
    """, as_dict=True)

    projects = frappe.db.sql("""
        SELECT name, project_name 
        FROM `tabProject`
        WHERE status = 'Open'
        ORDER BY project_name
    """, as_dict=True)

    companies = frappe.db.sql("""
        SELECT name FROM `tabCompany` ORDER BY name
    """, as_dict=True)

    return {
        "custodians": custodians,
        "projects": projects,
        "companies": companies
    }