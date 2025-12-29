import frappe
from frappe.utils import getdate


# Stock reports to be restricted during freeze period
STOCK_REPORTS = {
    "Stock Ledger",
    "Stock Ledger Extended",
    "Stock Ledger V2",
    "Stock Balance",
    "Stock Balance With Cash",
    "Stock Projected Qty",
    "Stock Summary",
    "Stock Ageing",
    "Item Price Stock",
    "Warehouse Wise Stock Balance",
    "Material Transfers - Report",
    "Stock Analytics",
    "Stock Analysis Custom",
    "Delivery Note Trends",
    "Purchase Receipt Trends",
    "Sales Order Analysis",
    "Purchase Order Analysis",
    "Purchase Order Analysis 2",
    "Item Shortage Report",
    "Batch-Wise Balance History",
    "Material Inward & Outward",
    "Material Request Transfers Report",
    "Item-wise PO and PR History",
    "Warehouse wise Item Balance Age and Value",
    "Warehouse Receipt wise Item Expiration",
}


def has_report_permission(doc, ptype, user):
    """
    Hook for has_permission on 'Report' doctype.
    Blocks access to stock reports during the freeze period for non-authorized roles.
    """
    if user == "Administrator":
        return True

    # Check if the report is in our restricted list
    report_name = doc.name if isinstance(doc, frappe.model.document.Document) else doc
    if report_name not in STOCK_REPORTS:
        return None  # Let standard permissions handle it

    # Check if we're in the freeze period
    today = getdate()
    if getdate("2025-12-29") <= today <= getdate("2025-12-31"):
        user_roles = frappe.get_roles(user)
        allowed_roles = {"Warehouse Manager", "Finance Manager"}
        
        # If user doesn't have allowed roles, deny access
        if not allowed_roles.intersection(set(user_roles)):
            return False

    return None


def check_report_access(doc, method=None):
    """
    Onload hook for 'Report' doctype.
    Providing a better error message when user attempts to open the report via Form view.
    """
    if frappe.session.user == "Administrator":
        return
    
    today = getdate()

    if doc.doctype != "Report":
        return

    if doc.name not in STOCK_REPORTS:
        return

    # Check if we're in the freeze period
    if getdate("2025-12-29") <= today <= getdate("2025-12-31"):
        user_roles = frappe.get_roles(frappe.session.user)
        allowed_roles = {"Warehouse Manager", "Finance Manager"}
        
        has_allowed_role = bool(allowed_roles.intersection(set(user_roles)))
        
        if not has_allowed_role:
            frappe.throw(
                f"Access to '{doc.name}' is restricted during the freeze period (Dec 29-31, 2025). "
                "Only Warehouse Manager and Accounts Manager roles can access this report.",
                frappe.PermissionError,
            )

