import frappe
from frappe.model.document import Document
from frappe.utils import add_days, nowdate
from frappe.model.mapper import get_mapped_doc
from frappe.utils import get_url_to_form

class ProjectSubContracts(Document):
    def on_submit(self):
        version_0_items = [
            row.requirement for row in self.fulfilment_terms
            if str(row.custom_version).strip() == '0'
        ]
        if version_0_items:
            supplier = self.party_name
            create_po(version_0_items, supplier, self.project, self.name, 0)
    
    

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
    def postprocess(source_doc, target_doc):
        target_doc.cost_code = source_doc.business_code__cost_center
        target_doc.vendor = source_doc.party_name
        target_doc.start_date = source_doc.start_date
        target_doc.end_date = source_doc.end_date
        target_doc.project_no = source_doc.project
        target_doc.project_code = source_doc.project_number

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
                },
                "add_if_empty": True
            }
        },
        postprocess=postprocess
    )

    return doc.as_dict()


@frappe.whitelist()
def fetch_po_wpr_ipm(project_sub_contracts):
    # get Purchase Order, Work Progress Report and Invoic released Memo that linked to Project Sub-Contrcats
    
    po = frappe.get_all("Purchase Order", 
        filters={"custom_project_sub_contract": project_sub_contracts}, 
        fields=["custom_project_sub_contract", "name", "supplier", "workflow_state", "per_billed", "per_received",
                "transaction_date", "grand_total", "advance_paid", "version"]
    )
    wpr = frappe.get_all("Work Progress Report", 
        filters={"project_sub_contracts": project_sub_contracts}, 
        fields=["project_sub_contracts", "name", "version", "business_type", "start_date", "end_date", "project", "sub_contractor"]
    )
    # frappe.throw(str(po))
    irm = frappe.get_all("Invoice released Memo", 
        filters={"project_sub_contracts": project_sub_contracts}, 
        fields=["project_sub_contracts", "name",  "discpline", "invoice_no", "invoice_date", "start_date", "end_date", 
                "project_no", "vendor", "client"]
    )


    if not po and not wpr and not irm:
        return "<p style='color: red;'>No linked records found.</p>"

    max_length = max(len(po), len(wpr), len(irm))

    html = """
    <div style="border:1px solid #ccc; border-radius:5px;">
        <table width="100%" style="border-collapse: collapse;">
            <thead>
                <tr style="color:brown">
                    <th width="33%" style="border:1px solid #ccc; padding:8px">Purchase Order</th>
                    <th width="33%" style="border:1px solid #ccc; padding:8px">Work Progress Report</th>
                    <th width="33%" style="border:1px solid #ccc; padding:8px">Invoice released Memo</th>
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
                    <b>Version:</b> {row.version}<br>
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
    # frappe.throw(str(html))
    return html