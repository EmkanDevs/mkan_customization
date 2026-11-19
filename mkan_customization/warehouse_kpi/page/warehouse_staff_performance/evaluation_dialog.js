// New / edit evaluation dialog. Only collects input; the server validates everything (spec 5.5).

class KpiEvaluationDialog {
	constructor({ form, doc, on_saved }) {
		this.form = form; // from get_evaluation_form
		this.doc = doc; // existing draft, or null
		this.on_saved = on_saved;
		this.esc = frappe.utils.escape_html;
		this.questions = doc ? doc.ratings.map((r) => r.question) : form.questions;
		this.ratings = doc ? doc.ratings.map((r) => r.rating || 0) : this.questions.map(() => 0);
		this.build();
	}

	build() {
		const allowed = this.form.allowed_warehouses;
		this.dialog = new frappe.ui.Dialog({
			title: this.doc ? __("Edit Stock User Evaluation") : __("New Stock User Evaluation"),
			size: "large",
			fields: [
				{ fieldname: "storekeeper", fieldtype: "Link", options: "User", label: __("Stock User"), reqd: 1,
					get_query: () => ({ query: "mkan_customization.warehouse_kpi.scope.get_storekeeper_users_query" }) },
				{ fieldtype: "Column Break" },
				{ fieldname: "warehouse", fieldtype: "Link", options: "Warehouse", label: __("Warehouse"), reqd: 1,
					get_query: () => ({ filters: { is_group: 0, company: this.form.company, ...(allowed.length ? { name: ["in", allowed] } : {}) } }) },
				{ fieldtype: "Section Break" },
				{ fieldname: "from_date", fieldtype: "Date", label: __("From Date"), reqd: 1 },
				{ fieldtype: "Column Break" },
				{ fieldname: "to_date", fieldtype: "Date", label: __("To Date"), reqd: 1 },
				{ fieldtype: "Section Break" },
				{ fieldname: "ratings_html", fieldtype: "HTML" },
				{ fieldname: "remarks", fieldtype: "Small Text", label: __("Manager Remarks (optional)") },
			],
			primary_action_label: __("Submit Evaluation"),
			primary_action: () => this.save(1),
			secondary_action_label: __("Save Draft"),
			secondary_action: () => this.save(0),
		});
		this.dialog.set_values({
			storekeeper: this.doc?.storekeeper, warehouse: this.doc?.warehouse,
			from_date: this.doc?.from_date || this.form.from_date, to_date: this.doc?.to_date || this.form.to_date,
			remarks: this.doc?.remarks,
		});
		this.render_ratings();
		this.dialog.$wrapper.find(".modal-title").after(`<span class="kpi-score-badge"></span>`);
		this.update_score();
		this.dialog.show();
	}

	render_ratings() {
		const html = this.questions.map((q, i) => `
			<div class="kpi-rate-box"><div><b>${i + 1}. ${this.esc(q)}</b></div>
				<div class="kpi-rate-row" data-q="${i}">
					${[1, 2, 3, 4, 5].map((n) => `<button type="button" class="kpi-rate ${this.ratings[i] === n ? "on" : ""}" data-v="${n}">${n}</button>`).join("")}
				</div></div>`);
		const $html = this.dialog.get_field("ratings_html").$wrapper.html(html.join(""));
		$html.on("click", ".kpi-rate", (e) => {
			const $b = $(e.currentTarget);
			this.ratings[$b.parent().data("q")] = +$b.data("v");
			$b.siblings().removeClass("on");
			$b.addClass("on");
			this.update_score();
		});
	}

	update_score() {
		const given = this.ratings.filter(Boolean);
		const text = given.length ? (given.reduce((a, b) => a + b, 0) / given.length).toFixed(2) + "/5" : "-";
		this.dialog.$wrapper.find(".kpi-score-badge").text(`${__("Score")}: ${text}`);
	}

	save(submit) {
		const v = this.dialog.get_values();
		if (!v) return;
		const data = {
			name: this.doc?.name, company: this.form.company, storekeeper: v.storekeeper, warehouse: v.warehouse,
			from_date: v.from_date, to_date: v.to_date, overall_remarks: v.remarks,
			ratings: this.questions.map((question, i) => ({ question, rating: this.ratings[i] || "", remarks: this.doc?.ratings[i].remarks })),
		};
		frappe.xcall(KPI_API + "save_evaluation", { data, submit }).then((name) => {
			this.dialog.hide();
			frappe.show_alert({ message: submit ? __("Evaluation submitted") : __("Draft saved"), indicator: "green" });
			this.on_saved(name);
		});
	}
}
