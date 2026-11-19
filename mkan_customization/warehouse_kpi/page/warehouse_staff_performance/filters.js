// Filter bar. No Apply button: any change refreshes after a debounce (spec 6.6).

// Wait this long after the last change before refreshing.
const KPI_DEBOUNCE_MS = 400;

class KpiFilters {
	constructor({ parent, context, on_change }) {
		this.context = context;
		this.on_change = frappe.utils.debounce(on_change, KPI_DEBOUNCE_MS);
		this.controls = {};
		this.$root = $(`
			<div class="kpi-filters">
				<div class="kpi-filter kpi-f-period"></div>
				<div class="kpi-filter kpi-f-from"></div>
				<div class="kpi-filter kpi-f-to"></div>
				<div class="kpi-filter kpi-f-warehouse"></div>
				<div class="kpi-filter kpi-f-location"></div>
				<div class="kpi-filter kpi-f-storekeeper"></div>
				<div class="kpi-filter kpi-f-status"></div>
				<div class="kpi-filter kpi-f-reset"><button class="btn btn-default btn-sm">${__("Reset")}</button></div>
			</div>
			<div class="kpi-filter-note"></div>
		`).appendTo(parent);
		this.make_controls();
		this.$root.find(".kpi-f-reset button").on("click", () => this.reset());
		this.apply_defaults();
		setTimeout(() => this.align_reset(), 0);
		$(window).on("resize.kpi_filters", () => this.align_reset());
	}

	// Line the Reset button up with the bottom edge of the input boxes, whatever Frappe adds below them.
	align_reset() {
		const $input = this.$root.find(".kpi-f-period .control-input").first();
		const $slot = this.$root.find(".kpi-f-reset");
		const $btn = $slot.find("button");
		if (!$input.length || !$input.is(":visible")) return;
		$btn.css({ height: $input.outerHeight() });
		const delta = ($input.offset().top + $input.outerHeight()) - ($btn.offset().top + $btn.outerHeight());
		if (delta) $slot.css("margin-bottom", (parseFloat($slot.css("margin-bottom")) || 0) - delta);
	}

	make_controls() {
		const add = (key, df) => {
			this.controls[key] = frappe.ui.form.make_control({
				parent: this.$root.find(`.kpi-f-${df.slot || key}`),
				df: { ...df, fieldname: key, change: () => this.changed(key) },
				render_input: true,
			});
		};
		add("period", {
			fieldtype: "Select", label: __("Period"), slot: "period",
			options: ["Today", "This Week", "This Month", "Custom Range"],
		});
		add("from_date", { fieldtype: "Date", label: __("From Date"), slot: "from" });
		add("to_date", { fieldtype: "Date", label: __("To Date"), slot: "to" });
		add("warehouse", {
			fieldtype: "Link", options: "Warehouse", label: __("Warehouse"),
			get_query: () => ({ filters: { is_group: 0, company: this.context.company } }),
		});
		add("location", { fieldtype: "Link", options: "Location", label: __("Equipment Location") });
		add("storekeeper", {
			fieldtype: "Link", options: "User", label: __("Stock User"),
			get_query: () => ({ query: "mkan_customization.warehouse_kpi.scope.get_storekeeper_users_query" }),
		});
		add("status", {
			fieldtype: "Select", label: __("Transaction Status"),
			options: ["Submitted + Cancelled", "Submitted", "Cancelled"],
		});
	}

	// A storekeeper sees their own name, read only. The server applies the same rule.
	// Leaving the locked state clears the value so it cannot linger.
	set_storekeeper_locked(locked) {
		this.locked = locked;
		this.set_silently({ storekeeper: locked ? frappe.session.user : "" });
		this.disable_control("storekeeper", locked);
	}

	apply_defaults() {
		this.set_silently({
			period: "This Month", status: "Submitted + Cancelled",
			warehouse: "", location: "",
			storekeeper: this.locked ? frappe.session.user : "",
		});
		this.sync_ui();
	}

	reset() {
		this.apply_defaults();
		this.on_change();
	}

	changed() {
		if (this.silent) return;
		this.sync_ui();
		if (this.is_valid()) this.on_change();
	}

	sync_ui() {
		const custom = this.value("period") === "Custom Range";
		this.$root.find(".kpi-f-from, .kpi-f-to").toggle(custom);
		this.disable_control("location", !!this.value("warehouse"));
		this.disable_control("warehouse", !!this.value("location"));
		this.show_note();
	}

	// A selected warehouse disables the location filter, and the other way round (spec 4.6).
	disable_control(key, disabled) {
		const control = this.controls[key];
		control.df.read_only = disabled ? 1 : 0;
		control.refresh();
	}

	is_valid() {
		const { from_date, to_date } = this.range();
		return !!from_date && !!to_date && from_date <= to_date;
	}

	show_note() {
		const { from_date, to_date } = this.range();
		let text = "";
		if (from_date && to_date && from_date > to_date) {
			text = __("From date must be on or before To date");
		} else if (this.value("period") !== "Custom Range" && from_date) {
			text = `${this.fmt(from_date)} ${__("to")} ${this.fmt(to_date)}`;
		}
		this.$root.siblings(".kpi-filter-note").text(text).toggleClass("text-danger", text.startsWith(__("From")));
	}

	range() {
		const today = frappe.datetime.get_today();
		const period = this.value("period");
		if (period === "Today") return { from_date: today, to_date: today };
		if (period === "This Week") {
			const monday = frappe.datetime.add_days(today, -((moment(today).day() + 6) % 7));
			return { from_date: monday, to_date: today };
		}
		if (period === "This Month") return { from_date: today.slice(0, 8) + "01", to_date: today };
		// A cleared date falls back to this month, the same default the server uses, so the data never goes stale.
		return {
			from_date: this.value("from_date") || today.slice(0, 8) + "01",
			to_date: this.value("to_date") || today,
		};
	}

	get_values() {
		return {
			...this.range(),
			company: this.context.company,
			warehouse: this.value("warehouse") || null,
			location: this.value("location") || null,
			storekeeper: this.value("storekeeper") || null,
			status: this.value("status"),
		};
	}

	value(key) {
		return this.controls[key].get_value();
	}

	set_silently(values) {
		this.silent = true;
		const sets = Object.entries(values).map(([key, value]) => this.controls[key].set_value(value));
		Promise.all(sets).finally(() => (this.silent = false));
	}

	fmt(date) {
		return moment(date).format("DD MMM YYYY");
	}
}
