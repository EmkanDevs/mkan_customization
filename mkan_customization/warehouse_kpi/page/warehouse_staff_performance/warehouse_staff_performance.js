try {
	delete localStorage["_page:warehouse-staff-performance"];
} catch (e) {}

// Page entry point. Parts are inlined by Frappe's include directive (no build step).
{% include "mkan_customization/warehouse_kpi/page/warehouse_staff_performance/filters.js" %}
{% include "mkan_customization/warehouse_kpi/page/warehouse_staff_performance/pager.js" %}
{% include "mkan_customization/warehouse_kpi/page/warehouse_staff_performance/side_panel.js" %}
{% include "mkan_customization/warehouse_kpi/page/warehouse_staff_performance/dashboard_view.js" %}
{% include "mkan_customization/warehouse_kpi/page/warehouse_staff_performance/details_table.js" %}
{% include "mkan_customization/warehouse_kpi/page/warehouse_staff_performance/performance_view.js" %}
{% include "mkan_customization/warehouse_kpi/page/warehouse_staff_performance/differences_view.js" %}
{% include "mkan_customization/warehouse_kpi/page/warehouse_staff_performance/evaluations_view.js" %}
{% include "mkan_customization/warehouse_kpi/page/warehouse_staff_performance/evaluation_dialog.js" %}

const KPI_API = "mkan_customization.warehouse_kpi.api.";
const KPI_TABS = [
	["dashboard", "Dashboard"],
	["performance", "Performance Report"],
	["differences", "Stock Differences"],
	["evaluations", "Evaluations"],
];
const KPI_DRILL_LABELS = {
	work: "All submitted transactions",
	"status:Cancelled": "Cancelled documents",
	"special:corrections": "Corrections",
	"special:amended": "Amended by user",
	"special:opening": "Opening entries",
};

frappe.pages["warehouse-staff-performance"].on_page_load = function (wrapper) {
	frappe.xcall(KPI_API + "get_page_context").then((context) => new KpiPage(wrapper, context));
};

