frappe.pages['supplier-purchase-da'].on_page_load = function (wrapper) {
    new SupplierPurchaseDashboard(wrapper);
};

class SupplierPurchaseDashboard {

    constructor(wrapper) {
        this.wrapper = wrapper;
        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: "Supplier Purchase Dashboard",
            single_column: true
        });

        this.render();
        this.create_filters();
        this.bind_events();
        this.show_empty_state();
    }

    render() {
        $(this.page.body).html(`
            <style>
                /* Vertical x-axis labels so every PO ID fits */
                #chart-supplier svg .x-axis text,
                #chart-project svg .x-axis text {
                    transform: rotate(-90deg);
                    transform-origin: center top;
                    text-anchor: end;
                    font-size: 9px;
                }
                .chart-scroll-wrapper,
                .table-scroll-wrapper {
                    overflow-x: auto;
                    -webkit-overflow-scrolling: touch;
                    border: 1px solid #ebebeb;
                    border-radius: 4px;
                    padding-bottom: 8px;
                }
                .chart-container {
                    flex-shrink: 0;
                    display: inline-block;
                }
                /* Force DataTable cells to not wrap so horizontal scroll appears */
                .table-scroll-wrapper .data-table .content {
                    white-space: nowrap !important;
                }
                .table-scroll-wrapper .data-table {
                    min-width: 1100px;
                }
            </style>

            <div class="container-fluid">

                <!-- Filters -->
                <div class="card mb-4">
                    <div class="card-body">
                        <h4 class="mb-3">Filters</h4>
                        <div class="row" id="filter-area"></div>
                    </div>
                </div>

                <!-- KPI Cards -->
                <div class="row mb-4">
                    <div class="col-md-3">
                        <div class="kpi-card">
                            <div class="kpi-title">Total PO Value</div>
                            <div class="kpi-value" id="total-po">SAR 0.00</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="kpi-card">
                            <div class="kpi-title">PO Count</div>
                            <div class="kpi-value" id="po-count">0</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="kpi-card">
                            <div class="kpi-title">New Suppliers</div>
                            <div class="kpi-value" id="supplier-count">0</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="kpi-card">
                            <div class="kpi-title">Average PO</div>
                            <div class="kpi-value" id="avg-po">SAR 0.00</div>
                        </div>
                    </div>
                </div>

                <!-- Supplier Chart -->
                <div class="card mb-4">
                    <div class="card-body">
                        <h4 class="mb-3">Purchase Analysis by Supplier</h4>
                        <div class="chart-scroll-wrapper">
                            <div id="chart-supplier" class="chart-container" style="height: 450px;"></div>
                        </div>
                        <div id="legend-supplier" class="mt-3"></div>
                    </div>
                </div>

                <!-- Project Chart -->
                <div class="card mb-4">
                    <div class="card-body">
                        <h4 class="mb-3">Purchase Analysis by Project</h4>
                        <div class="chart-scroll-wrapper">
                            <div id="chart-project" class="chart-container" style="height: 450px;"></div>
                        </div>
                        <div id="legend-project" class="mt-3"></div>
                    </div>
                </div>

                <!-- Bottom Tables -->
                <div class="row">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h4>Team Summary</h4>
                                <div id="summary-table"></div>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-8">
                        <div class="card">
                            <div class="card-body">
                                <h4>Purchase Orders</h4>
                                <div class="table-scroll-wrapper">
                                    <div id="detail-table"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        `);
    }

    create_filters() {
        this.filters = {};
        const now = new Date();
        const currentYear = now.getFullYear();
        const currentMonth = now.getMonth() + 1;

        const fields = [
            {
                fieldname: "company",
                label: "Company",
                fieldtype: "Link",
                options: "Company",
                default: "Construction Pillars Company"
            },
            {
                fieldname: "year",
                label: "Year",
                fieldtype: "Select",
                options: `\n${currentYear - 1}\n${currentYear}\n${currentYear + 1}`,
                default: String(currentYear),
                reqd: 1
            },
            {
                fieldname: "month",
                label: "Month",
                fieldtype: "Select",
                options: "\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n11\n12",
                default: String(currentMonth),
                reqd: 1
            },
            {
                fieldname: "from_date",
                label: "From Date",
                fieldtype: "Date",
                default: frappe.datetime.month_start()
            },
            {
                fieldname: "to_date",
                label: "To Date",
                fieldtype: "Date",
                default: frappe.datetime.month_end()
            },
            {
                fieldname: "supplier",
                label: "Supplier",
                fieldtype: "Link",
                options: "Supplier"
            },
            {
                fieldname: "project",
                label: "Project",
                fieldtype: "Link",
                options: "Project"
            },
            {
                fieldname: "owner",
                label: "Created By",
                fieldtype: "Link",
                options: "User"
            }
        ];

        fields.forEach(df => {
            const col = $('<div class="col-md-2 mb-3"></div>')
                .appendTo($(this.page.body).find("#filter-area"));

            this.filters[df.fieldname] = frappe.ui.form.make_control({
                parent: col,
                df: df,
                render_input: true
            });

            // Explicitly set default value — make_control does not auto-apply it
            if (df.default) {
                this.filters[df.fieldname].set_value(df.default);
            }
        });
    }

    bind_events() {
        this.page.set_primary_action("Refresh", () => {
            if (!this.validate_filters()) return;
            this.load_dashboard();
        });
    }

    validate_filters() {
        const mandatory = ['year', 'month'];
        let missing = [];

        mandatory.forEach(key => {
            if (!this.filters[key].get_value()) {
                missing.push(this.filters[key].df.label);
            }
        });

        if (missing.length) {
            frappe.show_alert({
                message: __("Please fill mandatory filters: {0}", [missing.join(", ")]),
                indicator: "red"
            });
            return false;
        }
        return true;
    }

    show_empty_state() {
        const msg = '<p class="text-muted text-center" style="padding-top:180px;">Select Year & Month, then click Refresh to load data</p>';
        $(this.page.body).find("#chart-supplier").html(msg);
        $(this.page.body).find("#chart-project").html(msg);
        $(this.page.body).find("#summary-table").html('<p class="text-muted text-center">No data available</p>');
        $(this.page.body).find("#detail-table").html('<p class="text-muted text-center">No data available</p>');
    }

    get_filters() {
        let filters = {};
        Object.keys(this.filters).forEach(key => {
            filters[key] = this.filters[key].get_value();
        });
        return filters;
    }

    load_dashboard() {
        frappe.call({
            method: "mkan_customization.mkan_customization.page.supplier_purchase_da.supplier_purchase_da.get_dashboard_data",
            args: {
                filters: this.get_filters()
            },
            callback: (r) => {
                if (!r.message) return;

                // ── KPIs ──
                $("#total-po").html(
                    format_currency(
                        r.message.kpis.total_po || 0,
                        frappe.defaults.get_default("currency")
                    )
                );
                $("#po-count").html(r.message.kpis.po_count || 0);
                $("#supplier-count").html(r.message.kpis.new_suppliers || 0);
                $("#avg-po").html(
                    format_currency(
                        r.message.kpis.average_po || 0,
                        frappe.defaults.get_default("currency")
                    )
                );

                // ── Charts ──
                this.render_bar_chart({
                    chart_id: "chart-supplier",
                    legend_id: "legend-supplier",
                    chart_data: r.message.supplier_chart,
                    color_key: "supplier",
                    color_array_key: "suppliers"
                });

                this.render_bar_chart({
                    chart_id: "chart-project",
                    legend_id: "legend-project",
                    chart_data: r.message.project_chart,
                    color_key: "project",
                    color_array_key: "projects"
                });

                // ── Tables ──
                this.render_team_summary(r.message.team_summary);
                this.render_detail_table(r.message.purchase_orders);
            }
        });
    }

    render_bar_chart({ chart_id, legend_id, chart_data, color_key, color_array_key }) {
        const $chart = $(this.page.body).find("#" + chart_id);
        const $legend = $(this.page.body).find("#" + legend_id);

        $chart.empty();
        $legend.empty();

        if (!chart_data || !chart_data.labels || !chart_data.labels.length) {
            $chart.html('<p class="text-muted text-center" style="padding-top:180px;">No data available</p>');
            $chart.css("width", "100%");
            return;
        }

        const barWidth = 55;
        const calculatedWidth = Math.max(chart_data.labels.length * barWidth, 800);
        const chartEl = document.getElementById(chart_id);
        chartEl.style.width = calculatedWidth + "px";
        chartEl.style.height = "450px";
        chartEl.style.flexShrink = "0";
        chartEl.style.display = "inline-block";
        void chartEl.offsetWidth;

        const meta = {};
        chart_data.labels.forEach((label, i) => {
            meta[label] = {
                created_by: chart_data.creators ? chart_data.creators[i] : '',
                color_value: chart_data[color_array_key] ? chart_data[color_array_key][i] : ''
            };
        });

        const colorMap = chart_data[color_key + "_colors"] || {};

        new frappe.Chart("#" + chart_id, {
            data: {
                labels: chart_data.labels,
                datasets: [{ name: "PO Value", values: chart_data.values }]
            },
            type: 'bar',
            height: 450,
            colors: ['#cccccc'],
            axisOptions: {
                xAxisMode: 'tick',
                xIsSeries: true
            },
            barOptions: {
                spaceRatio: 0.25
            },
            valuesOverPoints: true,
            tooltipOptions: {
                formatTooltipX: (d) => {
                    const m = meta[d] || {};
                    return `${d}  |  ${m.created_by || 'Unknown'}  |  ${m.color_value || ''}`;
                },
                formatTooltipY: (d) => format_currency(d, frappe.defaults.get_default("currency"))
            }
        });

        const paintBars = (attempt = 1) => {
            const svg = chartEl.querySelector('svg');
            if (!svg) {
                if (attempt < 20) setTimeout(() => paintBars(attempt + 1), 250);
                return;
            }

            const bars = svg.querySelectorAll('rect.bar');
            if (!bars.length && attempt < 20) {
                setTimeout(() => paintBars(attempt + 1), 250);
                return;
            }

            let painted = 0;
            bars.forEach((bar, i) => {
                const key = chart_data[color_array_key][i];
                if (key && colorMap[key]) {
                    bar.style.fill = colorMap[key];
                    bar.style.stroke = colorMap[key];
                    bar.setAttribute('fill', colorMap[key]);
                    painted++;
                }
            });

            if (painted < chart_data.labels.length && attempt < 20) {
                setTimeout(() => paintBars(attempt + 1), 300);
            }
        };

        [200, 500, 800, 1200].forEach(d => setTimeout(paintBars, d));
        this.render_legend(legend_id, colorMap);
    }

    render_legend(legend_id, color_map) {
        const $legend = $(this.page.body).find("#" + legend_id);
        const keys = Object.keys(color_map);
        if (!keys.length) return;

        let html = '<div class="d-flex flex-wrap justify-content-center" style="gap: 14px;">';
        keys.forEach(key => {
            html += `
                <div class="d-flex align-items-center" style="font-size: 12px; color: #555;">
                    <span style="display:inline-block;width:12px;height:12px;background:${color_map[key]};border-radius:2px;margin-right:6px;flex-shrink:0;"></span>
                    <span>${key}</span>
                </div>
            `;
        });
        html += '</div>';
        $legend.html(html);
    }

    render_team_summary(data) {
        const $table = $(this.page.body).find("#summary-table");
        $table.empty();

        if (!data || !data.length) {
            $table.html('<p class="text-muted text-center">No data available</p>');
            return;
        }

        this.summary_table = new frappe.DataTable($table[0], {
            columns: [
                { name: "Team Member", id: "team_member", width: 180 },
                { name: "POs Issued", id: "po_count", width: 120, align: "right" }
            ],
            data: data,
            layout: "fluid",
            noDataMessage: "No data available"
        });
    }

    render_detail_table(data) {
        const $table = $(this.page.body).find("#detail-table");
        $table.empty();

        if (!data || !data.length) {
            $table.html('<p class="text-muted text-center">No data available</p>');
            return;
        }

        this.detail_table = new frappe.DataTable($table[0], {
            columns: [
                {
                    name: "PO Number",
                    id: "po_number",
                    width: 150,
                    format: (value) => `<a href="/app/purchase-order/${value}" target="_blank">${value}</a>`
                },
                { name: "Date", id: "date", width: 120 },
                { name: "Supplier", id: "supplier_name", width: 260 },
                { name: "Project", id: "project_name", width: 220 },
                { name: "Created By", id: "created_by", width: 180 },
                {
                    name: "Total",
                    id: "grand_total",
                    width: 150,
                    align: "right",
                    format: (value) => format_currency(value, frappe.defaults.get_default("currency"))
                }
            ],
            data: data,
            layout: "fluid",
            noDataMessage: "No data available"
        });
    }
}