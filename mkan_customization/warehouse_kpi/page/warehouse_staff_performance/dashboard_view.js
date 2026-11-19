// Dashboard tab: cards, charts and summary tables (spec 6.6).

const KPI_CARDS = [
	// [title, value key, subtitle, drill, colour]
	["Total Transactions", "transactions", "Submitted documents", "work", "navy"],
	["Total Item Lines", "lines", "Across all documents", "work", "navy"],
	["Purchase Receipts", "Purchase Receipt", "From suppliers", "type:Purchase Receipt", "blue"],
	["Material Returns", "Material Return", "Completed from RMWR", "type:Material Return", "green"],
	["Material Issues", "Material Issue", "Issued from store", "type:Material Issue", "amber"],
	["Stock Transfers", "Stock Transfer", "From source warehouse", "type:Stock Transfer", "purple"],
	["MR Issued", "MR Issued", "Issued by the storekeeper", "type:MR Issued", "green"],
	["Equipment Logs", "Equipment Log", "Assets and light equipment", "type:Equipment Log", "blue"],
	["Corrections", "corrections", "Own documents amended", "special:corrections", "amber"],
	["Cancelled", "cancelled", "Shown separately", "status:Cancelled", "red"],
];

class KpiDashboard {
	constructor({ parent, on_drill }) {
		this.on_drill = on_drill;
		this.esc = frappe.utils.escape_html;
		this.$root = $(`
			<div>
				<div class="kpi-cards"></div>
				<div class="kpi-grid-2">
					<div class="kpi-box"><div class="kpi-box-title">${__("Transactions by Type")}</div><div class="kpi-type-bars"></div></div>
					<div class="kpi-box"><div class="kpi-box-title">${__("Activity Trend")}</div><div class="kpi-trend"></div></div>
				</div>
				<div class="kpi-grid-3">
					<div class="kpi-box"><div class="kpi-box-title">${__("Received and Issued Quantity")}</div><div class="kpi-qty"></div></div>
					<div class="kpi-box"><div class="kpi-box-title">${__("Material Requests by Type")}</div><div class="kpi-mr"></div></div>
					<div class="kpi-box"><div class="kpi-box-title">${__("Accuracy and Corrections")}</div><div class="kpi-accuracy"></div></div>
				</div>
			</div>
		`).appendTo(parent);
		this.$root.on("click", "[data-drill]", (e) => this.on_drill($(e.currentTarget).data("drill")));
	}

	render(data) {
		this.render_cards(data.totals);
		this.render_type_bars(data);
		this.render_equipment(data.equipment);
		this.render_trend(data.trend);
		this.render_quantities(data.quantities);
		this.render_material_requests(data.material_requests);
		this.render_accuracy(data.totals);
	}

	render_cards(totals) {
		const html = KPI_CARDS.map(([title, key, sub, drill, colour]) => {
			const value = totals[key] ?? totals.by_type[key] ?? 0;
			return `
				<div class="kpi-stat kpi-${colour}" data-drill="${drill}">
					<div class="kpi-stat-title">${__(title)}</div>
					<div class="kpi-stat-value">${value.toLocaleString()}</div>
					<div class="kpi-stat-sub">${__(sub)}</div>
				</div>`;
		});
		this.$root.find(".kpi-cards").html(html.join(""));
	}

	// Plain HTML bars (not frappe.Chart): horizontal and clickable, like the prototype.
	render_type_bars(data) {
		const rows = data.chart_types;
		const max = Math.max(1, ...rows.map((r) => r[1]));
		const bars = rows.map(([type, count], i) => `
			<div class="kpi-bar-row" data-drill="type:${this.esc(type)}">
				<span class="kpi-bar-label">${this.esc(__(type))}</span>
				<span class="kpi-bar-track"><span class="kpi-bar-fill kpi-bar-${i % 2}" style="width:${(count / max) * 100}%"></span></span>
				<b class="kpi-bar-count">${count}</b>
			</div>`);
		const opening = data.totals.opening
			? `<div class="kpi-note" data-drill="special:opening">${__("Opening entries, not counted above")}: ${data.totals.opening}</div>`
			: "";
		this.$root.find(".kpi-type-bars").html((bars.join("") || this.empty()) + opening);
	}

