frappe.query_reports["Purchaser Assigned Material Requests"] = {
    filters: [
        {
            fieldname: "assigned_to",
            label: __("Assigned To"),
            fieldtype: "Link",
            options: "User",
            default: frappe.session.user
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
            fieldtype: "Date"
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date"
        },
        {
            fieldname: "material_request",
            label: __("Material Request"),
            fieldtype: "Link",
            options: "Material Request"
        },
        {
            fieldname: "purpose",
            label: __("Purpose"),
            fieldtype: "Select",
            options: "Purchase\nMaterial Transfer\nManufacture\nCustomer Provided",
            default: "Purchase"
        }
    ]
};
