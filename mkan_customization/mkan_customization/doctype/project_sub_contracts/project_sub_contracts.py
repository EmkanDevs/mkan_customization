import frappe
from frappe.model.document import Document
from frappe.utils import add_days, nowdate
from frappe.model.mapper import get_mapped_doc
from frappe.utils import get_url_to_form
from frappe.utils import flt

class ProjectSubContracts(Document):
    def on_submit(self):
        version_0_items = [
            row.requirement for row in self.fulfilment_terms
            if str(row.custom_version).strip() == '0'
        ]
        if version_0_items:
            supplier = self.party_name
            # create_po(version_0_items, supplier, self.project, self.name, 0)


@frappe.whitelist()
def complete_contract(docname):
    doc = frappe.get_doc("Project Sub-Contracts", docname)

    if doc.completed_contract:
        return {"skipped": True, "reason": "Contract already marked as completed."}

    child_field = frappe.get_meta("Project Sub-Contracts").get_field("fulfilment_terms")
    child_doctype = child_field.options if child_field else "Contract Fulfilment Checklist"

    changes = []

    for row in doc.fulfilment_terms:
        if row.custom_wbs and flt(row.custom_quantity):
            wbs_name = row.custom_wbs
            try:
                wbs = frappe.db.get_value(
                    "WBS item",
                    wbs_name,
                    ["consumed_quantity", "qty"],
                    as_dict=True
                )

                old_qty = flt(wbs.consumed_quantity or 0.0)
                boq_qty = flt(wbs.qty or 0.0)
                add_qty = flt(row.custom_quantity or 0.0)
                new_qty = old_qty + add_qty

                if new_qty > boq_qty:
                    frappe.throw(
                        f"Consumed Quantity is greater than the BOQ quantity "
                        f"in the WBS item {wbs_name}."
                    )

                frappe.db.set_value(
                    "WBS item",
                    wbs_name,
                    "consumed_quantity",
                    new_qty,
                    update_modified=True
                )

                frappe.db.set_value(
                    child_doctype,
                    row.name,
                    "custom_quantity",
                    0,
                    update_modified=True
                )

                changes.append({
                    "wbs": wbs_name,
                    "child_row": row.name,
                    "old_consumed": old_qty,
                    "added": add_qty,
                    "new_consumed": new_qty
                })

            except frappe.ValidationError:
                raise
            except Exception:
                frappe.log_error(
                    f"Error updating WBS {wbs_name} for parent {docname}: {frappe.get_traceback()}",
                    "Contract Update Failed"
                )

    frappe.db.set_value(
        "Project Sub-Contracts",
        docname,
        "completed_contract",
        1,
        update_modified=True
    )

    frappe.db.commit()
    return {"skipped": False, "changes": changes}


@frappe.whitelist()
def create_multiple_purchase_orders(docname, version, supplier=None):
    try:
        version = str(version).strip()
        doc = frappe.get_doc("Project Sub-Contracts", docname)

        if not supplier:
            supplier = doc.party_name

        matching_items_version = [
            row.requirement for row in doc.fulfilment_terms
            if str(row.custom_version).strip() == version
        ]

        if not matching_items_version:
            frappe.throw(f"No requirements found with version = {version}.")

        # Check for existing PO before creating
        existing_po = frappe.get_all("Purchase Order", filters={
            "custom_project_sub_contract": doc.name,
            "version": version,
            "is_project_sub_contracting": 1,
            "docstatus": ["<", 2]  # Optional: draft/submitted
        }, pluck="name")

        if existing_po:
            po_link = f'<a href="/app/purchase-order/{existing_po[0]}" target="_blank">{existing_po[0]}</a>'
            frappe.throw(f"A Purchase Order already exists for this version: {po_link}")

        # No existing PO, so create
        po_name_version = create_po(matching_items_version, supplier, doc.project, doc.name, version)
        return [po_name_version]

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "PO Creation Failed")
        raise e

def create_po(item_codes, supplier, project, name, version):
    po = frappe.new_doc("Purchase Order")
    po.supplier = supplier
    po.project = project
    po.custom_project_sub_contract = name
    po.is_project_sub_contracting = 1
    po.version = version

    for item_code in item_codes:
        item = frappe.get_doc("Item", item_code)
        po.append("items", {
            "item_code": item.item_code,
            "item_name": item.item_name,
            "uom": item.stock_uom,
            "qty": 1,
            "schedule_date": add_days(nowdate(), 2)
        })

    po.insert(ignore_permissions=True)
    po.save()
    return po.name

