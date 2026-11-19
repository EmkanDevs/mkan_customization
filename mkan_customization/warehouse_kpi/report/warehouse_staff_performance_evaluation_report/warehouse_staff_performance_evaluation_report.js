const DETAIL_REPORT = "Warehouse Staff Transaction Detail";

// Which Transaction Detail filters a clicked number sets.
const WSP_DRILL = {
	transactions: { status: "Submitted" },
	lines: { status: "Submitted" },
	purchase_receipts: { status: "Submitted", transaction_type: "Purchase Receipt" },
	material_returns: { status: "Submitted", transaction_type: "Material Return" },
	return_requests: { status: "Submitted", transaction_type: "Return Request" },
	petty_cash: { status: "Submitted", transaction_type: "Petty Cash Receipt" },
	other_receipts: { status: "Submitted", transaction_type: "Other Material Receipt" },
	material_issues: { status: "Submitted", transaction_type: "Material Issue" },
	supplier_returns: { status: "Submitted", transaction_type: "Supplier Return" },
	transfers: { status: "Submitted", transaction_type: "Stock Transfer" },
	stock_adjustments: { status: "Submitted", transaction_type: "Stock Adjustment" },
	mr_created: { status: "Submitted", transaction_type: "MR Created" },
	mr_issued: { status: "Submitted", transaction_type: "MR Issued" },
	equipment_logs: { status: "Submitted", transaction_type: "Equipment Log" },
	assets: { status: "Submitted", transaction_type: "Equipment Log" },
	light_equipment: { status: "Submitted", transaction_type: "Equipment Log" },
	cancelled: { special: "Cancelled" },
	corrections: { special: "Corrections" },
	amended: { special: "Amended by user" },
};

frappe.query_reports["Warehouse Staff Performance Evaluation Report"] = {
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
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		const drill = WSP_DRILL[column.fieldname];
		if (!drill || !data || !data[column.fieldname]) return value;
		return `<a href="${wsp_detail_url(drill, data.user)}" target="_blank" rel="noopener">${value}</a>`;
	},
};

// Opens the Transaction Detail report in a new tab with the same filters plus the clicked number.
function wsp_detail_url(drill, user) {
	const current = frappe.query_report.get_filter_values() || {};
	const params = {};
	["company", "from_date", "to_date", "warehouse", "location"].forEach((key) => {
		if (current[key]) params[key] = current[key];
	});
	Object.assign(params, drill, { storekeeper: user });
	const query = Object.entries(params)
		.map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
		.join("&");
	return `/app/query-report/${encodeURIComponent(DETAIL_REPORT)}?${query}`;
}
