frappe.ui.form.on("Project", {
	refresh: function (frm) {
		// First report
		frm.add_custom_button("Contract Report", function () {
			frappe.set_route("query-report", "Project Contract Details", {
				project: frm.doc.name
			});
		}, "Reports");

		// Second report
		frm.add_custom_button("Site Violation Report", function () {
			frappe.set_route("query-report", "Project Site Violation", {
				project: frm.doc.name
			});
		}, "Reports");

		// Third report (optional)
		frm.add_custom_button("Petty Cash Report", function () {
			frappe.set_route("query-report", "Petty Cash Request", {
				project: frm.doc.name
			});
		}, "Reports");

		frm.add_custom_button("New Requisition Report", function () {
			frappe.set_route("query-report", "New Requisition", {
				for_project: frm.doc.name
			});
		}, "Reports");

		frm.add_custom_button(
			"PO Details Report",
			() => {
				frappe.route_options = {
					project: frm.doc.name
				};
				frappe.set_route("po-details-report");
			},
			__("Reports")
		);

		frm.add_custom_button("It Asset Management Report", function () {
			frappe.set_route("query-report", "It Asset Management", {
				project: frm.doc.name
			});
		}, "Reports");
		frm.add_custom_button("Non-Settled Petty Cash", function () {
			frappe.set_route("query-report", "Non-Settled Petty Cash", {
				project: frm.doc.name
			});
		}, "Reports");
	}
});
