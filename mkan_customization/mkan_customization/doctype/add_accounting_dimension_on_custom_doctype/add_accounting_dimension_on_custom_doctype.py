# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
    create_accounting_dimensions_for_doctype
)
from frappe.model.document import Document


class AddAccountingDimensionOnCustomDoctype(Document):
    pass


def create_client_scripts_for_all_doctypes(doc=None, method=None, doctypes=None):
    if not doctypes:
        try:
            config = frappe.get_single("Add Accounting Dimension On Custom Doctype")
            doctypes = [
                row.custom_doctype
                for row in (config.doctype_list or [])
                if row.custom_doctype
            ]
        except frappe.DoesNotExistError:
            return

    if not doctypes:
        return

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

// Utility function — only update when needed
function update_item_dimensions(frm) {{
    if (!frm.doc.items || !frm.doc.items.length) return;

    const fields_to_sync = [
        'cost_center',
        'sector',
        'scope',
        'section',
        'department',
        'region_location',
        'project'
    ];

    frm.doc.items.forEach(row => {{
        fields_to_sync.forEach(field => {{
            const parent_value = frm.doc[field] || '';

            if ((row[field] || '') !== parent_value) {{
                frappe.model.set_value(
                    row.doctype,
                    row.name,
                    field,
                    parent_value
                );
            }}
        }});
    }});
}}
"""

    for dt in doctypes:
        cs_name = f"{dt} - Sector Scope Linkage"
        code_for_doctype = js_code.format(
            doctype=dt.replace("'", "\\'")
        )

        existing = frappe.db.exists("Client Script", cs_name)

        if existing:
            cs_doc = frappe.get_doc("Client Script", existing)
            if cs_doc.script != code_for_doctype or not cs_doc.enabled:
                cs_doc.script = code_for_doctype
                cs_doc.enabled = 1
                cs_doc.save(ignore_permissions=True)
                frappe.msgprint(f"Updated Client Script for: {dt}")
        else:
            cs_doc = frappe.get_doc({
                "doctype": "Client Script",
                "name": cs_name,
                "dt": dt,
                "script": code_for_doctype,
                "enabled": 1
            })
            cs_doc.insert(ignore_permissions=True)
            frappe.msgprint(f"Created Client Script for: {dt}")


def reorder_accounting_dimension_fields(doc=None, method=None, doctypes=None):
    """
    Reorder accounting dimension fields across predefined doctypes
    in this order: sector → scope → department → section
    """

    if not doctypes:
        try:
            config = frappe.get_single("Add Accounting Dimension On Custom Doctype")
            doctypes = [
                row.custom_doctype
                for row in (config.doctype_list or [])
                if row.custom_doctype
            ]
        except frappe.DoesNotExistError:
            return

    if not doctypes:
        return

    order = [
        ("sector", "accounting_dimensions_section"),
        ("scope", "sector"),
        ("department", "scope"),
        ("section", "department"),
    ]

    modified = {}

    for dt in doctypes:
        meta = frappe.get_meta(dt)
        all_fieldnames = {f.fieldname for f in meta.fields}

        custom_fields_data = frappe.get_all(
            "Custom Field",
            filters={"dt": dt},
            fields=["fieldname"]
        )
        all_fieldnames.update({f.fieldname for f in custom_fields_data})

        if "accounting_dimensions_section" not in all_fieldnames:
            insert_after_section = None

            if "cost_center" in all_fieldnames:
                insert_after_section = "cost_center"
            elif "dimension_col_break" in all_fieldnames:
                insert_after_section = "dimension_col_break"

            frappe.get_doc({
                "doctype": "Custom Field",
                "dt": dt,
                "fieldname": "accounting_dimensions_section",
                "label": "Accounting Dimensions",
                "fieldtype": "Section Break",
                "insert_after": insert_after_section
            }).insert(ignore_permissions=True)

            all_fieldnames.add("accounting_dimensions_section")

        updated_fields = []

        for fieldname, insert_after in order:
            if fieldname not in all_fieldnames:
                continue

            insert_after_final = (
                insert_after if insert_after in all_fieldnames else None
            )

            cf_name = frappe.db.exists(
                "Custom Field",
                {"dt": dt, "fieldname": fieldname}
            )

            if cf_name:
                cf_doc = frappe.get_doc("Custom Field", cf_name)
                if cf_doc.insert_after != insert_after_final:
                    cf_doc.insert_after = insert_after_final
                    cf_doc.save(ignore_permissions=True)
                    updated_fields.append(cf_name)

        if updated_fields:
            modified[dt] = updated_fields
            frappe.clear_cache(doctype=dt)

    if modified:
        frappe.logger().info(
            f"[Accounting Dimension] Reordered fields for {len(modified)} doctypes: {modified}"
        )


def delete_client_scripts_on_dimension_delete(doc, method):
    """
    Deletes all dynamically created Client Scripts if one of the
    Accounting Dimensions (Scope, Section, Department, Sector) is deleted.
    """
    tracked_dimensions = ["Scope", "Section", "Department", "Sector"]

    if doc.accounting_dimension not in tracked_dimensions:
        return

    deleted_count = 0

    try:
        config = frappe.get_single("Add Accounting Dimension On Custom Doctype")
        doctypes = [
            row.custom_doctype
            for row in (config.doctype_list or [])
            if row.custom_doctype
        ]
    except frappe.DoesNotExistError:
        return

    for dt in doctypes:
        cs_name = f"{dt} - Sector Scope Linkage"
        existing = frappe.get_all(
            "Client Script",
            filters={"name": cs_name}
        )

        for e in existing:
            frappe.delete_doc(
                "Client Script",
                e.name,
                ignore_permissions=True,
                force=True
            )
            deleted_count += 1

    frappe.msgprint(
        f"Deleted {deleted_count} Client Scripts linked to Accounting Dimension '{doc.accounting_dimension}'."
    )


@frappe.whitelist()
def add_dimensions_for_custom_doctypes(doctypes=None):
    """
    Reads doctypes from the single doctype
    'Add Accounting Dimension On Custom Doctype'
    """

    if not doctypes:
        try:
            config = frappe.get_single(
                "Add Accounting Dimension On Custom Doctype"
            )
            doctypes = [
                row.custom_doctype
                for row in (config.doctype_list or [])
                if row.custom_doctype
            ]
        except frappe.DoesNotExistError:
            frappe.throw(
                "Setup document 'Add Accounting Dimension On Custom Doctype' not found."
            )

    if isinstance(doctypes, str):
        import json
        doctypes = json.loads(doctypes)

    doctypes = list(dict.fromkeys(filter(None, doctypes)))

    if not doctypes:
        frappe.msgprint("No valid doctypes provided in the list.")
        return

    for dt in doctypes:
        create_accounting_dimensions_for_doctype(dt)
        frappe.msgprint(f"Dimensions created for: {dt}")

    reorder_accounting_dimension_fields(doctypes=doctypes)
    create_client_scripts_for_all_doctypes(doctypes=doctypes)

    frappe.db.commit()
    frappe.msgprint(
        f"Successfully processed {len(doctypes)} doctypes."
    )


@frappe.whitelist()
def remove_dimensions_for_custom_doctypes(doctypes=None):
    """
    Removes accounting dimension custom fields from configured doctypes.
    """

    if not doctypes:
        try:
            config = frappe.get_single(
                "Add Accounting Dimension On Custom Doctype"
            )
            doctypes = [
                row.custom_doctype
                for row in (config.doctype_list or [])
                if row.custom_doctype
            ]
        except frappe.DoesNotExistError:
            frappe.throw(
                "Setup document 'Add Accounting Dimension On Custom Doctype' not found."
            )

    if isinstance(doctypes, str):
        import json
        doctypes = json.loads(doctypes)

    doctypes = list(dict.fromkeys(filter(None, doctypes)))

    if not doctypes:
        frappe.msgprint("No valid doctypes provided in the list.")
        return

    dimensions = frappe.get_all(
        "Accounting Dimension",
        filters={"disabled": 0},
        fields=["fieldname"]
    )
    fieldnames = [d.fieldname for d in dimensions if d.fieldname]

    removed_total = 0

    for dt in doctypes:
        removed_for_dt = 0

        for fieldname in fieldnames:
            cf_name = frappe.db.exists(
                "Custom Field",
                {"dt": dt, "fieldname": fieldname}
            )
            if cf_name:
                frappe.delete_doc(
                    "Custom Field",
                    cf_name,
                    ignore_permissions=True,
                    force=True
                )
                removed_for_dt += 1
                removed_total += 1

        cs_name = f"{dt} - Sector Scope Linkage"
        if frappe.db.exists("Client Script", cs_name):
            frappe.delete_doc(
                "Client Script",
                cs_name,
                ignore_permissions=True,
                force=True
            )

        if removed_for_dt:
            frappe.clear_cache(doctype=dt)

    frappe.msgprint(
        f"Removed {removed_total} accounting dimension fields and associated Client Scripts across {len(doctypes)} doctypes."
    )
