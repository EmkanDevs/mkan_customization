frappe.query_reports["Supplier Ageing"] = {
    filters: [
        {
            fieldname: "company",
            label: __("Company"),
            fieldtype: "Link",
            options: "Company",
            reqd: 1
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            reqd: 1
        },
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier"
        },
        {
            fieldname: "supplier_group",
            label: __("Supplier Group"),
            fieldtype: "Link",
            options: "Supplier Group"
        },
        {
            fieldname: "payment_terms_template",
            label: __("Payment Terms Template"),
            fieldtype: "Link",
            options: "Payment Terms Template"
        },
        {
            fieldname: "range",
            label: __("Ageing Range"),
            fieldtype: "Data",
            default: "30,60,90,120"
        }
    ]
};
