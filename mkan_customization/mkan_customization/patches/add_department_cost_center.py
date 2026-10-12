import frappe


def execute():
    if not frappe.db.exists("Custom Field", "Department-custom_cost_center") and not frappe.get_meta('Department').get_field('cost_center'):
        frappe.get_doc({
            "doctype": "Custom Field",
            "dt": "Department",
            "label": "Cost Center",
            "fieldname": "cost_center",
            "fieldtype": "Link",
            "options": "Cost Center",
            "insert_after": "parent_department",
        }).insert()