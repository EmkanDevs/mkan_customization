frappe.ui.form.on("Warehouse Staff Evaluation", {
	setup(frm) {
		frm.set_query("storekeeper", () => {
			return {
				query: "mkan_customization.warehouse_kpi.scope.get_storekeeper_users_query",
			};
		});

		frm.set_query("warehouse", (doc) => {
			let filters = {
				is_group: 0,
			};
			if (doc.company) {
				filters.company = doc.company;
			}
			return { filters };
		});
	},

	refresh(frm) {
		if (frm.is_new() && !frm.doc.company) {
			frm.set_value("company", frappe.defaults.get_default("company"));
		}
		// The questions come from Settings and fix the score, so rows cannot be added or removed.
		frm.set_df_property("ratings", "cannot_add_rows", 1);
		frm.set_df_property("ratings", "cannot_delete_rows", 1);
		if (frm.is_new()) frm.trigger("load_questions");
	},

	// A new form has no server onload, so fetch the active questions and fill the table.
	load_questions(frm) {
		if ((frm.doc.ratings || []).some((r) => r.question)) return;
		frappe
			.xcall("mkan_customization.warehouse_kpi.doctype.warehouse_staff_evaluation.warehouse_staff_evaluation.get_active_questions")
			.then((questions) => {
				frm.clear_table("ratings");
				questions.forEach((question) => frm.add_child("ratings", { question }));
				frm.refresh_field("ratings");
			});
	},
});
