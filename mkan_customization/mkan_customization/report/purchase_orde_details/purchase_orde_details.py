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
        
        # Material Request Information (Level 0)
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
        {"label": "BT Workflow State", "fieldname": "bt_workflow_state", "fieldtype": "Data", "width": 130},
        {"label": "Supplier Quotation", "fieldname": "supplier_quotation", "fieldtype": "Link", "options": "Supplier Quotation", "width": 180},
        {"label": "SQ Status", "fieldname": "sq_status", "fieldtype": "Data", "width": 100},
        {"label": "SQ Workflow State", "fieldname": "sq_workflow_state", "fieldtype": "Data", "width": 130},
        
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
        
        # Purchase Order Item Information (only for child rows)
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
    
    # Check for correct DocType "Bid Tabulation Discussion"
    bid_tabulation_exists = frappe.db.exists("DocType", "Bid Tabulation Discussion")
    
    # First, let's check what fields exist in Bid Tabulation Discussion
    if bid_tabulation_exists:
        try:
            # Test query to check available fields
            test_fields = frappe.db.sql("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'tabBid Tabulation Discussion'
                AND COLUMN_NAME IN ('status', 'docstatus', 'workflow_state')
            """)
            
            available_fields = [field[0] for field in test_fields]
            frappe.log_error(f"Available fields in Bid Tabulation Discussion: {available_fields}", "Bid Tabulation Fields")
        except:
            available_fields = []
    else:
        available_fields = []
    
    # FIXED: Query to get Material Request parent rows (simplified)
    parent_query = f"""
        SELECT DISTINCT
            'Material Request' AS document_type,
            mr.name AS document_name,
            mr.name AS material_request,
            mr.status AS mr_status,
            mr.workflow_state AS mr_workflow_state,
            0 AS indent,
            NULL AS parent_document
        FROM `tabMaterial Request` mr
        JOIN `tabMaterial Request Item` mri ON mri.parent = mr.name
        WHERE mr.material_request_type = %(mr_purpose)s
        ORDER BY mr.creation DESC
    """
    
    parent_rows = frappe.db.sql(parent_query, values, as_dict=True)
    
    # Add null values for missing columns
    for row in parent_rows:
        for col in ["request_for_quotation", "rfq_status", "rfq_workflow_state",
                   "bid_tabulation", "bt_status", "bt_workflow_state",
                   "supplier_quotation", "sq_status", "sq_workflow_state",
                   "purchase_order", "po_status", "po_workflow_state", "po_approval_date", "po_transaction_date",
                   "purchase_receipt", "pr_status", "pr_workflow_state", "purchase_invoice", "pi_status", "pi_workflow_state",
                   "payment_request", "payreq_status", "payreq_workflow_state", "payment_entry", "pe_status", "pe_workflow_state",
                   "item_code", "item_name", "item_group", "qty", "project", "schedule_date"]:
            row[col] = None
    
    data = []
    for mr_row in parent_rows:
        # Add Material Request parent row
        data.append(mr_row)
        
        # FIXED: Use docstatus instead of status for Bid Tabulation
        if bid_tabulation_exists:
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
                NULL AS bt_workflow_state,
            """
        else:
            bt_rfq_subquery = """
                NULL AS bid_tabulation,
                NULL AS bt_status,
                NULL AS bt_workflow_state,
            """

        # Get Request for Quotations linked to this Material Request
        rfq_query = f"""
            SELECT DISTINCT
                rfq.name AS request_for_quotation,
                rfq.status AS rfq_status,
                rfq.workflow_state AS rfq_workflow_state,
                
                -- Get Bid Tabulation linked to this RFQ
                {bt_rfq_subquery}
                
                -- Get Supplier Quotations linked to this RFQ
                (SELECT GROUP_CONCAT(DISTINCT sq.name SEPARATOR ', ')
                 FROM `tabSupplier Quotation` sq
                 JOIN `tabSupplier Quotation Item` sqi ON sqi.parent = sq.name
                 WHERE sqi.request_for_quotation = rfq.name) AS supplier_quotation,
                (SELECT GROUP_CONCAT(DISTINCT sq.status SEPARATOR ', ')
                 FROM `tabSupplier Quotation` sq
                 JOIN `tabSupplier Quotation Item` sqi ON sqi.parent = sq.name
                 WHERE sqi.request_for_quotation = rfq.name) AS sq_status,
                (SELECT GROUP_CONCAT(DISTINCT sq.workflow_state SEPARATOR ', ')
                 FROM `tabSupplier Quotation` sq
                 JOIN `tabSupplier Quotation Item` sqi ON sqi.parent = sq.name
                 WHERE sqi.request_for_quotation = rfq.name) AS sq_workflow_state
                
            FROM `tabRequest for Quotation` rfq
            JOIN `tabRequest for Quotation Item` rfqi ON rfqi.parent = rfq.name
            WHERE rfqi.material_request = %s
            GROUP BY rfq.name
            ORDER BY rfq.creation
        """
        
        rfq_rows = frappe.db.sql(rfq_query, mr_row["material_request"], as_dict=True)
        
        # Add RFQ rows as children of MR (indent 1)
        for rfq_row in rfq_rows:
            rfq_row["document_type"] = "Request for Quotation"
            rfq_row["document_name"] = rfq_row["request_for_quotation"]
            rfq_row["material_request"] = mr_row["material_request"]
            rfq_row["mr_status"] = mr_row["mr_status"]
            rfq_row["mr_workflow_state"] = mr_row["mr_workflow_state"]
            rfq_row["indent"] = 1
            rfq_row["parent_document"] = mr_row["material_request"]
            
            # Set other fields to NULL
            for col in ["purchase_order", "po_status", "po_workflow_state", "po_approval_date", "po_transaction_date",
                       "purchase_receipt", "pr_status", "pr_workflow_state", "purchase_invoice", "pi_status", "pi_workflow_state",
                       "payment_request", "payreq_status", "payreq_workflow_state", "payment_entry", "pe_status", "pe_workflow_state",
                       "item_code", "item_name", "item_group", "qty", "project", "schedule_date"]:
                rfq_row[col] = None
            
            data.append(rfq_row)
        
        # FIXED: Simplified Bid Tabulation query for PO level - using direct field from PO
        if bid_tabulation_exists:
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
                NULL AS bt_workflow_state,
            """
        else:
            bt_po_subquery = """
                NULL AS bid_tabulation,
                NULL AS bt_status,
                NULL AS bt_workflow_state,
            """

        # Get Purchase Orders linked to this Material Request with applied filters
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
                
                -- FIXED: Get Bid Tabulation directly from PO field
                {bt_po_subquery}
                
                -- Get RFQ linked to this PO
                (SELECT GROUP_CONCAT(DISTINCT rfq.name SEPARATOR ', ')
                 FROM `tabRequest for Quotation` rfq
                 JOIN `tabRequest for Quotation Item` rfqi ON rfqi.parent = rfq.name
                 WHERE rfqi.material_request = %s) AS request_for_quotation,
                (SELECT GROUP_CONCAT(DISTINCT rfq.status SEPARATOR ', ')
                 FROM `tabRequest for Quotation` rfq
                 JOIN `tabRequest for Quotation Item` rfqi ON rfqi.parent = rfq.name
                 WHERE rfqi.material_request = %s) AS rfq_status,
                (SELECT GROUP_CONCAT(DISTINCT rfq.workflow_state SEPARATOR ', ')
                 FROM `tabRequest for Quotation` rfq
                 JOIN `tabRequest for Quotation Item` rfqi ON rfqi.parent = rfq.name
                 WHERE rfqi.material_request = %s) AS rfq_workflow_state,
                
                -- Get Supplier Quotation linked to this PO
                (SELECT GROUP_CONCAT(DISTINCT sq.name SEPARATOR ', ')
                 FROM `tabSupplier Quotation` sq
                 JOIN `tabSupplier Quotation Item` sqi ON sqi.parent = sq.name
                 WHERE sqi.material_request = %s) AS supplier_quotation,
                (SELECT GROUP_CONCAT(DISTINCT sq.status SEPARATOR ', ')
                 FROM `tabSupplier Quotation` sq
                 JOIN `tabSupplier Quotation Item` sqi ON sqi.parent = sq.name
                 WHERE sqi.material_request = %s) AS sq_status,
                (SELECT GROUP_CONCAT(DISTINCT sq.workflow_state SEPARATOR ', ')
                 FROM `tabSupplier Quotation` sq
                 JOIN `tabSupplier Quotation Item` sqi ON sqi.parent = sq.name
                 WHERE sqi.material_request = %s) AS sq_workflow_state,
                
                -- Purchase Receipt for this PO
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
                
                -- Purchase Invoice for this PO
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
                
                -- Payment Request for this PO
                (SELECT GROUP_CONCAT(DISTINCT pr.name SEPARATOR ', ')
                 FROM `tabPayment Request` pr
                 WHERE pr.reference_name = po.name) AS payment_request,
                (SELECT GROUP_CONCAT(DISTINCT pr.status SEPARATOR ', ')
                 FROM `tabPayment Request` pr
                 WHERE pr.reference_name = po.name) AS payreq_status,
                (SELECT GROUP_CONCAT(DISTINCT pr.workflow_state SEPARATOR ', ')
                 FROM `tabPayment Request` pr
                 WHERE pr.reference_name = po.name) AS payreq_workflow_state,
                
                -- Payment Entry for this PO
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
            mr_row["material_request"],  # for SQ workflow state
            mr_row["material_request"]   # for WHERE clause
        ]
        
        po_rows = frappe.db.sql(po_query, po_values, as_dict=True)
        
        for po_row in po_rows:
            # Add Purchase Order as child row (indent 1)
            po_row["document_type"] = "Purchase Order"
            po_row["document_name"] = po_row["purchase_order"]
            po_row["material_request"] = mr_row["material_request"]
            po_row["mr_status"] = mr_row["mr_status"]
            po_row["mr_workflow_state"] = mr_row["mr_workflow_state"]
            po_row["indent"] = 1
            po_row["parent_document"] = mr_row["material_request"]
            po_row["item_code"] = None
            po_row["item_name"] = None
            po_row["item_group"] = None
            po_row["qty"] = None
            po_row["project"] = None
            po_row["schedule_date"] = None
            
            data.append(po_row)
            
            # Get Purchase Order Items for this PO
            po_item_query = """
                SELECT 
                    -- Document Info
                    'Purchase Order Item' AS document_type,
                    poi.name AS document_name,
                    
                    -- Material Request Info (from parent MR)
                    %s AS material_request,
                    %s AS mr_status,
                    %s AS mr_workflow_state,
                    
                    -- RFQ, BT, SQ Info (from parent PO)
                    %s AS request_for_quotation,
                    %s AS rfq_status,
                    %s AS rfq_workflow_state,
                    %s AS bid_tabulation,
                    %s AS bt_status,
                    %s AS bt_workflow_state,
                    %s AS supplier_quotation,
                    %s AS sq_status,
                    %s AS sq_workflow_state,
                    
                    -- Purchase Order Info
                    poi.parent AS purchase_order,
                    %s AS po_status,
                    %s AS po_workflow_state,
                    %s AS po_approval_date,
                    %s AS po_transaction_date,
                    
                    -- Related documents (from parent PO)
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
                    
                    -- Item Information (including item_group)
                    poi.item_code,
                    poi.item_name,
                    (SELECT item_group FROM `tabItem` WHERE name = poi.item_code) AS item_group,
                    poi.qty,
                    IFNULL(CAST(poi.project AS CHAR), '') AS project,
                    poi.schedule_date,
                    
                    -- Tree structure
                    2 AS indent,
                    %s AS parent_document
                    
                FROM `tabPurchase Order Item` poi
                WHERE poi.parent = %s
                ORDER BY poi.idx
            """
            
            # Prepare parameters for PO item query
            po_item_params = [
                mr_row["material_request"],
                mr_row["mr_status"],
                mr_row["mr_workflow_state"],
                po_row["request_for_quotation"],
                po_row["rfq_status"],
                po_row["rfq_workflow_state"],
                po_row["bid_tabulation"],
                po_row["bt_status"],
                po_row["bt_workflow_state"],
                po_row["supplier_quotation"],
                po_row["sq_status"],
                po_row["sq_workflow_state"],
                po_row["po_status"],
                po_row["po_workflow_state"],
                po_row["po_approval_date"],
                po_row["po_transaction_date"],
                po_row["purchase_receipt"],
                po_row["pr_status"],
                po_row["pr_workflow_state"],
                po_row["purchase_invoice"],
                po_row["pi_status"],
                po_row["pi_workflow_state"],
                po_row["payment_request"],
                po_row["payreq_status"],
                po_row["payreq_workflow_state"],
                po_row["payment_entry"],
                po_row["pe_status"],
                po_row["pe_workflow_state"],
                po_row["purchase_order"],  # parent document
                po_row["purchase_order"]   # for WHERE clause
            ]
            
            po_item_rows = frappe.db.sql(po_item_query, po_item_params, as_dict=True)
            data.extend(po_item_rows)

    # Add color indicators to status fields
    data = apply_status_colors(data)
    
    return data

def apply_status_colors(data):
    """Apply color coding to status fields based on workflow states"""
    
    status_color_map = {
        # Common statuses
        "Draft": "#3498db",  # Blue
        "Pending Approval": "#95a5a6",  # Gray
        "Pending": "#95a5a6",  # Gray
        "Approved": "#2ecc71",  # Green
        "Cancelled": "#e74c3c",  # Red
        "Submitted": "#2ecc71",  # Green
        "To Receive and Bill": "#f39c12",  # Orange
        "To Bill": "#f39c12",  # Orange
        "To Receive": "#f39c12",  # Orange
        "Completed": "#2ecc71",  # Green
        "Paid": "#2ecc71",  # Green
        "Unpaid": "#e74c3c",  # Red
        "Partially Paid": "#f39c12",  # Orange
        "Return": "#e67e22",  # Dark Orange
        "Initiated": "#3498db",  # Blue
        "Requested": "#f39c12",  # Orange
        "Payment Ordered": "#2ecc71",  # Green
        "Open": "#3498db",  # Blue
        "Closed": "#2ecc71",  # Green
        "Partially Ordered": "#f39c12",  # Orange
        "Received": "#2ecc71",  # Green
        "Partially Received": "#f39c12",  # Orange
        "Delivered": "#2ecc71",  # Green
        "Partially Delivered": "#f39c12",  # Orange
        "Stopped": "#e74c3c",  # Red
        "Rejected": "#e74c3c",  # Red
        "Transfer": "#9b59b6",  # Purple
        "Issue": "#e74c3c",  # Red
        "Manufacture": "#f39c12",  # Orange
        "Quotation": "#3498db",  # Blue
        "Ordered": "#2ecc71",  # Green
        "Awarded": "#2ecc71",  # Green
        "Evaluated": "#9b59b6",  # Purple
        "Expired": "#e74c3c",  # Red
        "Under Review": "#f39c12",  # Orange
        "Unknown": "#95a5a6",  # Gray for unknown status
    }
    
    # List of all status fields that need coloring
    status_fields = [
        "mr_status", "mr_workflow_state",
        "rfq_status", "rfq_workflow_state",
        "bt_status", "bt_workflow_state",
        "sq_status", "sq_workflow_state",
        "po_status", "po_workflow_state",
        "pr_status", "pr_workflow_state",
        "pi_status", "pi_workflow_state",
        "payreq_status", "payreq_workflow_state",
        "pe_status", "pe_workflow_state",
    ]
    
    for row in data:
        for field in status_fields:
            if row.get(field):
                # Handle multiple statuses separated by comma
                statuses = str(row[field]).split(', ')
                colored_statuses = []
                
                for status in statuses:
                    status = status.strip()
                    if status and status != 'None' and status != 'NULL':
                        color = status_color_map.get(status, "#34495e")  # Default dark gray
                        colored_statuses.append(f'<span style="color: {color}; font-weight: bold;">●</span> {status}')
                
                if colored_statuses:
                    row[field] = ', '.join(colored_statuses)
    
    return data