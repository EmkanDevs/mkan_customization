import frappe
from mkan_customization.mkan_customization.override.asset import get_asset_project, get_asset_department

def set_target_project(doc, method=None):
    if doc.purpose == "Receipt":
        for row in doc.assets:
            if row.asset and not row.custom_target_project:
                row.custom_target_project = frappe.db.get_value("Asset", row.asset, "custom_project")
    for row in doc.assets:
        if row.asset and not row.department:
            row.department = frappe.db.get_value("Asset", row.asset, "department")

def update_asset_project(doc, method=None):
    for row in doc.assets:
        if not row.asset:
            continue
        project = get_asset_project(row.asset)
        if project:
            frappe.db.set_value("Asset", row.asset, "custom_project", project, update_modified=False)
        department = get_asset_department(row.asset)
        if department:
            frappe.db.set_value("Asset", row.asset, "department", department, update_modified=False)