# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe

def execute(filters=None):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    warehouse = filters.get("warehouse")

    columns = [
        {"label": "Item (Issue)", "fieldname": "item_issue", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Item Name (Issue)", "fieldname": "item_name_issue", "fieldtype": "Data", "width": 150},
        {"label": "Item Group (Issue)", "fieldname": "item_group_issue", "fieldtype": "Link", "options": "Item Group", "width": 120},
        {"label": "Issue Qty", "fieldname": "issue_qty", "fieldtype": "Float", "width": 100},
        {"label": "Issue Amount", "fieldname": "issue_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Issue No. Req", "fieldname": "issue_no_of_reqs", "fieldtype": "Int", "width": 120},
        {"label": "Default Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 120},
        # {"label": "Target Warehouse", "fieldname": "warehouse_t", "fieldtype": "Link", "options": "Warehouse", "width": 120},
        {"label": "Receipt Qty", "fieldname": "receipt_qty", "fieldtype": "Float", "width": 100},
        {"label": "Receipt Amount", "fieldname": "receipt_amount", "fieldtype": "Currency", "width": 120},
        {"label": "Receipt No. Req", "fieldname": "receipt_no_of_reqs", "fieldtype": "Int", "width": 120},
        {"fieldname": "qty_percent", "label": "Qty %", "fieldtype": "Float", "width": 120},
        {"fieldname": "receipt_percent", "label": "Receipt %", "fieldtype": "Float", "width": 120},
    ]

    data = []

    warehouse_filter_issue = "AND sed.s_warehouse = %(warehouse)s" if warehouse else ""
    warehouse_filter_receipt = "AND sed.t_warehouse = %(warehouse)s" if warehouse else ""

    # Fetch Material Issue (OUT)
    issues = frappe.db.sql(f"""
        SELECT
            sed.item_code,
            item.item_name,
            item.item_group,
            sed.s_warehouse,
            SUM(sed.qty) AS qty,
            SUM(sed.amount) AS amount,
            1 AS no_of_reqs
            # COUNT(sed.parent) AS no_of_reqs
        FROM
            `tabStock Entry` se
        INNER JOIN
            `tabStock Entry Detail` sed ON se.name = sed.parent
        INNER JOIN
            `tabItem` item ON sed.item_code = item.name
        WHERE
            se.docstatus = 1
            AND se.stock_entry_type = 'Material Issue'
            AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
            {warehouse_filter_issue}
        GROUP BY
            sed.item_code, sed.s_warehouse
    """, {
        "from_date": from_date,
        "to_date": to_date,
        "warehouse": warehouse
    }, as_dict=True)

    # frappe.throw(str(issues))

    # Fetch Material Receipt (IN)
    receipts = frappe.db.sql(f"""
        SELECT
            sed.item_code,
            item.item_name,
            item.item_group,
            sed.t_warehouse,
            SUM(sed.qty) AS qty,
            SUM(sed.amount) AS amount,
            COUNT(sed.parent) AS no_of_reqs,
            # sed.qty AS qty,
            # sed.amount AS amount,
            se.name AS stock_entry
        FROM
            `tabStock Entry` se
        INNER JOIN
            `tabStock Entry Detail` sed ON se.name = sed.parent
        INNER JOIN
            `tabItem` item ON sed.item_code = item.name
        WHERE
            se.docstatus = 1
            AND se.stock_entry_type = 'Material Receipt'
            AND se.posting_date BETWEEN %(from_date)s AND %(to_date)s
            {warehouse_filter_receipt}
        GROUP BY
            sed.item_code
        ORDER BY
            sed.item_code, se.posting_date
    """, {
        "from_date": from_date,
        "to_date": to_date,
        "warehouse": warehouse
    }, as_dict=True)
    # frappe.throw(str(receipts))

    issue_map = {d.item_code: d for d in issues}
    receipt_map = {d.item_code: d for d in receipts}
    # receipt_map = {}
    # for rec in receipts:
        # receipt_map.setdefault(rec.item_code, []).append(rec)

    # all_items = set(list(issue_map.keys()) + list(receipt_map.keys()))

    for item_code, issue in issue_map.items():
        # issue = issue_map.get(item_code)
        receipts = receipt_map.get(item_code, [])
    # for item_code in all_items:
    #     issue = issue_map.get(item_code)
    #     receipts = receipt_map.get(item_code, [])

        if issue:
            issue_qty = issue.qty
            issue_amount = issue.amount
            warehouse = issue.s_warehouse
        else:
            issue_qty = None
            issue_amount = None
            warehouse = None
            
        if receipts:
            receipt_qty = receipts.qty
            receipt_amount = receipts.amount
            receipt_no_of_reqs = receipts.no_of_reqs
        else:
            receipt_qty = None
            receipt_amount = None
            receipt_no_of_reqs = None
            
        # total_receipt_qty = sum([receipt.qty for receipt in receipts]) if receipts else 0
        # total_receipt_amount = sum([receipt.amount for receipt in receipts]) if receipts else 0
        
        qty_percent = (receipt_qty / (issue_qty + receipt_qty) * 100) if (issue_qty and receipt_qty) else None
        receipt_percent = (receipt_amount / (issue_amount + receipt_amount) * 100) if (issue_amount and receipt_amount) else None

        data.append({
            "item_issue": issue.item_code if issue else None,
            "item_name_issue": issue.item_name if issue else None,
            "item_group_issue": issue.item_group if issue else None,
            "warehouse": warehouse if issue else None,
            # "warehouse_t": warehouse if issue else None,
            "issue_qty": issue_qty if issue else None,
            "issue_amount": issue_amount if issue else None,
            "issue_no_of_reqs": issue.no_of_reqs if issue else None,
            "receipt_qty": receipt_qty if receipts else None,
            "receipt_amount": receipt_amount if receipts else None,
            "receipt_no_of_reqs": receipt_no_of_reqs if receipts else None,
            "qty_percent": qty_percent,
            "receipt_percent": receipt_percent,
        })

        # if receipts:
        #     for idx, receipt in enumerate(receipts):
        #         qty_percent = (receipt.qty / (issue_qty + receipt.qty) * 100) if (issue_qty and receipt.qty) else None
        #         receipt_percent = (receipt.amount / (issue_amount + receipt.amount) * 100) if (issue_amount and receipt.amount) else None
                
        #         data.append({
        #             "item_issue": issue.item_code if (issue and idx == 0) else None,
        #             "item_name_issue": issue.item_name if (issue and idx == 0) else None,
        #             "item_group_issue": issue.item_group if (issue and idx == 0) else None,
        #             "warehouse": warehouse if (issue and idx == 0) else None,
        #             "issue_qty": issue.qty if (issue and idx == 0) else None,
        #             "issue_amount": issue.amount if (issue and idx == 0) else None,
        #             "issue_no_of_reqs": issue.no_of_reqs if (issue and idx == 0) else None,
        #             # "receipt_qty": receipt.qty,
        #             # "receipt_amount": receipt.amount,
        #             "receipt_qty": total_receipt_qty,
        #             "receipt_amount": total_receipt_amount,
        #             "receipt_no_of_reqs": len(receipts) if idx == 0 else None,
        #             "qty_percent": qty_percent,
        #             "receipt_percent": receipt_percent,
        #         })
        # else:
        #     # Only issue exists without any receipt
        #     data.append({
        #         "item_issue": issue.item_code if issue else None,
        #         "item_name_issue": issue.item_name if issue else None,
        #         "item_group_issue": issue.item_group if issue else None,
        #         "warehouse": warehouse if issue else None,
        #         "issue_qty": issue.qty if issue else None,
        #         "issue_amount": issue.amount if issue else None,
        #         "issue_no_of_reqs": issue.no_of_reqs if issue else None,
        #         "receipt_qty": None,
        #         "receipt_amount": None,
        #         "receipt_no_of_reqs": None,
        #         "qty_percent": None,
        #         "receipt_percent": None,
        #     })

    # Chart preparation
    labels = []
    issue_values = []
    receipt_values = []

    for row in data:
        label = row.get("item_issue") or "Unknown Item"
        if label not in labels:
            labels.append(label)
            issue_values.append(row.get("issue_qty") or 0)
            receipt_values.append(row.get("receipt_qty") or 0)

    chart = {
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "name": "Issue Qty",
                    "values": issue_values
                },
                {
                    "name": "Receipt Qty",
                    "values": receipt_values
                }
            ]
        },
        "type": "bar",
        "colors": ["#7cd6fd", "#743ee2"]
    }

    return columns, data, None, chart
