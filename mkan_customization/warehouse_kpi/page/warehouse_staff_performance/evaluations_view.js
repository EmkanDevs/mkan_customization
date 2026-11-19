// Evaluations tab: list on the left, detail on the right (spec 6.6).

class KpiEvaluations {
	constructor({ parent, fetch, can_evaluate, on_new, on_edit }) {
		this.fetch = fetch; // () -> Promise<list>
		this.can_evaluate = can_evaluate;
		this.on_edit = on_edit;
		this.esc = frappe.utils.escape_html;
		this.$root = $(`
			<div class="kpi-eval">
				<div class="kpi-box kpi-eval-list">
					<div class="kpi-box-title">
						<span>${__("Evaluations")}</span>
						${can_evaluate ? `<button type="button" class="btn btn-primary btn-xs kpi-eval-new">+ ${__("New")}</button>` : ""}
					</div>
					<div class="kpi-eval-items"></div>
				</div>
				<div class="kpi-box kpi-eval-detail"></div>
			</div>`).appendTo(parent);
		this.$root.find(".kpi-eval-new").on("click", on_new);
		this.$root.on("click", ".kpi-eval-item", (e) => this.select($(e.currentTarget).data("name")));
		this.$root.on("click", ".kpi-eval-edit", () => this.on_edit(this.current));
	}

	set_can_evaluate(value) {
		this.can_evaluate = value;
		this.$root.find(".kpi-eval-new").toggle(value);
	}

	load(select_name) {
		const token = (this.token = (this.token || 0) + 1);
		this.fetch().then((list) => {
			if (token !== this.token) return;
			this.render_list(list);
			const first = list.find((e) => e.name === (select_name || this.selected)) || list[0];
			if (first) this.select(first.name);
			else this.$root.find(".kpi-eval-detail").html(this.empty());
		});
	}

	render_list(list) {
		const html = list.map((e) => `
			<div class="kpi-eval-item" data-name="${this.esc(e.name)}">
				<b>${this.esc(e.storekeeper_name || e.storekeeper)}</b>
				<div class="text-muted">${this.esc(e.warehouse)}, ${this.period(e)}</div>
				<div>${this.pill(e.docstatus)} ${e.docstatus === 1 ? `<b class="kpi-eval-score">${e.overall_score.toFixed(2)}/5</b>` : ""}</div>
			</div>`);
		this.$root.find(".kpi-eval-items").html(html.join("") || this.empty());
	}

	select(name) {
		this.selected = name;
		this.$root.find(".kpi-eval-item").removeClass("active").filter(`[data-name="${CSS.escape(name)}"]`).addClass("active");
		frappe.xcall(KPI_API + "get_evaluation", { name }).then((doc) => {
			if (doc.name !== this.selected) return;
			this.current = doc;
			this.render_detail(doc);
		});
	}

	render_detail(d) {
		const score = d.complete ? `${d.overall_score.toFixed(2)}/5` : __("Incomplete");
		const card = (label, value) => `<div class="kpi-eval-card"><div class="kpi-eval-label">${__(label)}</div><b>${this.esc(value)}</b></div>`;
		const rows = d.ratings.map((r, i) => `
			<div class="kpi-eval-q"><span>${i + 1}. ${this.esc(r.question)}</span>
				<span class="kpi-dots">${this.dots(r.rating)}</span></div>`);
		this.$root.find(".kpi-eval-detail").html(`
			<div class="kpi-eval-head"><div><b class="kpi-eval-title">${this.esc(d.storekeeper_name)}, ${this.esc(d.name)}</b>
				<div class="text-muted">${__("Evaluated by")} ${this.esc(d.evaluated_by || "")}</div></div>${this.pill(d.docstatus)}</div>
			<div class="kpi-eval-body">
				<div class="kpi-eval-cards">${card("Warehouse", d.warehouse)}${card("Period", this.period(d))}${card("Overall Score", score)}${card("Status", d.docstatus ? "Submitted" : "Draft")}</div>
				${rows.join("")}
				<div class="kpi-eval-q kpi-eval-remarks"><div><b>${__("Manager Remarks")}</b>
					<div class="text-muted">${this.esc(d.remarks || (d.docstatus ? __("No remarks.") : __("Draft evaluation in progress.")))}</div></div></div>
				${d.can_edit && this.can_evaluate ? `<div class="kpi-eval-actions"><button class="btn btn-primary kpi-eval-edit">${__("Edit and Submit")}</button></div>` : ""}
			</div>`);
	}

	// Filled up to the chosen rating, like the prototype.
	dots(rating) {
		return [1, 2, 3, 4, 5].map((n) => `<span class="kpi-dot ${n <= rating ? "on" : ""}">${n}</span>`).join("");
	}

	pill(docstatus) {
		return docstatus === 1
			? `<span class="kpi-pill kpi-pill-green">${__("Submitted")}</span>`
			: `<span class="kpi-pill kpi-pill-amber">${__("Draft")}</span>`;
	}

	period(e) {
		const f = (d) => moment(d).format("DD MMM YYYY");
		return `${f(e.from_date)} ${__("to")} ${f(e.to_date)}`;
	}

	empty() {
		return `<div class="kpi-empty">${__("No evaluations for these filters")}</div>`;
	}
}
