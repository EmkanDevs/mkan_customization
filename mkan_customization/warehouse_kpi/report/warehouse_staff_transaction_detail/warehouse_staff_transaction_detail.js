const WSD_TYPES = [
	"", "Purchase Receipt", "Material Return", "Petty Cash Receipt", "Other Material Receipt",
	"Material Issue", "Supplier Return", "Stock Transfer", "Stock Adjustment", "Return Request",
	"MR Created", "MR Issued", "Equipment Log",
];

frappe.query_reports["Warehouse Staff Transaction Detail"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
			default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date",
			default: frappe.datetime.month_start(), reqd: 1 },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date",
			default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "warehouse", label: __("Warehouse"), fieldtype: "Link", options: "Warehouse" },
		{ fieldname: "location", label: __("Asset Location"), fieldtype: "Link", options: "Location" },
		{ fieldname: "storekeeper", label: __("Stock User"), fieldtype: "Link", options: "User",
			get_query: () => ({ query: "mkan_customization.warehouse_kpi.scope.get_storekeeper_users_query" }) },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select",
			options: ["Submitted + Cancelled", "Submitted", "Cancelled"], default: "Submitted + Cancelled" },
		{ fieldname: "transaction_type", label: __("Transaction Type"), fieldtype: "Select", options: WSD_TYPES },
		{ fieldname: "mr_type", label: __("MR Type"), fieldtype: "Select",
			options: ["", "Material Issue", "Material Transfer", "Purchase", "Customer Provided"] },
		{ fieldname: "special", label: __("Special"), fieldtype: "Select",
			options: ["", "Corrections", "Amended by user", "Opening", "Cancelled"] },
	],
};
