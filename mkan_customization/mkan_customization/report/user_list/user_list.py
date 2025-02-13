import frappe

def execute(filters=None):
    columns = [
        {"label": "User", "fieldname": "user", "fieldtype": "Link", "options": "User", "width": 200},
        {"label": "Full Name", "fieldname": "_full_name", "fieldtype": "Data", "width": 200},
        {"label": "Role", "fieldname": "role", "fieldtype": "Link", "options": "Role", "width": 200},
        {"label": "Allow Doctype", "fieldname": "doctype", "fieldtype": "Link", "options": "DocType", "width": 200},
        {"label":"For Value","fieldname": "for_value","fieldtype": "Dynamic Link","options": "doctype","width": 220,
		},
    ]

    query = """
    SELECT 
        u.name AS user, 
        u.full_name as _full_name, 
        hr.role, 
        up.allow AS doctype,
        up.for_value
    FROM `tabUser` u
    LEFT JOIN `tabHas Role` hr ON u.name = hr.parent
    LEFT JOIN `tabUser Permission` up ON u.name = up.user
    WHERE u.enabled = 1
    """

    params = []
    if filters:
        if filters.get('user'):
            query += " AND u.name = %s"
            params.append(filters['user'])
        if filters.get('role'):
            query += " AND hr.role = %s"
            params.append(filters['role'])

    query += " ORDER BY u.name"
    data = frappe.db.sql(query, params, as_dict=True)

    return columns, data
