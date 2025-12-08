import frappe

def create_client_scripts_for_all_doctypes(doc, method):
    # List of doctypes to apply the client script
    doctypes = [
        "Leave Encashment", "Payroll Entry", "Expense Taxes and Charges",
        "Expense Claim Detail", "Expense Claim", "Asset Depreciation Schedule",
        "Asset Movement Item", "Payment Request", "Payment Reconciliation Allocation",
        "Payment Reconciliation", "Supplier Quotation Item", "Supplier Quotation",
        "Account Closing Balance", "Subcontracting Receipt Item", "Subcontracting Receipt",
        "Subcontracting Order Item", "Subcontracting Order", "Sales Order", "Purchase Receipt",
        "Purchase Order", "POS Invoice Item", "POS Invoice", "Subscription Plan",
        "Subscription", "Opening Invoice Creation Tool Item", "Opening Invoice Creation Tool",
        "POS Profile", "Stock Reconciliation", "Loyalty Program", "Asset Capitalization",
        "Asset Repair", "Asset Value Adjustment", "Landed Cost Item", "Shipping Rule",
        "Purchase Taxes and Charges", "Sales Taxes and Charges", "Payment Entry Deduction",
        "Stock Entry Detail", "Purchase Receipt Item", "Delivery Note Item", "Material Request Item",
        "Journal Entry Account", "Sales Order Item", "Purchase Order Item", "Purchase Invoice Item",
        "Sales Invoice Item", "Delivery Note", "Budget", "Stock Entry", "Asset", "Payment Entry",
        "Purchase Invoice", "Sales Invoice", "Payment Ledger Entry", "GL Entry","HR Payment Required",
        "Payment Request","Temp Room Booking","Project Site Violation"
    ]

    # JavaScript code for Sector -> Scope linkage
    js_code = """
frappe.ui.form.on('{doctype}', {{
    sector: function(frm) {{
        frm.set_value('scope', '');
        frm.set_query('scope', () => ({{
            filters: {{ sector: frm.doc.sector }}
        }}));
        frm.toggle_display('scope', !!frm.doc.sector);
        update_item_dimensions(frm);
    }},

    department: function(frm) {{
        frm.set_value('section', '');
        frm.set_query('section', () => ({{
            filters: {{ department: frm.doc.department }}
        }}));
        frm.toggle_display('section', !!frm.doc.department);
        update_item_dimensions(frm);
    }},

    scope: update_item_dimensions,
    cost_center: update_item_dimensions,
    section: update_item_dimensions,
    region_location: update_item_dimensions,
    project: update_item_dimensions,

    refresh: function(frm) {{
        if (frm.doc.sector) {{
            frm.set_query('scope', () => ({{
                filters: {{ sector: frm.doc.sector }}
            }}));
        }}

        if (frm.doc.department) {{
            frm.set_query('section', () => ({{
                filters: {{ department: frm.doc.department }}
            }}));
        }}

        frm.toggle_display('scope', !!frm.doc.sector);
        frm.toggle_display('section', !!frm.doc.department);
    }}
}});

// ✅ Fixed: Utility function — only update when needed
function update_item_dimensions(frm) {{
    if (!frm.doc.items || !frm.doc.items.length) return;

    const fields_to_sync = [
        'scope',
        'cost_center',
        'sector',
        'section',
        'department',
        'region_location',
        'project'
    ];

    frm.doc.items.forEach(row => {{
        fields_to_sync.forEach(field => {{
            const parent_value = frm.doc[field] || '';

            // ✅ Only set if different
            if ((row[field] || '') !== parent_value) {{
                frappe.model.set_value(row.doctype, row.name, field, parent_value);
            }}
        }});
    }});
}}
"""

    # Loop through all doctypes
    for dt in doctypes:
        cs_name = f"{dt} - Sector Scope Linkage"
        code_for_doctype = js_code.format(doctype=dt.replace("'", "\\'"))  # escape quotes

        # Check if Client Script already exists
        existing = frappe.get_all("Client Script", filters={"name": cs_name}, limit=1)
        if existing:
            cs_doc = frappe.get_doc("Client Script", existing[0].name)
            cs_doc.script = code_for_doctype
            cs_doc.save()
        else:
            cs_doc = frappe.get_doc({
                "doctype": "Client Script",
                "name": cs_name,
                "dt": dt,
                "script": code_for_doctype,
                "enabled": 1
            })
            cs_doc.insert(ignore_permissions=True)


