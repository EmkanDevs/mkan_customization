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


def create_asset_movement(doc, method=None):
    """Create a project transfer after an asset-linked record changes project."""
    previous_doc = doc.get_doc_before_save()
    if not previous_doc or not doc.asset or not doc.project:
        return

    if previous_doc.project == doc.project:
        return

    asset = frappe.db.get_value(
        "Asset", doc.asset, ["custom_project", "company", "location", "department"], as_dict=True
    )
    if not asset or not asset.custom_project or asset.custom_project == doc.project:
        return

    movement = frappe.new_doc("Asset Movement")
    movement.purpose = "Transfer"
    movement.company = asset.company
    movement.reference_doctype = doc.doctype
    movement.reference_name = doc.name

    movement.append("assets", {
        "asset": doc.asset,
        "source_location": asset.location,
        "target_location": asset.location,
        "custom_source_project": asset.custom_project,
        "custom_target_project": doc.project,
        "department": doc.get("department") or asset.department,
    })

    movement.insert(ignore_permissions=True)

    frappe.msgprint(
        f"Asset Movement {movement.name} created for asset {doc.asset}."
    )
