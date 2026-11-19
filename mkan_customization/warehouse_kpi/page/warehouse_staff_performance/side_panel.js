// Drawer that shows a document summary without leaving the page (spec 6.6).

class KpiSidePanel {
	constructor() {
		this.$el = $(`
			<div class="kpi-panel">
				<div class="kpi-panel-head">
					<div class="kpi-panel-title"></div>
					<button class="btn btn-xs btn-default kpi-panel-close">${__("Close")}</button>
				</div>
				<div class="kpi-panel-body"></div>
			</div>
		`).appendTo(document.body);
		this.$el.find(".kpi-panel-close").on("click", () => this.close());
		this.$el.on("click", ".kpi-back", () => this.open_list(...this.list_args));
	}

	// A list of documents (e.g. behind one number of the Performance Report).
	open_list(title, fetch) {
		this.list_args = [title, fetch];
		this.show(title, "", true);
		this.table = new KpiDetailsTable({
			parent: this.$el.find(".kpi-panel-body"),
			fetch,
			on_open: (doctype, name) => this.open_document(doctype, name, true),
			on_show_all: () => {},
		});
		this.table.load(0);
	}

	open_document(doctype, name, from_list = false) {
		this.can_go_back = from_list;
		this.show(name, `<div class="text-muted">${__("Loading...")}</div>`);
		frappe.call({
			method: "mkan_customization.warehouse_kpi.api.get_document_summary",
			args: { doctype, name },
			callback: (r) => this.show(name, this.render_summary(r.message)),
			error: () => this.close(),
		});
	}

	show(title, html, wide = false) {
		this.$el.toggleClass("kpi-panel-wide", wide);
		this.$el.find(".kpi-panel-title").text(title);
		this.$el.find(".kpi-panel-body").html(html);
		this.$el.addClass("open");
	}

	close() {
		this.$el.removeClass("open");
	}

	render_summary(doc) {
		const esc = frappe.utils.escape_html;
		const fields = [[__("Status"), doc.status], [__("Created By"), doc.owner], ...doc.fields]
			.map(([k, v]) => `<div class="kpi-kv"><span>${esc(k)}</span><b>${esc(v)}</b></div>`)
			.join("");
		const head = doc.columns.map((c) => `<th>${esc(c)}</th>`).join("");
		const body = doc.items
			.map((row) => `<tr>${row.map((v) => `<td>${esc(v)}</td>`).join("")}</tr>`)
			.join("");
		const back = this.can_go_back ? `<a class="btn btn-default btn-sm kpi-back">&lsaquo; ${__("Back to list")}</a> ` : "";
		return `
			${back}<a class="btn btn-primary btn-sm" target="_blank" rel="noopener"
				href="/app/${frappe.router.slug(doc.doctype)}/${encodeURIComponent(doc.name)}">${__("Open document")}</a>
			<div class="kpi-kvs">${fields}</div>
			<div class="kpi-scroll"><table class="kpi-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>
		`;
	}
}
