import frappe


@frappe.whitelist()
def get_dashboard_data(filters=None):
    filters = frappe.parse_json(filters) if filters else {}

    return {
        "kpis": get_kpis(filters),
        "supplier_chart": get_supplier_chart(filters),
        "project_chart": get_project_chart(filters),
        "team_summary": get_team_summary(filters),
        "purchase_orders": get_purchase_orders(filters),
    }


def get_kpis(filters):
    conditions = get_conditions(filters)

    result = frappe.db.sql(
        f"""
        SELECT
            COUNT(DISTINCT po.name) as po_count,
            IFNULL(SUM(po.grand_total), 0) as total_po,
            COUNT(DISTINCT po.supplier) as supplier_count,
            IFNULL(AVG(po.grand_total), 0) as avg_po
        FROM `tabPurchase Order` po
        WHERE po.docstatus = 1
            {conditions}
        """,
        filters,
        as_dict=True,
    )[0]

    return {
        "total_po": result.total_po,
        "po_count": result.po_count,
        "new_suppliers": result.supplier_count,
        "average_po": result.avg_po,
    }


def get_supplier_chart(filters):
    conditions = get_conditions(filters)

    data = frappe.db.sql(
        f"""
        SELECT
            po.name as po_name,
            po.grand_total as value,
            po.supplier as supplier,
            po.owner,
            IFNULL(u.full_name, po.owner) as owner_name
        FROM `tabPurchase Order` po
        LEFT JOIN `tabUser` u ON u.name = po.owner
        WHERE po.docstatus = 1
            {conditions}
        ORDER BY po.grand_total DESC
        """,
        filters,
        as_dict=True,
    )

    if not data:
        return {
            "labels": [],
            "values": [],
            "suppliers": [],
            "creators": [],
            "supplier_colors": {},
        }

    palette = [
        "#7cd6fd", "#743ee2", "#ff5858", "#ffa00a", "#feef72",
        "#28a745", "#dc3545", "#6f42c1", "#fd7e14", "#20c997",
        "#e83e8c", "#17a2b8", "#6610f2", "#ffc107", "#198754",
        "#0d6efd", "#adb5bd", "#d63384", "#6c757d", "#fd7e14",
    ]

    suppliers = sorted(list(set([d.supplier for d in data])))
    supplier_colors = {
        supplier: palette[i % len(palette)]
        for i, supplier in enumerate(suppliers)
    }

    return {
        "labels": [d.po_name for d in data],
        "values": [d.value for d in data],
        "suppliers": [d.supplier for d in data],
        "creators": [d.owner_name for d in data],
        "supplier_colors": supplier_colors,
    }


def get_project_chart(filters):
    conditions = get_conditions(filters)

    data = frappe.db.sql(
        f"""
        SELECT
            po.name as po_name,
            po.grand_total as value,
            COALESCE(NULLIF(po.project, ''), NULLIF(poi.project, ''), '(No Project)') as project_id,
            COALESCE(NULLIF(prj.project_name, ''), NULLIF(po.project, ''), NULLIF(poi.project, ''), '(No Project)') as project_name,
            po.owner,
            IFNULL(u.full_name, po.owner) as owner_name
        FROM `tabPurchase Order` po
        LEFT JOIN `tabPurchase Order Item` poi
            ON poi.parent = po.name AND poi.idx = 1
        LEFT JOIN `tabProject` prj
            ON prj.name = COALESCE(NULLIF(po.project, ''), poi.project)
        LEFT JOIN `tabUser` u ON u.name = po.owner
        WHERE po.docstatus = 1
            {conditions}
        ORDER BY po.grand_total DESC
        """,
        filters,
        as_dict=True,
    )

    if not data:
        return {
            "labels": [],
            "values": [],
            "projects": [],
            "creators": [],
            "project_colors": {},
        }

    palette = [
        "#0d6efd", "#6610f2", "#6f42c1", "#d63384", "#dc3545",
        "#fd7e14", "#ffc107", "#198754", "#20c997", "#17a2b8",
        "#7cd6fd", "#743ee2", "#ff5858", "#ffa00a", "#feef72",
        "#28a745", "#e83e8c", "#adb5bd", "#6c757d", "#fd7e14",
    ]

    # Use project_name for colors and legend
    projects = sorted(list(set([d.project_name for d in data])))
    project_colors = {
        project: palette[i % len(palette)]
        for i, project in enumerate(projects)
    }

    return {
        "labels": [d.po_name for d in data],
        "values": [d.value for d in data],
        "projects": [d.project_name for d in data],
        "project_ids": [d.project_id for d in data],
        "creators": [d.owner_name for d in data],
        "project_colors": project_colors,
    }


def get_team_summary(filters):
    conditions = get_conditions(filters)

    return frappe.db.sql(
        f"""
        SELECT
            IFNULL(u.full_name, po.owner) as team_member,
            COUNT(DISTINCT po.name) as po_count
        FROM `tabPurchase Order` po
        LEFT JOIN `tabUser` u ON u.name = po.owner
        WHERE po.docstatus = 1
            {conditions}
        GROUP BY po.owner, u.full_name
        ORDER BY po_count DESC
        """,
        filters,
        as_dict=True,
    )


def get_purchase_orders(filters):
    conditions = get_conditions(filters)

    return frappe.db.sql(
        f"""
        SELECT
            po.name as po_number,
            po.transaction_date as date,
            po.supplier,
            po.supplier_name,
            po.grand_total,
            po.owner,
            IFNULL(u.full_name, po.owner) as created_by,
            poi.project,
            IFNULL(prj.project_name, poi.project) as project_name
        FROM `tabPurchase Order` po
        LEFT JOIN `tabPurchase Order Item` poi
            ON poi.parent = po.name AND poi.idx = 1
        LEFT JOIN `tabProject` prj
            ON prj.name = poi.project
        LEFT JOIN `tabUser` u
            ON u.name = po.owner
        WHERE po.docstatus = 1
            {conditions}
        GROUP BY po.name
        ORDER BY po.transaction_date DESC
        LIMIT 100
        """,
        filters,
        as_dict=True,
    )


def get_conditions(filters):
    conditions = ""

    if filters.get("company"):
        conditions += " AND po.company = %(company)s"

    if filters.get("year"):
        conditions += " AND YEAR(po.transaction_date) = %(year)s"

    if filters.get("month"):
        conditions += " AND MONTH(po.transaction_date) = %(month)s"

    if filters.get("from_date"):
        conditions += " AND po.transaction_date >= %(from_date)s"

    if filters.get("to_date"):
        conditions += " AND po.transaction_date <= %(to_date)s"

    if filters.get("supplier"):
        conditions += " AND po.supplier = %(supplier)s"

    if filters.get("project"):
        conditions += """
            AND EXISTS (
                SELECT 1
                FROM `tabPurchase Order Item` poi
                WHERE poi.parent = po.name
                  AND poi.project = %(project)s
            )
        """

    if filters.get("owner"):
        conditions += " AND po.owner = %(owner)s"

    return conditions