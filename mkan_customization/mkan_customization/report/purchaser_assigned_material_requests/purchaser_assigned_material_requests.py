import frappe
from frappe import _


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        # ---- Material Request ----
        {
            "label": _("Material Request"),
            "fieldname": "mr_name",
            "fieldtype": "Link",
            "options": "Material Request",
            "width": 160,
        },
        {
            "label": _("Assigned To"),
            "fieldname": "assigned_to_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("Transaction Date"),
            "fieldname": "transaction_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": _("Required By"),
            "fieldname": "required_by",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": _("Set Warehouse"),
            "fieldname": "set_warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 160,
        },
        {
            "label": _("MR Workflow State"),
            "fieldname": "mr_workflow_state",
            "fieldtype": "Data",
            "width": 140,
        },

        # ---- Purchase Order ----
        {
            "label": _("Purchase Order"),
            "fieldname": "po_name",
            "fieldtype": "Link",
            "options": "Purchase Order",
            "width": 160,
        },
        {
            "label": _("PO Date"),
            "fieldname": "po_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": _("Project"),
            "fieldname": "project",
            "fieldtype": "Link",
            "options": "Project",
            "width": 140,
        },
        {
            "label": _("Project Name"),
            "fieldname": "project_name",
            "fieldtype": "Data",
            "width": 200,
        },
        {
            "label": _("Supplier Code"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 140,
        },
        {
            "label": _("Supplier Name"),
            "fieldname": "supplier_name",
            "fieldtype": "Data",
            "width": 180,
        },
        {
            "label": _("PO Workflow State"),
            "fieldname": "po_workflow_state",
            "fieldtype": "Data",
            "width": 140,
        },
    ]


def get_data(filters):
    conditions = []
    values = {}

    # ---- Filters ----
    if filters.get("material_request"):
        conditions.append("mr.name = %(material_request)s")
        values["material_request"] = filters["material_request"]

    if filters.get("project"):
        conditions.append("po.project = %(project)s")
        values["project"] = filters["project"]

    if filters.get("purpose"):
        conditions.append("mr.material_request_type = %(purpose)s")
        values["purpose"] = filters["purpose"]

    if filters.get("from_date"):
        conditions.append("mr.transaction_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("mr.transaction_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("assigned_to"):
        conditions.append("""
            EXISTS (
                SELECT 1
                FROM `tabToDo` tdf
                WHERE tdf.reference_type = 'Material Request'
                  AND tdf.reference_name = mr.name
                  AND tdf.owner = %(assigned_to)s
                  AND tdf.status = 'Open'
            )
        """)
        values["assigned_to"] = filters["assigned_to"]

    condition_str = " AND ".join(conditions)

    return frappe.db.sql(f"""
        SELECT
            mr.name AS mr_name,
            u.full_name AS assigned_to_name,
            mr.transaction_date,
            mr.schedule_date AS required_by,
            mr.set_warehouse,
            mr.workflow_state AS mr_workflow_state,

            po.name AS po_name,
            po.transaction_date AS po_date,
            po.project,
            pr.project_name AS project_name,
            po.supplier,
            po.supplier_name,
            po.workflow_state AS po_workflow_state

        FROM `tabMaterial Request` mr

        LEFT JOIN `tabToDo` td
            ON td.reference_type = 'Material Request'
            AND td.reference_name = mr.name
            AND td.status = 'Open'

        LEFT JOIN `tabUser` u
            ON u.name = td.owner

        LEFT JOIN `tabPurchase Order Item` poi
            ON poi.material_request = mr.name

        LEFT JOIN `tabPurchase Order` po
            ON po.name = poi.parent
            AND po.docstatus = 1

        LEFT JOIN `tabProject` pr
            ON pr.name = po.project

        WHERE
            mr.docstatus = 1
            {f"AND {condition_str}" if condition_str else ""}

        ORDER BY
            mr.transaction_date DESC,
            po.transaction_date DESC
    """, values, as_dict=True)