@frappe.whitelist()
def create_work_progress_report(doc_name):
    # Fetch the parent document
    sub_contract = frappe.get_doc("Project Sub-Contracts", doc_name)

    # Create a new Work Progress Report document
    wpr = frappe.new_doc("Work Progress Report")
    wpr.project = sub_contract.project
    wpr.start_date = sub_contract.start_date
    wpr.end_date = sub_contract.end_date
    wpr.project_code = sub_contract.project_number
    wpr.cost_code = sub_contract.cost_center
    wpr.sub_contractor = sub_contract.party_name

    # Fetch child table entries from fulfilment_terms
    for ft in sub_contract.fulfilment_terms:
        item_code = ft.requirement
        item_name = ft.requirement_label
        notes = ft.notes

        # Get UOM from Item doctype
        uom = ""
        if item_code:
            item_doc = frappe.get_doc("Item", item_code)
            uom = item_doc.stock_uom

        # Append to Work Progress Report's child table
        wpr.append("work_progress_detail", {
            "item": item_code,
            "item_code": item_name,
            "uom": uom,
            "site_engineer_or_supervisor_notes": notes
        })

    # Save the new document
    wpr.insert(ignore_permissions=True)
    frappe.msgprint(f"Work Progress Report {wpr.name} created.")
    return wpr.name

@frappe.whitelist()
def work_progress_report_map(source_name):
    # Step 1: Get all used versions
    used_versions = frappe.db.sql("""
        SELECT DISTINCT version
        FROM `tabWork Progress Detail`
        WHERE parenttype = 'Work Progress Report'
          AND parent IN (
              SELECT name FROM `tabWork Progress Report`
              WHERE project_sub_contracts = %s
          )
    """, (source_name,), as_list=True)
    used_versions = {v[0] for v in used_versions}

    # Step 2: Get all available versions
    all_versions = frappe.db.sql("""
        SELECT DISTINCT custom_version
        FROM `tabContract Fulfilment Checklist`
        WHERE parent = %s
          AND custom_version IS NOT NULL
        ORDER BY custom_version ASC
    """, (source_name,), as_list=True)
    all_versions = [v[0] for v in all_versions]

    # Step 3: Pick the smallest unused version
    next_version = None
    for v in all_versions:
        if v not in used_versions:
            next_version = v
            break

    if next_version is None:
        frappe.throw("All versions from the checklist have already been used.")

    # Step 4: Mapping logic
    def postprocess(source_doc, target_doc):
        target_doc.cost_code = source_doc.business_code__cost_center
        target_doc.sub_contractor = source_doc.party_name
        target_doc.start_date = source_doc.start_date
        target_doc.end_date = source_doc.end_date
        target_doc.naming_series = "CONTR-"
        target_doc.project_code = frappe.db.get_value("Project", source_doc.project, "custom_project_code")
        target_doc.version = next_version  # Optional: Store version on report

    # Step 5: Use captured version in lambda
    doc = get_mapped_doc(
        "Project Sub-Contracts",
        source_name,
        {
            "Project Sub-Contracts": {
                "doctype": "Work Progress Report",
                "validation": {
                    "docstatus": ["=", 1]
                }
            },
            "Contract Fulfilment Checklist": {
                "doctype": "Work Progress Detail",
                "field_map": {
                    "requirement": "item",
                    "custom_requirement_label": "item_code",
                    "custom_version":"version"
                },
                "add_if_empty": True,
                "condition": lambda d: d.custom_version == next_version
            }
        },
        postprocess=postprocess
    )

    return doc.as_dict()



