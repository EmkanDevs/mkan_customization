// Transaction Details table with server-side paging and drill filter (spec 6.6).

const KPI_PAGE_SIZES = [10, 25, 50, 100];

class KpiDetailsTable {
	constructor({ parent, fetch, on_open, on_show_all }) {
		this.fetch = fetch; // (offset, limit) -> Promise<{total, rows}>
		this.on_open = on_open;
		this.esc = frappe.utils.escape_html;
		this.page_size = 10;
		this.offset = 0;
		this.$root = $(`
			<div class="kpi-box kpi-details">
				<div class="kpi-box-title">${__("Transaction Details")}
					<a class="kpi-show-all" style="display:none">${__("Show all")}</a></div>
				<div class="kpi-scroll kpi-details-body"></div>
				<div class="kpi-pager"></div>
			</div>
		`).appendTo(parent);
		this.$root.find(".kpi-show-all").on("click", on_show_all);
		this.$root.on("click", ".kpi-doc", (e) => {
			this.on_open($(e.currentTarget).data("doctype"), $(e.currentTarget).data("name"));
		});
		this.$root.on("change", ".kpi-size", (e) => this.set_page_size(+e.target.value));
		this.$root.on("click", ".kpi-prev", () => this.go(-1));
		this.$root.on("click", ".kpi-next", () => this.go(1));
	}

	load(offset = 0) {
		this.offset = offset;
		const token = (this.token = (this.token || 0) + 1);
		this.fetch(offset, this.page_size).then((data) => {
			if (token === this.token) this.render(data);
		});
	}

	set_label(label, drilled) {
		this.label = label;
		this.$root.find(".kpi-show-all").toggle(drilled);
	}

	render(data) {
		this.total = data.total;
		const head = ["Document", "Date", "Stock User", "Type", "Warehouse / Location", "Status", "Lines", "Transaction Qty", "Stock Qty"];
		const th = head.map((h, i) => `<th class="${i >= 6 ? "num" : ""}">${__(h)}</th>`).join("");
		const body = data.rows.map((r) => this.row_html(r)).join("");
		const table = `<table class="kpi-table"><thead><tr>${th}</tr></thead><tbody>${body}</tbody></table>`;
		this.$root.find(".kpi-details-body").html(data.rows.length ? table : `<div class="kpi-empty">${__("No data for these filters")}</div>`);
		this.render_pager();
	}

	row_html(r) {
		const e = this.esc;
		const status = `<span class="kpi-pill ${r.status === "Cancelled" ? "kpi-pill-red" : "kpi-pill-green"}">${__(r.status)}</span>`;
		return `<tr>
			<td><a class="kpi-doc" data-doctype="${e(r.doctype)}" data-name="${e(r.name)}">${e(r.name)}</a></td>
			<td>${moment(r.date).format("DD MMM YYYY")}</td>
			<td>${e(r.user_name)}</td>
			<td>${e(r.type)}</td>
			<td>${e(r.place)}</td>
			<td>${status}</td>
			<td class="num">${r.lines}</td>
			<td class="num">${e(r.txn_qty || "-")}</td>
			<td class="num">${e(r.stock_qty || "-")}</td>
		</tr>`;
	}

	render_pager() {
		const pages = Math.max(1, Math.ceil(this.total / this.page_size));
		const page = Math.floor(this.offset / this.page_size) + 1;
		const from = this.total ? this.offset + 1 : 0;
		const to = Math.min(this.offset + this.page_size, this.total);
		const sizes = KPI_PAGE_SIZES.map((n) => `<option ${n === this.page_size ? "selected" : ""}>${n}</option>`).join("");
		this.$root.find(".kpi-pager").html(`
			<span class="text-muted">${this.esc(this.label || __("All transaction types"))}</span>
			<span class="kpi-pager-ctl">
				<span class="text-muted">${from}-${to} ${__("of")} ${this.total}</span>
				<select class="kpi-size form-control input-xs">${sizes}</select>
				<button class="btn btn-xs btn-default kpi-prev" ${page <= 1 ? "disabled" : ""}>&lsaquo; ${__("Prev")}</button>
				<b>${__("Page")} ${page} ${__("of")} ${pages}</b>
				<button class="btn btn-xs btn-default kpi-next" ${page >= pages ? "disabled" : ""}>${__("Next")} &rsaquo;</button>
			</span>`);
	}

	go(direction) {
		this.load(Math.max(0, this.offset + direction * this.page_size));
	}

	set_page_size(size) {
		this.page_size = size;
		this.load(0);
	}
}
