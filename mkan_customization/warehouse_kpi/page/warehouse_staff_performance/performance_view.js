// Performance Report tab: one row per storekeeper (spec 6.4, 6.6).

const KPI_PERF_COLUMNS = [
	["transactions", "Transactions"], ["lines", "Item Lines", false],
	["purchase_receipts", "Purchase Receipts"], ["material_returns", "Material Returns"],
	["return_requests", "Return Requests"], ["petty_cash", "Petty Cash"], ["other_receipts", "Other Receipts"],
	["material_issues", "Material Issues"], ["supplier_returns", "Supplier Returns"], ["transfers", "Transfers"],
	["stock_adjustments", "Stock Adjustments"], ["mr_created", "MR Created"], ["mr_issued", "MR Issued"],
	["equipment_logs", "Equipment Logs"], ["assets", "Assets"], ["light_equipment", "Light Equipment"],
	["cancelled", "Cancelled"], ["corrections", "Corrections"],
	["amended", "Amended By User"],
];

class KpiPerformance {
	constructor({ parent, fetch, on_drill }) {
		this.fetch = fetch; // ({limit, offset}) -> Promise<{total, rows}>
		this.on_drill = on_drill; // (row, key, label)
		this.esc = frappe.utils.escape_html;
		this.rows = [];
		this.$root = $(`
			<div class="kpi-box">
				<div class="kpi-box-title">${__("Warehouse Staff Performance Evaluation Report")}</div>
				<div class="kpi-scroll kpi-perf-body"></div>
			</div>`).appendTo(parent);
		this.pager = new KpiPager({ parent: this.$root, on_change: () => this.load() });
		this.$root.on("click", ".kpi-num", (e) => {
			const $a = $(e.currentTarget);
			this.on_drill(this.rows[$a.data("row")], $a.data("key"), $a.data("label"));
		});
	}

	reset() {
		this.pager.reset();
		this.load();
	}

	load() {
		const token = (this.token = (this.token || 0) + 1);
		this.fetch(this.pager.state()).then((data) => {
			if (token !== this.token) return;
			this.rows = data.rows;
			this.render(data);
		});
	}

	render(data) {
		const th = (label, cls = "") => `<th class="${cls}">${__(label)}</th>`;
		const head = th("Stock User") + th("Warehouses") +
			KPI_PERF_COLUMNS.map(([, l]) => th(l, "num")).join("") + th("Latest Evaluation");
		const body = data.rows.map((r, i) => this.row_html(r, i)).join("");
		this.$root.find(".kpi-perf-body").html(
			data.rows.length
				? `<table class="kpi-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`
				: `<div class="kpi-empty">${__("No data for these filters")}</div>`
		);
		this.pager.render(data.total);
	}

	row_html(r, i) {
		const cells = KPI_PERF_COLUMNS.map(([key, label, clickable]) => {
			const n = r[key];
			if (clickable === false || !n) return `<td class="num ${n ? "" : "text-muted"}">${n}</td>`;
			return `<td class="num"><a class="kpi-num" data-row="${i}" data-key="${key}" data-label="${this.esc(__(label))}">${n}</a></td>`;
		}).join("");
		return `<tr><td class="kpi-strong">${this.esc(r.storekeeper_name)}</td>
			<td class="kpi-places">${this.esc(r.warehouses || "-")}</td>${cells}<td>${this.score(r.latest_score)}</td></tr>`;
	}

	score(value) {
		if (value == null) return `<span class="text-muted">-</span>`;
		return `<span class="kpi-score"><span class="kpi-score-bar"><span style="width:${(value / 5) * 100}%"></span></span>
			<b>${value.toFixed(2)}/5</b></span>`;
	}
}