	// Equipment Log split under the bars: documents by transaction type, rows by kind.
	render_equipment({ by_type, assets, light }) {
		const parts = by_type.map(([t, n]) => `<a data-drill="elr:${this.esc(t)}">${this.esc(__(t))} ${n}</a>`);
		parts.push(`${__("Assets")} ${assets}`, `${__("Light Equipment")} ${light}`);
		const html = `<div class="kpi-note kpi-elr">${__("Equipment Logs")}: ${parts.join(" &middot; ")}</div>`;
		this.$root.find(".kpi-type-bars").append(html);
	}

	render_trend(trend) {
		const el = this.$root.find(".kpi-trend").empty()[0];
		if (!trend.transactions.some(Boolean)) {
			el.innerHTML = this.empty();
			return;
		}
		new frappe.Chart(el, {
			type: "line",
			height: 260,
			colors: ["#2563eb", "#0d9488"],
			// Ticks only on the x axis, so only the horizontal grid lines show.
			axisOptions: { xIsSeries: true, xAxisMode: "tick", yAxisMode: "span" },
			// Dots only while the range is short enough to keep them readable.
			lineOptions: { regionFill: 0, hideDots: trend.dates.length > 31 ? 1 : 0, dotSize: 4 },
			data: {
				labels: trend.dates.map((d) => moment(d).format("DD/MM")),
				datasets: [
					{ name: __("Transactions"), values: trend.transactions },
					{ name: __("Item lines"), values: trend.lines },
				],
			},
		});
	}

	render_quantities(rows) {
		const num = (v) => (v ? v.toLocaleString(undefined, { maximumFractionDigits: 2 }) : "0");
		const body = rows.map((r) => `
			<tr><td><b>${this.esc(r.uom)}</b></td><td class="num">${num(r.received)}</td>
			<td class="num">${num(r.issued)}</td><td class="num">${num(r.transferred)}</td></tr>`);
		const head = [__("Stock UOM"), __("Received"), __("Issued"), __("Transferred")];
		this.$root.find(".kpi-qty").html(this.table(head, body));
	}

	render_material_requests({ rows, total }) {
		const cell = (n, drill) => (n ? `<a data-drill="${drill}">${n}</a>` : `<span class="text-muted">0</span>`);
		const body = rows.map((r) => `
			<tr><td>${this.esc(__(r.type))}</td>
			<td class="num">${cell(r.created, `mr:Created:${r.type}`)}</td>
			<td class="num">${cell(r.issued, `mr:Issued:${r.type}`)}</td></tr>`);
		body.push(`<tr class="kpi-total"><td>${__("Total")}</td><td class="num">${total.created}</td><td class="num">${total.issued}</td></tr>`);
		this.$root.find(".kpi-mr").html(this.table([__("Request Type"), __("Created"), __("Issued")], body));
	}

	render_accuracy(totals) {
		const items = [
			["Corrections", "Own documents later amended", totals.corrections, "special:corrections"],
			["Amended by user", "Amendments this user made", totals.amended, "special:amended"],
			["Cancelled documents", "Not counted as work", totals.cancelled, "status:Cancelled"],
		];
		const html = items.map(([title, sub, n, drill]) => `
			<div class="kpi-acc" data-drill="${drill}">
				<div><div class="kpi-acc-title">${__(title)}</div><div class="kpi-stat-sub">${__(sub)}</div></div>
				<div class="kpi-acc-value">${n}</div>
			</div>`);
		this.$root.find(".kpi-accuracy").html(html.join(""));
	}

	table(head, body) {
		if (!body.length) return this.empty();
		const th = head.map((h, i) => `<th class="${i ? "num" : ""}">${h}</th>`).join("");
		return `<table class="kpi-table"><thead><tr>${th}</tr></thead><tbody>${body.join("")}</tbody></table>`;
	}

	empty() {
		return `<div class="kpi-empty">${__("No data for these filters")}</div>`;
	}
}
