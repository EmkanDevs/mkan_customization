frappe.query_reports["GL Detailed Cost Data for All Projects Report"] = {
    filters: [
        {
            fieldname: "from_date",
            label: __("Valid From"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: __("Valid To"),
            fieldtype: "Date",
            reqd: 1,
            default: frappe.datetime.month_end()
        },

        {
            fieldname: "voucher_type",
            label: __("Voucher Type"),
            fieldtype: "Select",
            options: [
                "",
                "Journal Entry",
                "Payment Entry",
                "Sales Invoice",
                "Purchase Invoice",
                "Sales Order",
                "Purchase Order",
                "Sales Receipt",
                "Purchase Receipt",
                "Stock Entry",
                "Expense Claim",
                "Asset",
                "Asset Movement"
            ],
            on_change: function () {
                let voucher_type =
                    frappe.query_report.get_filter_value("voucher_type");

                // Clear existing subtype
                frappe.query_report.set_filter_value(
                    "voucher_subtype",
                    ""
                );

                if (!voucher_type) {
                    frappe.query_report.refresh();
                    return;
                }

                // Get subtypes for selected voucher type
                frappe.db.get_list("GL Entry", {
                    fields: ["voucher_subtype"],
                    filters: {
                        voucher_type: voucher_type,
                        voucher_subtype: ["is", "set"]
                    },
                    distinct: true,
                    order_by: "voucher_subtype asc",
                    limit_page_length: 0
                }).then(function (records) {

                    let options = [""];

                    records.forEach(function (row) {
                        if (row.voucher_subtype) {
                            options.push(row.voucher_subtype);
                        }
                    });

                    let subtype_filter =
                        frappe.query_report.get_filter("voucher_subtype");

                    subtype_filter.df.options = options;
                    subtype_filter.refresh();

                    // Refresh report with selected voucher type
                    frappe.query_report.refresh();
                });
            }
        },

        {
            fieldname: "voucher_subtype",
            label: __("Voucher Sub-Type"),
            fieldtype: "Select",
            options: [""],
            on_change: function () {
                frappe.query_report.refresh();
            }
        },

        {
            fieldname: "account_type",
            label: __("Account Type"),
            fieldtype: "Select",
            options: [
                "",
                "Income",
                "Expense"
            ]
        },

        {
            fieldname: "voucher_no",
            label: __("Voucher No"),
            fieldtype: "Data"
        },

        {
            fieldname: "project",
            label: __("Project"),
            fieldtype: "Link",
            options: "Project"
        },

        {
            fieldname: "department",
            label: __("Department"),
            fieldtype: "Link",
            options: "Department"
        }
    ]
};