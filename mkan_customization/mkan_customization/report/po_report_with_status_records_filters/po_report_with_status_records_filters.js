frappe.query_reports["PO Report with Status Records Filters"] = {
    filters: [
        {
            fieldname: "purchase_order",
            label: __("Purchase Order"),
            fieldtype: "Link",
            options: "Purchase Order"
        },
        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project"
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.month_end()
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: [
                "",
                "Draft",
                "To Receive and Bill",
                "To Receive",
                "To Bill",
                "Completed",
                "Cancelled"
            ]
        }
    ]
};
