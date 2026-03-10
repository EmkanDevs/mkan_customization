frappe.query_reports["PO Details with Supplier Quotation"] = {
    "filters": [
        {
            "fieldname": "supplier",
            "label": "Supplier",
            "fieldtype": "Link",
            "options": "Supplier"
        },
        {
            "fieldname": "project",
            "label": "Project",
            "fieldtype": "Link",
            "options": "Project"
        },
        {
            "fieldname": "purchase_order",
            "label": "Purchase Order",
            "fieldtype": "Link",
            "options": "Purchase Order"
        },
        {
            "fieldname": "from_date",
            "label": "PO From Date",
            "fieldtype": "Date"
        },
        {
            "fieldname": "to_date",
            "label": "PO To Date",
            "fieldtype": "Date"
        }
    ]
};