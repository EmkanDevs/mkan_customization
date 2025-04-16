frappe.ui.form.on("Supplier Quotation", {
	refresh: function (frm) {
		if (frm.doc.status === "Expired" && frm.doc.docstatus !== 1) {
			frm.add_custom_button("Reopen", function () {
				frm.set_value("status", "Draft");
				frm.set_value("valid_till", frappe.datetime.get_today());
				frm.save()
			});
		}
	}
});
