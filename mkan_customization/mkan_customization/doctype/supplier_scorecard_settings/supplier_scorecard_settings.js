frappe.ui.form.on("Supplier Scorecard Settings", {
	refresh(frm) {
		frm.add_custom_button(__("Load Sample Values"), () => {
			frappe.confirm(__("Replace everything on this form with the sample values?"), () =>
				frm.call("load_defaults").then(() => frm.dirty() || frm.refresh())
			);
		});
	},
});