def get_next_version(source_name):
    """Helper function to determine the next version to map."""
    used_versions = frappe.db.sql("""
        SELECT DISTINCT version
        FROM `tabWork Progress Detail`
        WHERE parenttype = 'Work Progress Report'
          AND parent IN (
              SELECT name FROM `tabWork Progress Report`
              WHERE project_sub_contracts = %s
          )
    """, (source_name,), as_list=True)
    used_versions = {v[0] for v in used_versions}

    all_versions = frappe.db.sql("""
        SELECT DISTINCT custom_version
        FROM `tabContract Fulfilment Checklist`
        WHERE parent = %s
          AND custom_version IS NOT NULL
        ORDER BY custom_version ASC
    """, (source_name,), as_list=True)
    all_versions = [v[0] for v in all_versions]

    for v in all_versions:
        if v not in used_versions:
            return v

    frappe.throw("All versions from the checklist have already been used.")


@frappe.whitelist()
def invoice_released_memo_map(source_name):
    # Step 1: Get used versions in Invoice Released Memo
    used_versions = frappe.db.sql("""
        SELECT DISTINCT version
        FROM `tabInvoice released memo detail`
        WHERE parenttype = 'Invoice released Memo'
          AND parent IN (
              SELECT name FROM `tabInvoice released Memo`
              WHERE project_sub_contracts = %s
          )
    """, (source_name,), as_list=True)
    used_versions = {v[0] for v in used_versions}

    # Step 2: Get available versions from Contract Fulfilment Checklist
    all_versions = frappe.db.sql("""
        SELECT DISTINCT custom_version
        FROM `tabContract Fulfilment Checklist`
        WHERE parent = %s
          AND custom_version IS NOT NULL
        ORDER BY custom_version ASC
    """, (source_name,), as_list=True)
    all_versions = [v[0] for v in all_versions]

    # Step 3: Pick the smallest unused version
    next_version = None
    for v in all_versions:
        if v not in used_versions:
            next_version = v
            break

    if next_version is None:
        frappe.throw("All versions from the checklist have already been used for Invoice Release Memo.")

    # Step 4: Postprocess to set header fields + version
    def postprocess(source_doc, target_doc):
        target_doc.cost_code = source_doc.business_code__cost_center
        target_doc.vendor = source_doc.party_name
        target_doc.naming_series = "CONTR-"
        target_doc.created_from = "Project Sub Contracts"
        target_doc.start_date = source_doc.start_date
        target_doc.end_date = source_doc.end_date
        target_doc.project_no = source_doc.project
        target_doc.project_code = source_doc.project_number
        target_doc.vate_rate = source_doc.vat_rate
        target_doc.version = next_version   # ✅ set version on parent

    # Step 5: Mapping logic with version condition
    doc = get_mapped_doc(
        "Project Sub-Contracts",
        source_name,
        {
            "Project Sub-Contracts": {
                "doctype": "Invoice released Memo",
                "validation": {
                    "docstatus": ["=", 1]
                }
            },
            "Contract Fulfilment Checklist": {
                "doctype": "Invoice released memo detail",
                "field_map": {
                    "requirement": "item",
                    "custom_requirement_label": "item_name",
                    "custom_version": "version"
                },
                "add_if_empty": True,
                "condition": lambda d: d.custom_version == next_version
            }
        },
        postprocess=postprocess
    )

    return doc.as_dict()


