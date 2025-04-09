frappe.ui.form.on("Expense Claim", {
	setup: function (frm) {

		frm.set_query("custom_account_head", "expenses", function () {
			return {
				filters: [
					["company", "=", frm.doc.company],
					[
						"account_type",
						"in",
						["Tax", "Chargeable", "Income Account", "Expenses Included In Valuation"],
					],
				],
			};
		});

	},
});