def reorder_accounting_dimension_fields(doc, method):
    """
    Reorder accounting dimension fields across predefined doctypes
    in this order: sector → scope → department → section
    """

    doctypes = [
        "Leave Encashment", "Payroll Entry", "Expense Taxes and Charges",
        "Expense Claim Detail", "Expense Claim", "Asset Depreciation Schedule",
        "Asset Movement Item", "Payment Request", "Payment Reconciliation Allocation",
        "Payment Reconciliation", "Supplier Quotation Item", "Supplier Quotation",
        "Account Closing Balance", "Subcontracting Receipt Item", "Subcontracting Receipt",
        "Subcontracting Order Item", "Subcontracting Order", "Sales Order", "Purchase Receipt",
        "Purchase Order", "POS Invoice Item", "POS Invoice", "Subscription Plan",
        "Subscription", "Opening Invoice Creation Tool Item", "Opening Invoice Creation Tool",
        "POS Profile", "Stock Reconciliation", "Loyalty Program", "Asset Capitalization",
        "Asset Repair", "Asset Value Adjustment", "Landed Cost Item", "Shipping Rule",
        "Purchase Taxes and Charges", "Sales Taxes and Charges", "Payment Entry Deduction",
        "Stock Entry Detail", "Purchase Receipt Item", "Delivery Note Item", "Material Request Item",
        "Journal Entry Account", "Sales Order Item", "Purchase Order Item", "Purchase Invoice Item",
        "Sales Invoice Item", "Delivery Note", "Budget", "Stock Entry", "Asset", "Payment Entry",
        "Purchase Invoice", "Sales Invoice", "Payment Ledger Entry", "GL Entry","HR Payment Required",
        "Payment Request","Temp Room Booking","Project Site Violation"
    ]

    # desired order (fieldname, insert_after)
    order = [
        ("sector", "dimension_col_break"),
        ("scope", "sector"),
        ("department", "scope"),
        ("section", "department"),
    ]

    modified = {}

    for dt in doctypes:
        existing_fields = {
            f.fieldname for f in frappe.get_all("Custom Field", filters={"dt": dt}, fields=["fieldname"])
        }

        updated_fields = []
        for fieldname, insert_after in order:
            # Skip if this field doesn’t exist
            if fieldname not in existing_fields:
                continue

            # ✅ Always treat dimension_col_break as valid even if not in custom fields
            if insert_after == "dimension_col_break" or insert_after in existing_fields:
                insert_after_final = insert_after
            else:
                insert_after_final = None

            custom_fields = frappe.get_all(
                "Custom Field",
                filters={"dt": dt, "fieldname": fieldname},
                fields=["name", "insert_after"],
            )

            for cf in custom_fields:
                if cf.insert_after != insert_after_final:
                    frappe.db.set_value(
                        "Custom Field",
                        cf.name,
                        "insert_after",
                        insert_after_final,
                        update_modified=False,
                    )
                    updated_fields.append(cf.name)

        if updated_fields:
            modified[dt] = updated_fields
            frappe.clear_cache(doctype=dt)

    if modified:
        frappe.logger().info(f"[Accounting Dimension] Reordered fields for {len(modified)} doctypes: {modified}")

        
def delete_client_scripts_on_dimension_delete(doc, method):
    """
    Deletes all dynamically created Client Scripts if one of the
    Accounting Dimensions (Scope, Section, Department, Sector) is deleted.
    """
    tracked_dimensions = ["Scope", "Section", "Department", "Sector"]

    if doc.accounting_dimension not in tracked_dimensions:
        return

    doctypes = [
        "Leave Encashment", "Payroll Entry", "Expense Taxes and Charges",
        "Expense Claim Detail", "Expense Claim", "Asset Depreciation Schedule",
        "Asset Movement Item", "Payment Request", "Payment Reconciliation Allocation",
        "Payment Reconciliation", "Supplier Quotation Item", "Supplier Quotation",
        "Account Closing Balance", "Subcontracting Receipt Item", "Subcontracting Receipt",
        "Subcontracting Order Item", "Subcontracting Order", "Sales Order", "Purchase Receipt",
        "Purchase Order", "POS Invoice Item", "POS Invoice", "Subscription Plan",
        "Subscription", "Opening Invoice Creation Tool Item", "Opening Invoice Creation Tool",
        "POS Profile", "Stock Reconciliation", "Loyalty Program", "Asset Capitalization",
        "Asset Repair", "Asset Value Adjustment", "Landed Cost Item", "Shipping Rule",
        "Purchase Taxes and Charges", "Sales Taxes and Charges", "Payment Entry Deduction",
        "Stock Entry Detail", "Purchase Receipt Item", "Delivery Note Item", "Material Request Item",
        "Journal Entry Account", "Sales Order Item", "Purchase Order Item", "Purchase Invoice Item",
        "Sales Invoice Item", "Delivery Note", "Budget", "Stock Entry", "Asset", "Payment Entry",
        "Purchase Invoice", "Sales Invoice", "Payment Ledger Entry", "GL Entry","HR Payment Required",
        "Payment Request","Temp Room Booking","Project Site Violation"
    ]

    deleted_count = 0

    for dt in doctypes:
        cs_name = f"{dt} - Sector Scope Linkage"
        existing = frappe.get_all("Client Script", filters={"name": cs_name})
        for e in existing:
            frappe.delete_doc("Client Script", e.name, ignore_permissions=True, force=True)
            deleted_count += 1

    frappe.msgprint(f"✅ Deleted {deleted_count} Client Scripts linked to Accounting Dimension '{doc.accounting_dimension}'.")
