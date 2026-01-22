import frappe
from frappe.utils import formatdate

def execute(filters=None):
    """Main function to generate the tree report"""
    if not filters:
        filters = {}

    columns = get_columns()
    data = get_data(filters)

    return columns, data

def get_columns():
    """Define the report columns - Including RFQ and Bid Tabulation"""
    columns = [
        # Document Reference
        {"label": "Document Type", "fieldname": "document_type", "fieldtype": "Data", "width": 150},
        {"label": "Document Name", "fieldname": "document_name", "fieldtype": "Dynamic Link", "options": "document_type", "width": 180},
        
        # Material Request Information
        {"label": "Material Request", "fieldname": "material_request", "fieldtype": "Link", "options": "Material Request", "width": 180},
        {"label": "MR Status", "fieldname": "mr_status", "fieldtype": "Data", "width": 100},
        {"label": "MR Workflow State", "fieldname": "mr_workflow_state", "fieldtype": "Data", "width": 130},
        
        # Request for Quotation Information
        {"label": "Request for Quotation", "fieldname": "request_for_quotation", "fieldtype": "Link", "options": "Request for Quotation", "width": 180},
        {"label": "RFQ Status", "fieldname": "rfq_status", "fieldtype": "Data", "width": 100},
        {"label": "RFQ Workflow State", "fieldname": "rfq_workflow_state", "fieldtype": "Data", "width": 130},
        
        # Bid Tabulation / Supplier Quotation Information
        {"label": "Bid Tabulation", "fieldname": "bid_tabulation", "fieldtype": "Link", "options": "Bid Tabulation Discussion", "width": 180},
        {"label": "BT Status", "fieldname": "bt_status", "fieldtype": "Data", "width": 100},
        {"label": "Supplier Quotation", "fieldname": "supplier_quotation", "fieldtype": "Link", "options": "Supplier Quotation", "width": 180},
        {"label": "SQ Status", "fieldname": "sq_status", "fieldtype": "Data", "width": 100},
        
        # Purchase Order Information
        {"label": "Purchase Order", "fieldname": "purchase_order", "fieldtype": "Link", "options": "Purchase Order", "width": 180},
        {"label": "PO Status", "fieldname": "po_status", "fieldtype": "Data", "width": 100},
        {"label": "PO Workflow State", "fieldname": "po_workflow_state", "fieldtype": "Data", "width": 130},
        {"label": "PO Approval Date", "fieldname": "po_approval_date", "fieldtype": "Data", "width": 140},
        {"label": "PO Transaction Date", "fieldname": "po_transaction_date", "fieldtype": "Date", "width": 130},
        
        # Purchase Receipt
        {"label": "Purchase Receipt", "fieldname": "purchase_receipt", "fieldtype": "Link", "options": "Purchase Receipt", "width": 180},
        {"label": "PR Status", "fieldname": "pr_status", "fieldtype": "Data", "width": 100},
        {"label": "PR Workflow State", "fieldname": "pr_workflow_state", "fieldtype": "Data", "width": 130},
        
        # Purchase Invoice
        {"label": "Purchase Invoice", "fieldname": "purchase_invoice", "fieldtype": "Link", "options": "Purchase Invoice", "width": 180},
        {"label": "PI Status", "fieldname": "pi_status", "fieldtype": "Data", "width": 100},
        {"label": "PI Workflow State", "fieldname": "pi_workflow_state", "fieldtype": "Data", "width": 130},
        
        # Payment Request
        {"label": "Payment Request", "fieldname": "payment_request", "fieldtype": "Link", "options": "Payment Request", "width": 180},
        {"label": "PayReq Status", "fieldname": "payreq_status", "fieldtype": "Data", "width": 100},
        {"label": "PayReq Workflow State", "fieldname": "payreq_workflow_state", "fieldtype": "Data", "width": 130},
        
        # Payment Entry
        {"label": "Payment Entry", "fieldname": "payment_entry", "fieldtype": "Link", "options": "Payment Entry", "width": 180},
        {"label": "PE Status", "fieldname": "pe_status", "fieldtype": "Data", "width": 100},
        {"label": "PE Workflow State", "fieldname": "pe_workflow_state", "fieldtype": "Data", "width": 130},
        
        # Purchase Order Item Information
        {"label": "Item Code", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 130},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Data", "width": 150},
        {"label": "Item Group", "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 130},
        {"label": "Quantity", "fieldname": "qty", "fieldtype": "Float", "width": 90},
        {"label": "Project", "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 130},
        {"label": "Schedule Date", "fieldname": "schedule_date", "fieldtype": "Date", "width": 120},
        
        # Technical fields for tree structure
        {"label": "Indent", "fieldname": "indent", "fieldtype": "Int", "width": 50, "hidden": 1},
        {"label": "Parent Document", "fieldname": "parent_document", "fieldtype": "Data", "width": 180, "hidden": 1},
    ]
    
    return columns

def get_data(filters):
    """Fetches and organizes the report data in tree format"""
    conditions = []
    values = {}

    # Base condition for Material Request Purpose
    mr_purpose = filters.get("material_request_purpose", "Purchase")
    if mr_purpose:
        conditions.append("mr.material_request_type = %(mr_purpose)s")
        values["mr_purpose"] = mr_purpose

    # Handle project filtering
    if filters.get("project"):
        if isinstance(filters["project"], list):
            conditions.append("poi.project IN %(projects)s")
            values["projects"] = tuple(filters["project"])
        else:
            conditions.append("poi.project = %(project)s")
            values["project"] = filters["project"]
    
    # Handle date range filtering on PO transaction date
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("po.transaction_date BETWEEN %(from_date)s AND %(to_date)s")
        values["from_date"] = filters["from_date"]
        values["to_date"] = filters["to_date"]

    condition_str = " AND ".join(conditions) if conditions else "1=1"
    
    # Check for Bid Tabulation Discussion DocType existence
    bid_tabulation_exists = frappe.db.exists("DocType", "Bid Tabulation Discussion")
    
    # Check if workflow_state exists in Request for Quotation
    rfq_has_workflow = frappe.db.sql("""
        SELECT COUNT(*) 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = 'tabRequest for Quotation'
        AND COLUMN_NAME = 'workflow_state'
    """)[0][0] > 0
    
    # Get Material Request parent rows
    parent_query = """
        SELECT DISTINCT
            'Material Request' AS document_type,
            mr.name AS document_name,
            mr.name AS material_request,
            mr.status AS mr_status,
            mr.workflow_state AS mr_workflow_state,
            0 AS indent,
            NULL AS parent_document
        FROM `tabMaterial Request` mr
        WHERE mr.material_request_type = %(mr_purpose)s
        ORDER BY mr.creation DESC
    """
    
    parent_rows = frappe.db.sql(parent_query, values, as_dict=True)
    
    # Initialize null columns for parent rows
    null_columns = [
        "request_for_quotation", "rfq_status", "rfq_workflow_state",
        "bid_tabulation", "bt_status",
        "supplier_quotation", "sq_status",
        "purchase_order", "po_status", "po_workflow_state", "po_approval_date", "po_transaction_date",
        "purchase_receipt", "pr_status", "pr_workflow_state", 
        "purchase_invoice", "pi_status", "pi_workflow_state",
        "payment_request", "payreq_status", "payreq_workflow_state", 
        "payment_entry", "pe_status", "pe_workflow_state",
        "item_code", "item_name", "item_group", "qty", "project", "schedule_date"
    ]
    
    for row in parent_rows:
        for col in null_columns:
            row[col] = None
    
    data = []
    
    for mr_row in parent_rows:
        # Add Material Request parent row
        data.append(mr_row)
        
        # Build Bid Tabulation subquery based on DocType existence
        bt_rfq_subquery = """
            (SELECT GROUP_CONCAT(DISTINCT bt.name SEPARATOR ', ')
             FROM `tabBid Tabulation Discussion` bt
             WHERE bt.request_for_quotation = rfq.name) AS bid_tabulation,
            (SELECT GROUP_CONCAT(DISTINCT CASE 
                WHEN bt.docstatus = 0 THEN 'Draft'
                WHEN bt.docstatus = 1 THEN 'Submitted'
                WHEN bt.docstatus = 2 THEN 'Cancelled'
                ELSE 'Unknown'
             END SEPARATOR ', ')
             FROM `tabBid Tabulation Discussion` bt
             WHERE bt.request_for_quotation = rfq.name) AS bt_status,
        """ if bid_tabulation_exists else """
            NULL AS bid_tabulation,
            NULL AS bt_status,
        """

        # Build RFQ workflow field based on field existence
        rfq_workflow_field = "rfq.workflow_state AS rfq_workflow_state," if rfq_has_workflow else "NULL AS rfq_workflow_state,"
        
        # Get Request for Quotations linked to this Material Request
        rfq_query = f"""
            SELECT DISTINCT
                rfq.name AS request_for_quotation,
                rfq.status AS rfq_status,
                {rfq_workflow_field}
                {bt_rfq_subquery}
                (SELECT GROUP_CONCAT(DISTINCT sq.name SEPARATOR ', ')
                 FROM `tabSupplier Quotation` sq
                 JOIN `tabSupplier Quotation Item` sqi ON sqi.parent = sq.name
                 WHERE sqi.request_for_quotation = rfq.name) AS supplier_quotation,
                (SELECT GROUP_CONCAT(DISTINCT sq.status SEPARATOR ', ')
                 FROM `tabSupplier Quotation` sq
                 JOIN `tabSupplier Quotation Item` sqi ON sqi.parent = sq.name
                 WHERE sqi.request_for_quotation = rfq.name) AS sq_status
            FROM `tabRequest for Quotation` rfq
            JOIN `tabRequest for Quotation Item` rfqi ON rfqi.parent = rfq.name
            WHERE rfqi.material_request = %s
            GROUP BY rfq.name
            ORDER BY rfq.creation
        """
        
        rfq_rows = frappe.db.sql(rfq_query, mr_row["material_request"], as_dict=True)
        
        # Add RFQ rows as children of MR
        for rfq_row in rfq_rows:
            rfq_row.update({
                "document_type": "Request for Quotation",
                "document_name": rfq_row["request_for_quotation"],
                "material_request": mr_row["material_request"],
                "mr_status": mr_row["mr_status"],
                "mr_workflow_state": mr_row["mr_workflow_state"],
                "indent": 1,
                "parent_document": mr_row["material_request"]
            })
            
            # Set PO and downstream fields to NULL
            for col in ["purchase_order", "po_status", "po_workflow_state", "po_approval_date", "po_transaction_date",
                       "purchase_receipt", "pr_status", "pr_workflow_state", 
                       "purchase_invoice", "pi_status", "pi_workflow_state",
                       "payment_request", "payreq_status", "payreq_workflow_state", 
                       "payment_entry", "pe_status", "pe_workflow_state",
                       "item_code", "item_name", "item_group", "qty", "project", "schedule_date"]:
                rfq_row[col] = None
            
            data.append(rfq_row)
        
        # Build Bid Tabulation subquery for PO level
        bt_po_subquery = """
            po.bid_tabulation AS bid_tabulation,
            (SELECT CASE 
                WHEN bt.docstatus = 0 THEN 'Draft'
                WHEN bt.docstatus = 1 THEN 'Submitted'
                WHEN bt.docstatus = 2 THEN 'Cancelled'
                ELSE 'Unknown'
             END
             FROM `tabBid Tabulation Discussion` bt
             WHERE bt.name = po.bid_tabulation) AS bt_status,
        """ if bid_tabulation_exists else """
            NULL AS bid_tabulation,
            NULL AS bt_status,
        """

        # Build RFQ workflow subquery for PO level
        rfq_workflow_subquery = """
            (SELECT GROUP_CONCAT(DISTINCT rfq.workflow_state SEPARATOR ', ')
             FROM `tabRequest for Quotation` rfq
             JOIN `tabRequest for Quotation Item` rfqi ON rfqi.parent = rfq.name
             WHERE rfqi.material_request = %s) AS rfq_workflow_state,
        """ if rfq_has_workflow else "NULL AS rfq_workflow_state,"
        
        # Get Purchase Orders linked to this Material Request
        po_query = f"""
            SELECT DISTINCT
                po.name AS purchase_order,
                po.status AS po_status,
                po.workflow_state AS po_workflow_state,
                (SELECT DATE_FORMAT(sc.modification_time, '%%d-%%m-%%Y %%H:%%i:%%s')
                 FROM `tabState Change Items` sc
                 WHERE sc.parent = po.name
                 AND sc.docstatus = 1 AND sc.workflow_state = 'Approved'
                 LIMIT 1) AS po_approval_date,
                po.transaction_date AS po_transaction_date,
                {bt_po_subquery}
                (SELECT GROUP_CONCAT(DISTINCT rfq.name SEPARATOR ', ')
                 FROM `tabRequest for Quotation` rfq
                 JOIN `tabRequest for Quotation Item` rfqi ON rfqi.parent = rfq.name
                 WHERE rfqi.material_request = %s) AS request_for_quotation,
                (SELECT GROUP_CONCAT(DISTINCT rfq.status SEPARATOR ', ')
                 FROM `tabRequest for Quotation` rfq
                 JOIN `tabRequest for Quotation Item` rfqi ON rfqi.parent = rfq.name
                 WHERE rfqi.material_request = %s) AS rfq_status,
                {rfq_workflow_subquery}
                (SELECT GROUP_CONCAT(DISTINCT sq.name SEPARATOR ', ')
                 FROM `tabSupplier Quotation` sq
                 JOIN `tabSupplier Quotation Item` sqi ON sqi.parent = sq.name
                 WHERE sqi.material_request = %s) AS supplier_quotation,
                (SELECT GROUP_CONCAT(DISTINCT sq.status SEPARATOR ', ')
                 FROM `tabSupplier Quotation` sq
                 JOIN `tabSupplier Quotation Item` sqi ON sqi.parent = sq.name
                 WHERE sqi.material_request = %s) AS sq_status,
                (SELECT GROUP_CONCAT(DISTINCT pr.name SEPARATOR ', ')
                 FROM `tabPurchase Receipt` pr
                 JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
                 JOIN `tabPurchase Order Item` poi2 ON poi2.name = pri.purchase_order_item
                 WHERE poi2.parent = po.name) AS purchase_receipt,
                (SELECT GROUP_CONCAT(DISTINCT pr.status SEPARATOR ', ')
                 FROM `tabPurchase Receipt` pr
                 JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
                 JOIN `tabPurchase Order Item` poi2 ON poi2.name = pri.purchase_order_item
                 WHERE poi2.parent = po.name) AS pr_status,
                (SELECT GROUP_CONCAT(DISTINCT pr.workflow_state SEPARATOR ', ')
                 FROM `tabPurchase Receipt` pr
                 JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
                 JOIN `tabPurchase Order Item` poi2 ON poi2.name = pri.purchase_order_item
                 WHERE poi2.parent = po.name) AS pr_workflow_state,
                (SELECT GROUP_CONCAT(DISTINCT pi.name SEPARATOR ', ')
                 FROM `tabPurchase Invoice` pi
                 JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
                 WHERE pii.purchase_order = po.name) AS purchase_invoice,
                (SELECT GROUP_CONCAT(DISTINCT pi.status SEPARATOR ', ')
                 FROM `tabPurchase Invoice` pi
                 JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
                 WHERE pii.purchase_order = po.name) AS pi_status,
                (SELECT GROUP_CONCAT(DISTINCT pi.workflow_state SEPARATOR ', ')
                 FROM `tabPurchase Invoice` pi
                 JOIN `tabPurchase Invoice Item` pii ON pii.parent = pi.name
                 WHERE pii.purchase_order = po.name) AS pi_workflow_state,
                (SELECT GROUP_CONCAT(DISTINCT pr.name SEPARATOR ', ')
                 FROM `tabPayment Request` pr
                 WHERE pr.reference_name = po.name) AS payment_request,
                (SELECT GROUP_CONCAT(DISTINCT pr.status SEPARATOR ', ')
                 FROM `tabPayment Request` pr
                 WHERE pr.reference_name = po.name) AS payreq_status,
                (SELECT GROUP_CONCAT(DISTINCT pr.workflow_state SEPARATOR ', ')
                 FROM `tabPayment Request` pr
                 WHERE pr.reference_name = po.name) AS payreq_workflow_state,
                (SELECT GROUP_CONCAT(DISTINCT pe.name SEPARATOR ', ')
                 FROM `tabPayment Entry` pe
                 JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
                 WHERE per.reference_name = po.name) AS payment_entry,
                (SELECT GROUP_CONCAT(DISTINCT pe.status SEPARATOR ', ')
                 FROM `tabPayment Entry` pe
                 JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
                 WHERE per.reference_name = po.name) AS pe_status,
                (SELECT GROUP_CONCAT(DISTINCT pe.workflow_state SEPARATOR ', ')
                 FROM `tabPayment Entry` pe
                 JOIN `tabPayment Entry Reference` per ON per.parent = pe.name
                 WHERE per.reference_name = po.name) AS pe_workflow_state
            FROM `tabPurchase Order` po
            JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
            JOIN `tabMaterial Request Item` mri ON mri.name = poi.material_request_item
            WHERE mri.parent = %s
            GROUP BY po.name
            ORDER BY po.creation
        """
        
        po_values = [
            mr_row["material_request"],  # for RFQ
            mr_row["material_request"],  # for RFQ status
            mr_row["material_request"],  # for RFQ workflow state
            mr_row["material_request"],  # for SQ
            mr_row["material_request"],  # for SQ status
            mr_row["material_request"]   # for WHERE clause
        ]
        
        po_rows = frappe.db.sql(po_query, po_values, as_dict=True)
        
        for po_row in po_rows:
            # Add Purchase Order as child row
            po_row.update({
                "document_type": "Purchase Order",
                "document_name": po_row["purchase_order"],
                "material_request": mr_row["material_request"],
                "mr_status": mr_row["mr_status"],
                "mr_workflow_state": mr_row["mr_workflow_state"],
                "indent": 1,
                "parent_document": mr_row["material_request"],
                "item_code": None,
                "item_name": None,
                "item_group": None,
                "qty": None,
                "project": None,
                "schedule_date": None
            })
            
            data.append(po_row)
            
            # Get Purchase Order Items for this PO
            po_item_query = """
                SELECT 
                    'Purchase Order Item' AS document_type,
                    poi.name AS document_name,
                    %s AS material_request,
                    %s AS mr_status,
                    %s AS mr_workflow_state,
                    %s AS request_for_quotation,
                    %s AS rfq_status,
                    %s AS rfq_workflow_state,
                    %s AS bid_tabulation,
                    %s AS bt_status,
                    %s AS supplier_quotation,
                    %s AS sq_status,
                    poi.parent AS purchase_order,
                    %s AS po_status,
                    %s AS po_workflow_state,
                    %s AS po_approval_date,
                    %s AS po_transaction_date,
                    %s AS purchase_receipt,
                    %s AS pr_status,
                    %s AS pr_workflow_state,
                    %s AS purchase_invoice,
                    %s AS pi_status,
                    %s AS pi_workflow_state,
                    %s AS payment_request,
                    %s AS payreq_status,
                    %s AS payreq_workflow_state,
                    %s AS payment_entry,
                    %s AS pe_status,
                    %s AS pe_workflow_state,
                    poi.item_code,
                    poi.item_name,
                    (SELECT item_group FROM `tabItem` WHERE name = poi.item_code) AS item_group,
                    poi.qty,
                    IFNULL(CAST(poi.project AS CHAR), '') AS project,
                    poi.schedule_date,
                    2 AS indent,
                    %s AS parent_document
                FROM `tabPurchase Order Item` poi
                WHERE poi.parent = %s
                ORDER BY poi.idx
            """
            
            po_item_params = [
                mr_row["material_request"], mr_row["mr_status"], mr_row["mr_workflow_state"],
                po_row["request_for_quotation"], po_row["rfq_status"], po_row["rfq_workflow_state"],
                po_row["bid_tabulation"], po_row["bt_status"],
                po_row["supplier_quotation"], po_row["sq_status"],
                po_row["po_status"], po_row["po_workflow_state"], 
                po_row["po_approval_date"], po_row["po_transaction_date"],
                po_row["purchase_receipt"], po_row["pr_status"], po_row["pr_workflow_state"],
                po_row["purchase_invoice"], po_row["pi_status"], po_row["pi_workflow_state"],
                po_row["payment_request"], po_row["payreq_status"], po_row["payreq_workflow_state"],
                po_row["payment_entry"], po_row["pe_status"], po_row["pe_workflow_state"],
                po_row["purchase_order"], po_row["purchase_order"]
            ]
            
            po_item_rows = frappe.db.sql(po_item_query, po_item_params, as_dict=True)
            data.extend(po_item_rows)

    return data