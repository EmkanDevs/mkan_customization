// Stock Differences tab: bars by warehouse, monthly summary, item-level details (spec 4.8, 6.6).

class KpiDifferences {
	constructor({ parent, fetch, on_open, currency }) {
		this.fetch = fetch; // (summary_page, detail_page) -> Promise
		this.on_open = on_open;
		this.currency = currency;
		this.esc = frappe.utils.escape_html;
		this.$root = $(`
			<div>
				<div class="kpi-grid-2 kpi-grid-diff">
					<div class="kpi-box"><div class="kpi-box-title">${__("Difference Value by Warehouse")}</div><div class="kpi-diff-bars"></div></div>
					<div class="kpi-box"><div class="kpi-box-title">${__("Monthly Difference Summary")}</div>
						<div class="kpi-scroll kpi-diff-summary"></div><div class="kpi-summary-pager"></div></div>
				</div>
				<div class="kpi-box"><div class="kpi-box-title">${__("Stock Difference Details")}</div>
					<div class="kpi-scroll kpi-diff-details"></div><div class="kpi-detail-pager"></div></div>
			</div>`).appendTo(parent);
		this.summary_pager = new KpiPager({ parent: this.$root.find(".kpi-summary-pager"), on_change: () => this.load() });
		this.detail_pager = new KpiPager({ parent: this.$root.find(".kpi-detail-pager"), on_change: () => this.load() });
		this.$root.on("click", ".kpi-doc", (e) => this.on_open("Stock Reconciliation", $(e.currentTarget).data("name")));
	}

	reset() {
		this.summary_pager.reset();
		this.detail_pager.reset();
		this.load();
	}

	load() {
		const token = (this.token = (this.token || 0) + 1);
		this.fetch(this.summary_pager.state(), this.detail_pager.state()).then((data) => {
			if (token === this.token) this.render(data);
		});
	}

	render(data) {
		this.render_bars(data.bars);
		this.render_summary(data.summary.rows);
		this.summary_pager.render(data.summary.total);
		this.render_details(data.details.rows);
		this.detail_pager.render(data.details.total);
	}

	render_bars(bars) {
		const max = Math.max(1, ...bars.map((b) => Math.abs(b[1])));
		const html = bars.map(([wh, value], i) => `
			<div class="kpi-bar-row kpi-bar-row-diff">
				<span>${this.esc(wh)}</span>
				<span class="kpi-bar-track"><span class="kpi-bar-fill kpi-bar-${value < 0 ? 2 : i % 2}" style="width:${(Math.abs(value) / max) * 100}%"></span></span>
				<b>${this.money(value)}</b>
			</div>`);
		this.$root.find(".kpi-diff-bars").html(`<div class="kpi-type-bars">${html.join("") || this.empty()}</div>`);
	}

	render_summary(rows) {
		const body = rows.map((r) => `<tr><td>${moment(r.month + "-01").format("MMM YYYY")}</td><td>${this.esc(r.warehouse)}</td>
			<td>${this.esc(r.owner_name)}</td><td class="num">${r.items_checked}</td><td class="num">${r.difference_lines}</td>
			<td class="num">${this.currency} ${this.money(r.value)}</td></tr>`);
		this.table(".kpi-diff-summary", ["Month", "Warehouse", "Created By", "Items Checked", "Difference Lines", "Difference Value"], body, [3, 4, 5]);
	}

	render_details(rows) {
		const body = rows.map((r) => `<tr>
			<td><a class="kpi-doc" data-name="${this.esc(r.name)}">${this.esc(r.name)}</a></td>
			<td>${moment(r.date).format("DD MMM YYYY")}</td><td>${this.esc(r.warehouse)}</td>
			<td>${this.esc(r.item_name || r.item_code)}</td><td>${this.esc(r.uom)}</td>
			<td class="num">${this.qty(r.erp_qty)}</td><td class="num">${this.qty(r.counted_qty)}</td>
			<td class="num">${r.difference > 0 ? "+" : ""}${this.qty(r.difference)}</td>
			<td class="num">${this.money(r.value)}</td><td>${this.esc(r.owner_name)}</td></tr>`);
		const head = ["Reconciliation", "Date", "Warehouse", "Item", "UOM", "ERP Qty", "Counted Qty", "Difference", `Value (${this.currency})`, "Created By"];
		this.table(".kpi-diff-details", head, body, [5, 6, 7, 8]);
	}

	table(selector, head, body, nums) {
		const th = head.map((h, i) => `<th class="${nums.includes(i) ? "num" : ""}">${__(h)}</th>`).join("");
		this.$root.find(selector).html(
			body.length
				? `<table class="kpi-table"><thead><tr>${th}</tr></thead><tbody>${body.join("")}</tbody></table>`
				: this.empty()
		);
	}

	money(v) {
		return v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}

	qty(v) {
		return v.toLocaleString(undefined, { maximumFractionDigits: 3 });
	}

	empty() {
		return `<div class="kpi-empty">${__("No data for these filters")}</div>`;
	}
}