class KpiPage {
	constructor(wrapper, context) {
		this.context = context;
		this.tab = "dashboard";
		this.view_as = this.initial_view();
		this.loaded = {};
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __("Warehouse Staff Performance Evaluation Dashboard"),
			single_column: true,
		});
		this.drill = "all";
		this.build_layout();
		this.panel = new KpiSidePanel();
		this.filters = new KpiFilters({
			parent: this.$body.find(".kpi-filters-slot"),
			context,
			on_change: () => this.refresh(),
		});
		this.dashboard = new KpiDashboard({
			parent: this.$body.find(".kpi-tab-dashboard"),
			on_drill: (drill) => this.set_drill(drill),
		});
		this.details = new KpiDetailsTable({
			parent: this.$body.find(".kpi-tab-dashboard"),
			fetch: (offset, limit) => this.fetch_transactions(offset, limit),
			on_open: (doctype, name) => this.panel.open_document(doctype, name),
			on_show_all: () => this.set_drill("all"),
		});
		this.build_tabs();
		this.build_view_menu();
		this.apply_view();
		this.page.set_primary_action(__("Export All to Excel"), () => this.export_excel(), "es-line-download");
		this.refresh();
	}

	build_tabs() {
		const filters = () => this.values();
		const call = (method, args) => frappe.xcall(KPI_API + method, { filters: filters(), ...args });
		this.performance = new KpiPerformance({
			parent: this.$body.find(".kpi-tab-performance").empty(),
			fetch: (page) => call("get_performance", page),
			on_drill: (row, act, label) =>
				this.panel.open_list(`${row.storekeeper_name}: ${label}`, (offset, limit) =>
					call("get_drill_docs", { user: row.storekeeper, act, limit, offset })),
		});
		this.differences = new KpiDifferences({
			parent: this.$body.find(".kpi-tab-differences").empty(),
			currency: this.context.currency,
			fetch: (summary_page, detail_page) => call("get_stock_differences", { summary_page, detail_page }),
			on_open: (doctype, name) => this.panel.open_document(doctype, name),
		});
		this.evaluations = new KpiEvaluations({
			parent: this.$body.find(".kpi-tab-evaluations").empty(),
			can_evaluate: this.context.can_evaluate,
			fetch: () => call("get_evaluations"),
			on_new: () => this.open_evaluation_dialog(null),
			on_edit: (doc) => this.open_evaluation_dialog(doc),
		});
	}

	values() {
		return { ...this.filters.get_values(), view_as: this.view_as };
	}

	// Only managers can switch. The server narrows to the user's own records for "Stock User".
	initial_view() {
		if (this.context.is_storekeeper_only) return "Stock User";
		try {
			return localStorage.getItem("kpi_view_as") === "Stock User" ? "Stock User" : "Stock Manager";
		} catch (e) {
			return "Stock Manager";
		}
	}

	build_view_menu() {
		if (this.context.is_storekeeper_only) return;
		const group = __("View as {0}", [__(this.view_as)]);
		this.page.clear_inner_toolbar();
		["Stock Manager", "Stock User"].forEach((mode) => {
			const label = __("View as {0}", [__(mode)]);
			this.page.add_inner_button(label, () => this.set_view(mode), group);
		});
	}

	set_view(mode) {
		if (mode === this.view_as) return;
		this.view_as = mode;
		try {
			localStorage.setItem("kpi_view_as", mode);
		} catch (e) {}
		this.build_view_menu();
		this.apply_view();
		this.refresh();
	}

	apply_view() {
		const own = this.view_as === "Stock User";
		this.filters.set_storekeeper_locked(own || this.context.is_storekeeper_only);
		this.evaluations.set_can_evaluate(this.context.can_evaluate && !own);
	}

	// POST download: the server answers with the file, so the filters never go in the URL.
	export_excel() {
		if (!this.filters.is_valid()) return frappe.msgprint(__("Select a valid date range first."));
		open_url_post(`/api/method/${KPI_API}export_excel`, { filters: JSON.stringify(this.values()) });
	}

	open_evaluation_dialog(doc) {
		frappe.xcall(KPI_API + "get_evaluation_form").then((form) => {
			new KpiEvaluationDialog({ form, doc, on_saved: (name) => this.evaluations.load(name) });
		});
	}

	build_layout() {
		const tabs = KPI_TABS.map(([key, label], i) =>
			`<a class="kpi-tab ${i ? "" : "active"}" data-tab="${key}">${__(label)}</a>`
		).join("");
		const placeholders = KPI_TABS.slice(1).map(([key, label]) =>
			`<div class="kpi-tab-${key}" style="display:none"><div class="kpi-box"><div class="kpi-empty">${__(label)}: ${__("coming in the next step")}</div></div></div>`
		).join("");
		this.$body = $(`
			<div class="kpi-page">
				<div class="kpi-tabs">${tabs}</div>
				<div class="kpi-filters-slot"></div>
				<div class="kpi-tab-dashboard"></div>
				${placeholders}
			</div>
		`).appendTo(this.page.main);
		this.$body.on("click", ".kpi-tab", (e) => this.show_tab($(e.currentTarget).data("tab")));
	}

	show_tab(key) {
		this.$body.find(".kpi-tab").removeClass("active").filter(`[data-tab=${key}]`).addClass("active");
		KPI_TABS.forEach(([k]) => this.$body.find(`.kpi-tab-${k}`).toggle(k === key));
		this.tab = key;
		this.load_tab();
	}

	// Tabs other than the dashboard load when opened, and again after a filter change.
	load_tab() {
		if (this.tab === "dashboard" || this.loaded[this.tab]) return;
		this.loaded[this.tab] = true;
		const view = { performance: this.performance, differences: this.differences, evaluations: this.evaluations }[this.tab];
		view.reset ? view.reset() : view.load();
	}

	refresh() {
		if (!this.filters.is_valid()) return;
		this.loaded = {};
		this.load_tab();
		const token = (this.token = (this.token || 0) + 1);
		frappe
			.xcall(KPI_API + "get_dashboard", { filters: this.values() })
			.then((data) => {
				if (token === this.token) this.dashboard.render(data);
			});
		this.details.load(0);
	}

	set_drill(drill) {
		this.drill = drill;
		this.details.set_label(this.drill_label(drill), drill !== "all");
		this.details.load(0);
		this.details.$root[0].scrollIntoView({ behavior: "smooth", block: "start" });
	}

	fetch_transactions(offset, limit) {
		return frappe.xcall(KPI_API + "get_transactions", {
			filters: this.values(),
			drill: this.drill,
			limit,
			offset,
		});
	}

	drill_label(drill) {
		if (KPI_DRILL_LABELS[drill]) return __(KPI_DRILL_LABELS[drill]);
		const [kind, a, b] = drill.split(":");
		if (kind === "type") return __(a);
		if (kind === "elr") return `${__("Equipment Logs")}: ${__(a)}`;
		if (kind === "mr") return `MR ${a}${b ? ` (${b})` : ""}`;
		return __("All transaction types");
	}
}
