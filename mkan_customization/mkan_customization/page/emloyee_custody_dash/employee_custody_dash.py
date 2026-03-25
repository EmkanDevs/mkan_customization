import frappe
from frappe.utils import nowdate

@frappe.whitelist()
def get_it_assets(employee, active_only=0):
    condition = ""
    values = {"employee": employee}

    if int(active_only):
        condition += " AND (child.to_date IS NULL OR child.to_date >= %(today)s)"
        values["today"] = nowdate()

    data = frappe.db.sql(f"""
        SELECT
            iam.asset_local_code AS asset_id,
            iam.item,
            iam.item_name,
            iam.item_group,
            iam.manufacturer,
            child.from_date,
            child.to_date
        FROM `tabIT Asset Management` iam
        INNER JOIN `tabIT Asset Assigned User2` child
            ON child.parent = iam.name
        WHERE child.assigned_user = %(employee)s
        {condition}
        ORDER BY child.from_date DESC
    """, values, as_dict=True)

    return data


@frappe.whitelist()
def get_sim_cards(employee, active_only=0):
    condition = ""
    values = {"employee": employee}

    # ✅ Apply Active filter on status
    if int(active_only):
        condition += " AND sim.status = 'In Use'"

    data = frappe.db.sql(f"""
        SELECT
            sim.name AS sim_id,
            sim.service_no,
            sim.serial_number,
            sim.reason_of_purchase,
            sim.sim_provider,
            sim.status,
            child.from_date,
            child.to_date
        FROM `tabSIM Management` sim
        INNER JOIN `tabSIM Assigned User` child
            ON child.parent = sim.name
        WHERE child.assigned_user = %(employee)s
        {condition}
        ORDER BY child.from_date DESC
    """, values, as_dict=True)

    return data


@frappe.whitelist()
def get_vehicles(employee):
    data = frappe.db.sql("""
        SELECT
            v.name AS vehicle_id,
            v.tags,
            v.license_plate,
            v.door_number,
            v.vehicle_types,
            v.model_year
        FROM `tabVehicles` v
        WHERE v.driver = %s
        ORDER BY v.modified DESC
    """, (employee,), as_dict=True)

    return data


@frappe.whitelist()
def get_employee_custody(employee=None):
    condition = ""
    values = {}

    if employee:
        condition = "AND emp.name = %(employee)s"
        values["employee"] = employee

    data = frappe.db.sql(f"""
        SELECT
            emp.name AS employee,
            emp.employee_name,
            emp.department,

            IFNULL(adv.total_advance, 0) 
            - IFNULL(exp.total_expense, 0) AS pending_amount

        FROM `tabEmployee` emp

        LEFT JOIN (
            SELECT employee, SUM(paid_amount) AS total_advance
            FROM `tabEmployee Advance`
            WHERE docstatus = 1
            GROUP BY employee
        ) adv ON adv.employee = emp.name

        LEFT JOIN (
            SELECT employee, SUM(total_claimed_amount) AS total_expense
            FROM `tabExpense Claim`
            WHERE docstatus = 1
            GROUP BY employee
        ) exp ON exp.employee = emp.name

        WHERE 
            (IFNULL(adv.total_advance, 0) 
            - IFNULL(exp.total_expense, 0)) != 0
            {condition}

        ORDER BY pending_amount DESC
    """, values, as_dict=True)

    return data