frappe.ui.form.on("Project", {
	refresh: function (frm) {
		frm.add_custom_button("Contract Report", function () {
			frappe.set_route("query-report", "Project Contract Details", {
				project: frm.doc.name
			});
		});
	}
});