@frappe.whitelist()
def fetch_po_wpr_ipm(project_sub_contracts):
    # get Purchase Order, Work Progress Report and Invoice Released Memo that are linked to Project Sub-Contracts
    
    po = frappe.get_all(
        "Purchase Order", 
        filters={"custom_project_sub_contract": project_sub_contracts}, 
        fields=[
            "custom_project_sub_contract", "name", "supplier", "workflow_state",
            "per_billed", "per_received", "transaction_date", "grand_total",
            "advance_paid", "version", "docstatus"
        ]
    )
    wpr = frappe.get_all(
        "Work Progress Report", 
        filters={"project_sub_contracts": project_sub_contracts}, 
        fields=[
            "project_sub_contracts", "name", "version", "business_type",
            "start_date", "end_date", "project", "sub_contractor", "docstatus"
        ]
    )
    irm = frappe.get_all(
        "Invoice released Memo", 
        filters={"project_sub_contracts": project_sub_contracts}, 
        fields=[
            "project_sub_contracts", "name", "discpline", "invoice_no", "invoice_date",
            "start_date", "end_date", "project_no", "vendor", "client", "version", "docstatus"
        ]
    )

    if not po and not wpr and not irm:
        return "<p style='color: red;'>No linked records found.</p>"

    # Helper to translate docstatus
    def get_status_label(status):
        return {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(status, "Unknown")

    max_length = max(len(po), len(wpr), len(irm))

    html = """
    <div style="border:1px solid #ccc; border-radius:5px;">
        <table width="100%" style="border-collapse: collapse;">
            <thead>
                <tr style="color:brown">
                    <th width="33%" style="border:1px solid #ccc; padding:8px">Purchase Order</th>
                    <th width="33%" style="border:1px solid #ccc; padding:8px">Work Progress Report</th>
                    <th width="33%" style="border:1px solid #ccc; padding:8px">Invoice Released Memo</th>
                </tr>
            </thead>
            <tbody>
    """

    for i in range(max_length):
        html += "<tr>"

        # Purchase Order
        if i < len(po):
            row = po[i]
            link = get_url_to_form("Purchase Order", row.name)
            html += f"""
                <td width="33%" style="border:1px solid #ccc; padding:8px;">
                    <b>Project Sub-Contracts:</b> {row.custom_project_sub_contract}<br>
                    <b>ID:</b> <a href="{link}" target="_blank" style="color:#0070cc; text-decoration: underline; font-weight: bold;">{row.name}</a><br>
                    <b>Status:</b> {get_status_label(row.docstatus)}<br>
                    <b>Supplier Name:</b> {row.supplier}<br>
                    <b>Workflow Status:</b> {row.workflow_state}<br>
                    <b>% Billed:</b> {row.per_billed}<br>
                    <b>Amount Paid:</b> {(row.grand_total * row.per_billed)/100}<br>
                    <b>% Received:</b> {row.per_received}<br>
                    <b>Date:</b> {row.transaction_date}<br>
                    <b>Grand Total:</b> {row.grand_total}<br>
                    <b>Advance Paid:</b> {row.advance_paid}<br>
                    <b>Version:</b> {row.version}<br>
                </td>
            """
        else:
            html += "<td style='border:1px solid #ccc; padding:8px;'></td>"

        # Work Progress Report
        if i < len(wpr):
            row = wpr[i]
            link = get_url_to_form("Work Progress Report", row.name)
            html += f"""
                <td width="33%" style="border:1px solid #ccc; padding:8px;">
                    <b>Project Sub-Contracts:</b> {row.project_sub_contracts}<br>
                    <b>ID:</b> <a href="{link}" target="_blank" style="color:#0070cc; text-decoration: underline; font-weight: bold;">{row.name}</a><br>
                    <b>Status:</b> {get_status_label(row.docstatus)}<br>
                    <b>Sequence:</b> {row.version}<br>
                    <b>Business Type:</b> {row.business_type}<br>
                    <b>Start Date:</b> {row.start_date}<br>
                    <b>End Date:</b> {row.end_date}<br>
                    <b>Project Name:</b> {row.project}<br>
                    <b>Sub-Contractor:</b> {row.sub_contractor}
                </td>
            """
        else:
            html += "<td style='border:1px solid #ccc; padding:8px;'></td>"

        # Invoice Released Memo
        if i < len(irm):
            row = irm[i]
            link = get_url_to_form("Invoice released Memo", row.name)
            html += f"""
                <td width="33%" style="border:1px solid #ccc; padding:8px;">
                    <b>Project Sub-Contracts:</b> {row.project_sub_contracts}<br>
                    <b>ID:</b> <a href="{link}" target="_blank" style="color:#0070cc; text-decoration: underline; font-weight: bold;">{row.name}</a><br>
                    <b>Status:</b> {get_status_label(row.docstatus)}<br>
                    <b>Sequence:</b> {row.version}<br>
                    <b>Discipline:</b> {row.discpline}<br>
                    <b>Invoice No.:</b> {row.invoice_no}<br>
                    <b>Invoice Date:</b> {row.invoice_date}<br>
                    <b>Start Date:</b> {row.start_date}<br>
                    <b>End Date:</b> {row.end_date}<br>
                    <b>Project Name:</b> {row.project_no}<br>
                    <b>Vendor:</b> {row.vendor}<br>
                    <b>Client:</b> {row.client}
                </td>
            """
        else:
            html += "<td style='border:1px solid #ccc; padding:8px;'></td>"

        html += "</tr>"

    html += """
            </tbody>
        </table>
    </div>
    """
    return html


@frappe.whitelist()
def fetch_so_wpr_irm(sales_order):
    # get Work Progress Reports linked to Sales Order
    wpr = frappe.get_all(
        "Work Progress Report",
        filters={"sales_order": sales_order},
        fields=[
            "name", "version", "business_type", "start_date", "end_date",
            "project", "sub_contractor", "docstatus"
        ]
    )

    # get Invoice Released Memo linked to Sales Order
    irm = frappe.get_all(
        "Invoice released Memo",
        filters={"sales_order": sales_order},
        fields=[
            "name", "discpline", "invoice_no", "invoice_date", "start_date",
            "end_date", "project_no", "vendor", "client", "version", "docstatus"
        ]
    )

    if not wpr and not irm:
        return "<p style='color: red;'>No linked Work Progress Reports or Invoice Released Memos found.</p>"

    # Helper for docstatus
    def get_status_label(status):
        return {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(status, "Unknown")

    max_length = max(len(wpr), len(irm))

    html = """
    <div style="border:1px solid #ccc; border-radius:5px;">
        <table width="100%" style="border-collapse: collapse;">
            <thead>
                <tr style="color:brown">
                    <th width="50%" style="border:1px solid #ccc; padding:8px">Work Progress Report</th>
                    <th width="50%" style="border:1px solid #ccc; padding:8px">Invoice Released Memo</th>
                </tr>
            </thead>
            <tbody>
    """

    for i in range(max_length):
        html += "<tr>"

        # Work Progress Report
        if i < len(wpr):
            row = wpr[i]
            link = get_url_to_form("Work Progress Report", row.name)
            html += f"""
                <td style="border:1px solid #ccc; padding:8px;">
                    <b>ID:</b> <a href="{link}" target="_blank" style="color:#0070cc; font-weight: bold;">{row.name}</a><br>
                    <b>Status:</b> {get_status_label(row.docstatus)}<br>
                    <b>Sequence:</b> {row.version}<br>
                    <b>Business Type:</b> {row.business_type}<br>
                    <b>Start Date:</b> {row.start_date}<br>
                    <b>End Date:</b> {row.end_date}<br>
                    <b>Project:</b> {row.project}<br>
                    <b>Sub-Contractor:</b> {row.sub_contractor}
                </td>
            """
        else:
            html += "<td style='border:1px solid #ccc; padding:8px;'></td>"

        # Invoice Released Memo
        if i < len(irm):
            row = irm[i]
            link = get_url_to_form("Invoice released Memo", row.name)
            html += f"""
                <td style="border:1px solid #ccc; padding:8px;">
                    <b>ID:</b> <a href="{link}" target="_blank" style="color:#0070cc; font-weight: bold;">{row.name}</a><br>
                    <b>Status:</b> {get_status_label(row.docstatus)}<br>
                    <b>Sequence:</b> {row.version}<br>
                    <b>Discipline:</b> {row.discpline}<br>
                    <b>Invoice No:</b> {row.invoice_no}<br>
                    <b>Invoice Date:</b> {row.invoice_date}<br>
                    <b>Start Date:</b> {row.start_date}<br>
                    <b>End Date:</b> {row.end_date}<br>
                    <b>Project No:</b> {row.project_no}<br>
                    <b>Vendor:</b> {row.vendor}<br>
                    <b>Client:</b> {row.client}
                </td>
            """
        else:
            html += "<td style='border:1px solid #ccc; padding:8px;'></td>"

        html += "</tr>"

    html += """
            </tbody>
        </table>
    </div>
    """
    return html


@frappe.whitelist()
def jinja_data(project_sub_contracts):
    po = frappe.get_all("Purchase Order", 
        filters={"custom_project_sub_contract": project_sub_contracts}, 
        fields=["custom_project_sub_contract", "name", "supplier", "workflow_state", "per_billed", "per_received",
                "transaction_date", "grand_total", "advance_paid", "version"]
    )
    wpr = frappe.get_all("Work Progress Report", 
        filters={"project_sub_contracts": project_sub_contracts}, 
        fields=["project_sub_contracts", "name", "version", "business_type", "start_date", "end_date", "project", "sub_contractor"]
    )
    irm = frappe.get_all("Invoice released Memo", 
        filters={"project_sub_contracts": project_sub_contracts}, 
        fields=["project_sub_contracts", "name",  "discpline", "invoice_no", "invoice_date", "start_date", "end_date", 
                "project_no", "vendor", "client"]
    )

    return {
        "po_list": po,
        "wpr_list": wpr,
        "irm_list": irm
    }


@frappe.whitelist()
def get_stock_entries(project_sub_contract, supplier, start_date, end_date):
    if not supplier:
        frappe.throw("Supplier is required in Project Sub-contract")

    query = """
        SELECT 
            name, posting_date, custom_supplier_code, docstatus, from_warehouse
        FROM `tabStock Entry`
        WHERE 
            stock_entry_type = 'Send to Subcontractor'
            AND custom_supplier_code = %(supplier)s
            AND posting_date BETWEEN %(start_date)s AND %(end_date)s
        ORDER BY posting_date ASC
    """

    data = frappe.db.sql(query, {
        "supplier": supplier,
        "start_date": start_date,
        "end_date": end_date
    }, as_dict=True)
    return data


@frappe.whitelist()
def get_stock_entries_irm(vendor, posting_date):
    """Get stock entries for Invoice Released Memo based on vendor and posting date"""
    if not vendor:
        frappe.throw("Vendor is required")

    query = """
        SELECT 
            name, posting_date, custom_supplier_code, docstatus, from_warehouse
        FROM `tabStock Entry`
        WHERE 
            stock_entry_type = 'Send to Subcontractor'
            AND custom_supplier_code = %(vendor)s
            AND posting_date = %(posting_date)s
        ORDER BY posting_date ASC
    """

    data = frappe.db.sql(query, {
        "vendor": vendor,
        "posting_date": posting_date
    }, as_dict=True)
    return data


@frappe.whitelist()
def get_stock_entry_items_irm(vendor, posting_date):
    """Get stock entry items for Invoice Released Memo based on vendor and posting date"""
    
    stock_entries = frappe.db.get_all(
        "Stock Entry",
        filters={
            "stock_entry_type": "Send to Subcontractor",
            "custom_supplier_code": vendor,
            "posting_date": posting_date
        },
        fields=["name"]
    )

    if not stock_entries:
        return []

    stock_entry_names = [se.name for se in stock_entries]

    return frappe.db.get_all(
        "Stock Entry Detail",
        filters={"parent": ["in", stock_entry_names]},
        fields=[
            "parent",
            "item_code",
            "item_name",
            "qty",
            "uom",
            "s_warehouse",
            "t_warehouse",
            "basic_rate"
        ],
        order_by="parent asc"
    )


@frappe.whitelist()
def get_stock_entry_items(supplier, start_date, end_date):

    stock_entries = frappe.db.get_all(
        "Stock Entry",
        filters={
            "stock_entry_type": "Send to Subcontractor",
            "custom_supplier_code": supplier,
            "posting_date": ["between", [start_date, end_date]]
        },
        fields=["name"]
    )

    if not stock_entries:
        return []

    stock_entry_names = [se.name for se in stock_entries]

    return frappe.db.get_all(
        "Stock Entry Detail",
        filters={"parent": ["in", stock_entry_names]},
        fields=[
            "parent",
            "item_code",
            "item_name",
            "qty",
            "uom",
            "s_warehouse",
            "t_warehouse",
            "basic_rate"      # REQUIRED FIELD
        ],
        order_by="parent asc"
    )


@frappe.whitelist()
def get_project_sub_contracts_for_stock_entry(supplier, posting_date):
    query = """
        SELECT 
            psc.name, 
            psc.party_name, 
            psc.start_date, 
            psc.end_date, 
            psc.docstatus, 
            COALESCE(project.project_name, psc.project) AS project, 
            psc.project_number
        FROM `tabProject Sub-Contracts` psc
        LEFT JOIN `tabProject` project ON psc.project = project.name
        WHERE psc.party_name = %(supplier)s
        AND %(posting_date)s BETWEEN psc.start_date AND psc.end_date
        ORDER BY psc.start_date ASC
    """

    data = frappe.db.sql(query, {
        "supplier": supplier,
        "posting_date": posting_date
    }, as_dict=True)

    return data