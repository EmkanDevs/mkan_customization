// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt

frappe.query_reports["Is Return Purchase Receipt Report"] = {
	filters: [
		{ fieldname: "return_against", label: __("Original Purchase Receipt No"), fieldtype: "Link", options: "Purchase Receipt" },
		{ fieldname: "year", label: __("Year (Is Return Record)"), fieldtype: "Int" },
		{
			fieldname: "month",
			label: __("Month (Is Return Record)"),
			fieldtype: "Select",
			options: ["", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"].join("\n"),
		},
		{ fieldname: "owner", label: __("Created By"), fieldtype: "Link", options: "User" },
		{ fieldname: "item_code", label: __("Item"), fieldtype: "Link", options: "Item" },
		{ fieldname: "item_group", label: __("Item Group"), fieldtype: "Link", options: "Item Group" },
		{ fieldname: "supplier", label: __("Supplier"), fieldtype: "Link", options: "Supplier" },
		{ fieldname: "project", label: __("Project"), fieldtype: "Link", options: "Project" },
		{ fieldname: "material_request", label: __("Material Request"), fieldtype: "Link", options: "Material Request" },
		{ fieldname: "purchase_order", label: __("Purchase Order"), fieldtype: "Link", options: "Purchase Order" },
		{ fieldname: "workflow_state", label: __("Workflow State"), fieldtype: "Link", options: "Workflow State" },
	],
};
