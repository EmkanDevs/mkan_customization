frappe.pages['-petty-cash-executiv'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: ' Petty Cash Executive Dashboard',
		single_column: true
	});
    const $refreshBtn = page.add_inner_button(__('Refresh'), function() {
        loadDashboard();
    });
    const $printBtn = page.add_inner_button(__('Print'), function() {
        printGrid();
    });
    const $excelBtn = page.add_inner_button(__('Excel'), function() {
        exportGridToExcel();
    });
    $refreshBtn.html(`<i class="fa fa-refresh"></i> ${__("Refresh")}`);
    $excelBtn.html(`<i class="fa fa-file-excel-o"></i> ${__("Excel")}`);
    $printBtn.html(`<i class="fa fa-print"></i> ${__("Print")}`);

    // ── Global state ──
    let dashboardData = {};
    let chartInstances = {};
    let currentPage = 0;
    let pageLength = 50;

    // ── Inject CSS ──
    const style = $(`
        <style>
        /* Base typography for consistency */
        .layout-main-section { background: linear-gradient(180deg, #f7f9fb 0%, #eef3f8 100%); }
        .pcd-container { max-width: 1600px; margin: 0 auto; padding: 0 16px 16px; font-family: Inter, "Helvetica Neue", Arial, sans-serif; font-size: 11.3px; color: var(--text-color, #1f272e); background: transparent; }
        .pcd-card { background: linear-gradient(180deg, #fff 0%, #fbfdff 100%); border: 1px solid #d8e0e8; border-radius: 8px; box-shadow: 0 8px 22px rgba(31,39,46,0.08), 0 1px 2px rgba(31,39,46,0.05); margin-bottom: 12px; overflow: hidden; }
        .pcd-card-header { min-height: 46px; padding: 10px 16px; border-bottom: 1px solid #dfe6ee; display: flex; align-items: center; justify-content: space-between; gap: 12px; background: linear-gradient(180deg, #fff 0%, #f8fafc 100%); }
        .pcd-card-header h2 { font-size: 13px; line-height: 1.25; font-weight: 600; color: var(--heading-color, #1f272e); margin: 0; display: flex; align-items: center; gap: 7px; }
        .pcd-card-body { padding: 14px 16px; }
        .pcd-filters-grid { display: grid; grid-template-columns: 1.4fr 0.7fr 0.9fr 1fr 1fr 1.25fr 1.25fr; gap: 10px 12px; align-items: end; }
        @media (max-width: 1200px) { .pcd-filters-grid { grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); } }
        .pcd-filter-group { display: flex; flex-direction: column; gap: 5px; }
        .pcd-filter-group label { font-size: 10.5px; font-weight: 600; color: var(--text-muted, #6b7280); }
        .pcd-filter-group select, .pcd-filter-group input { padding: 6px 10px; border: 1px solid var(--border-color, #d1d8dd); border-radius: 6px; font-size: 11.3px; background: var(--control-bg, #fff); color: var(--text-color, #1f272e); outline: none; }
        .pcd-filter-group select:focus, .pcd-filter-group input:focus { border-color: var(--primary, #2490ef); box-shadow: 0 0 0 3px rgba(36,144,239,0.12); }
        .pcd-kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(205px, 1fr)); gap: 12px; margin-bottom: 12px; }
        .pcd-kpi-card { background: linear-gradient(180deg, #fff 0%, #fbfdff 100%); border: 1px solid #d8e0e8; border-radius: 8px; padding: 13px 16px; position: relative; overflow: hidden; box-shadow: 0 8px 20px rgba(31,39,46,0.08), 0 1px 2px rgba(31,39,46,0.05); transition: transform 0.2s, box-shadow 0.2s; }
        .pcd-kpi-card:hover { transform: translateY(-2px); box-shadow: 0 12px 24px rgba(31,39,46,0.12), 0 2px 4px rgba(31,39,46,0.06); }
        .pcd-kpi-card::before { content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%; }
        .pcd-kpi-card.blue::before { background: var(--primary, #2490ef); }
        .pcd-kpi-card.green::before { background: #28a745; }
        .pcd-kpi-card.orange::before { background: #ff8c00; }
        .pcd-kpi-card.purple::before { background: #743ee2; }
        .pcd-kpi-card.teal::before { background: #00a8a8; }
        .pcd-kpi-label { font-size: 10.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; color: var(--text-muted, #6b7280); margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between; }
        .pcd-kpi-value { font-size: 18px; line-height: 1.2; font-weight: 700; color: var(--heading-color, #1f272e); margin-bottom: 4px; }
        .pcd-kpi-subtext { font-size: 9.7px; color: var(--text-muted, #6b7280); display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
        .pcd-badge { padding: 2px 5px; border-radius: 4px; font-size: 8.9px; font-weight: 600; }
        .pcd-badge.up { background: #e4f5e9; color: #28a745; }
        .pcd-badge.neutral { background: #e7f3ff; color: var(--primary, #2490ef); }
        .pcd-dashboard-grid { display: grid; grid-template-columns: repeat(12, 1fr); column-gap: 14px; row-gap: 12px; margin-bottom: 12px; }
        .pcd-col-4 { grid-column: span 4; }
        .pcd-col-6 { grid-column: span 6; }
        .pcd-col-8 { grid-column: span 8; }
        .pcd-col-12 { grid-column: span 12; }
        @media (max-width: 1200px) { .pcd-col-4, .pcd-col-6, .pcd-col-8 { grid-column: span 12; } }
        .pcd-chart-container { position: relative; height: 218px; width: 100%; }
        .pcd-col-12 .pcd-chart-container { height: 238px; }
        .pcd-chart-container-sm { height: 190px; }
        .pcd-tab-switcher { display: flex; background: var(--bg-light-gray, #f3f5f7); padding: 3px; border-radius: 6px; gap: 2px; }
        .pcd-tab-btn { padding: 5px 11px; font-size: 10.5px; font-weight: 600; border-radius: 4px; border: none; background: transparent; cursor: pointer; color: var(--text-muted, #6b7280); transition: all 0.2s; }
        .pcd-tab-btn.active { background: var(--card-bg, #fff); color: var(--primary, #2490ef); box-shadow: 0 1px 3px rgba(15,23,42,0.06); }
        .pcd-card-actions { display: flex; align-items: center; gap: 6px; }
        .pcd-icon-btn { width: 28px; height: 28px; display: inline-flex; align-items: center; justify-content: center; border: 1px solid var(--border-color, #d1d8dd); border-radius: 6px; background: var(--card-bg, #fff); color: var(--text-muted, #6b7280); cursor: pointer; transition: all 0.2s; }
        .pcd-icon-btn:hover { color: var(--primary, #2490ef); background: #f7fbff; border-color: var(--primary, #2490ef); }
        .pcd-table-wrapper { overflow-x: auto; }
        .pcd-table { width: 100%; border-collapse: collapse; font-size: 11.3px; text-align: left; }
        .pcd-table th { background: var(--bg-light-gray, #f3f5f7); color: var(--text-muted, #6b7280); font-weight: 600; font-size: 10.5px; padding: 8px 11px; border-bottom: 2px solid var(--border-color, #d1d8dd); text-transform: uppercase; letter-spacing: 0.3px; }
        .pcd-table td { padding: 9px 11px; border-bottom: 1px solid var(--border-color, #d1d8dd); color: var(--text-color, #1f272e); font-size: 11.3px; white-space: normal; word-break: break-word; }
        .pcd-table tr:hover { background: var(--bg-light-gray, #f3f5f7); }
        .pcd-table tr.total-row { font-weight: 700; background: var(--bg-light-gray, #f3f5f7); border-top: 2px solid var(--border-color, #d1d8dd); }
        .pcd-text-right { text-align: right; }
        .pcd-text-center { text-align: center; }
        .pcd-status-pill { display: inline-flex; align-items: center; gap: 5px; padding: 3px 7px; border-radius: 12px; font-size: 9.7px; font-weight: 600; white-space: normal; }
        .pcd-status-draft { background: #f3f5f7; color: #6b7280; }
        .pcd-status-pending { background: #fff4de; color: #ff8c00; }
        .pcd-status-approved { background: #e4f5e9; color: #28a745; }
        .pcd-status-tobill { background: #f0eaff; color: #743ee2; }
        .pcd-btn { display: inline-flex; align-items: center; gap: 7px; padding: 6px 12px; font-size: 11.3px; font-weight: 600; border-radius: 6px; border: 1px solid transparent; cursor: pointer; transition: all 0.2s; }
        .pcd-btn-primary { background: var(--primary, #2490ef); color: #fff; }
        .pcd-btn-primary:hover { background: #1677c7; }
        .pcd-btn-outline { background: var(--card-bg, #fff); border-color: var(--border-color, #d1d8dd); color: var(--text-color, #1f272e); }
        .pcd-btn-outline:hover { background: var(--bg-light-gray, #f3f5f7); border-color: #b8c2cc; }
        .pcd-search-box { position: relative; width: 320px; }
        .pcd-search-box input { width: 100%; padding: 6px 12px 6px 32px; border: 1px solid var(--border-color, #d1d8dd); border-radius: 6px; background: var(--bg-light-gray, #f3f5f7); font-size: 11.3px; }
        .pcd-search-box input:focus { background: var(--card-bg, #fff); border-color: var(--primary, #2490ef); outline: none; box-shadow: 0 0 0 3px rgba(36,144,239,0.12); }
        .pcd-search-box i { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-muted, #6b7280); }
        .pcd-pagination { display: flex; justify-content: center; align-items: center; gap: 6px; padding: 10px; }
        .pcd-pagination button { padding: 5px 10px; font-size: 10.8px; border: 1px solid #e2e8f0; background: #fff; border-radius: 4px; cursor: pointer; }
        .pcd-pagination button:disabled { opacity: 0.5; cursor: not-allowed; }
        .pcd-pagination span { font-size: 10.8px; color: #64748b; }
        .pcd-loading { text-align: center; padding: 28px; color: #64748b; }
        .pcd-badge-new { background: var(--primary, #2490ef); color: #fff; font-size: 8.1px; padding: 2px 5px; border-radius: 10px; margin-left: 5px; text-transform: uppercase; }
        .page-actions .inner-group-button .btn i { margin-right: 5px; color: var(--text-muted, #6b7280); }
        </style>
    `);
    $('head').append(style);

    // ── Build page structure ──
    const $page = $(page.body);
    $page.addClass('pcd-container');
    $page.html(`
        <!-- Filters Card -->
        <div class="pcd-card">
            <div class="pcd-card-header">
                <h2><i class="fa fa-filter" style="color:var(--primary, #2490ef)"></i> ${__("Dashboard Filters")}</h2>
                <div style="display:flex;gap:8px;">
                    <button class="pcd-btn pcd-btn-outline" id="pcd-reset-filters">
                        <i class="fa fa-undo"></i> ${__("Reset")}
                    </button>
                </div>
            </div>
            <div class="pcd-card-body">
                <div class="pcd-filters-grid">
                    <div class="pcd-filter-group">
                        <label>${__("Company")}</label>
                        <select id="pcd-filter-company"><option value="">${__("Loading...")}</option></select>
                    </div>
                    <div class="pcd-filter-group">
                        <label>${__("Year")} *</label>
                        <select id="pcd-filter-year">
                            <option value="2026" selected>2026</option>
                            <option value="2025">2025</option>
                        </select>
                    </div>
                    <div class="pcd-filter-group">
                        <label>${__("Month")}</label>
                        <select id="pcd-filter-month">
                            <option value="All">${__("All Months")}</option>
                            <option value="1">${__("January")}</option>
                            <option value="2">${__("February")}</option>
                            <option value="3">${__("March")}</option>
                            <option value="4">${__("April")}</option>
                            <option value="5">${__("May")}</option>
                            <option value="6">${__("June")}</option>
                            <option value="7">${__("July")}</option>
                            <option value="8">${__("August")}</option>
                            <option value="9">${__("September")}</option>
                            <option value="10">${__("October")}</option>
                            <option value="11">${__("November")}</option>
                            <option value="12">${__("December")}</option>
                        </select>
                    </div>
                    <div class="pcd-filter-group">
                        <label>${__("From Date")}</label>
                        <input type="date" id="pcd-filter-from" value="2026-01-01">
                    </div>
                    <div class="pcd-filter-group">
                        <label>${__("To Date")}</label>
                        <input type="date" id="pcd-filter-to" value="2026-04-30">
                    </div>
                    <div class="pcd-filter-group">
                        <label>${__("Custodian (Employee)")}</label>
                        <select id="pcd-filter-custodian"><option value="All">${__("All Custodians")}</option></select>
                    </div>
                    <div class="pcd-filter-group">
                        <label>${__("Project")}</label>
                        <select id="pcd-filter-project"><option value="All">${__("All Projects")}</option></select>
                    </div>
                </div>
            </div>
        </div>

        <!-- KPI Cards -->
        <div class="pcd-kpi-grid" id="pcd-kpi-section">
            <div class="pcd-kpi-card blue">
                <div class="pcd-kpi-label">${__("Total Petty Cash Spent")} <i class="fa fa-coins"></i></div>
                <div class="pcd-kpi-value" id="pcd-kpi-total">SAR 0.00</div>
                <div class="pcd-kpi-subtext">
                    <span class="pcd-badge up"><i class="fa fa-arrow-trend-up"></i> +12.4%</span>
                    <span id="pcd-kpi-receipts">${__("Across 0 Purchase Receipts")}</span>
                </div>
            </div>
            <div class="pcd-kpi-card green">
                <div class="pcd-kpi-label">${__("Total Tax / VAT (15%)")} <i class="fa fa-file-invoice-dollar"></i></div>
                <div class="pcd-kpi-value" id="pcd-kpi-tax">SAR 0.00</div>
                <div class="pcd-kpi-subtext">
                    <span class="pcd-badge neutral" id="pcd-kpi-net">${__("Net: SAR 0.00")}</span>
                </div>
            </div>
            <div class="pcd-kpi-card orange">
                <div class="pcd-kpi-label">${__("Pending Approvals")} <i class="fa fa-clock-rotate-left"></i></div>
                <div class="pcd-kpi-value" id="pcd-kpi-pending">0 ${__("Receipts")}</div>
                <div class="pcd-kpi-subtext">
                    <span style="color:#ff8c00;font-weight:600;" id="pcd-kpi-pending-amt">SAR 0.00</span> ${__("awaiting signature")}
                </div>
            </div>
            <div class="pcd-kpi-card purple">
                <div class="pcd-kpi-label">${__("Active Custodians")} <i class="fa fa-user-shield"></i></div>
                <div class="pcd-kpi-value" id="pcd-kpi-custodians">0 ${__("Employees")}</div>
                <div class="pcd-kpi-subtext">
                    <span id="pcd-kpi-top-custodian">${__("Top: —")}</span>
                </div>
            </div>
            <div class="pcd-kpi-card teal">
                <div class="pcd-kpi-label">${__("Average Receipt Value")} <i class="fa fa-chart-line"></i></div>
                <div class="pcd-kpi-value" id="pcd-kpi-avg">SAR 0.00</div>
                <div class="pcd-kpi-subtext">
                    <span id="pcd-kpi-qty">${__("Total Quantity: 0 Units")}</span>
                </div>
            </div>
        </div>

        <!-- 3 Core Charts -->
        <div class="pcd-dashboard-grid">
            <!-- Custodian -->
            <div class="pcd-card pcd-col-12">
                <div class="pcd-card-header">
                    <h2><i class="fa fa-id-badge" style="color:var(--primary, #2490ef)"></i> ${__("Petty Cash by Custodian")}</h2>
                    <div class="pcd-card-actions">
                        <button class="pcd-icon-btn pcd-download-chart" data-chart="custodian" title="${__("Download PNG")}"><i class="fa fa-download"></i></button>
                        <div class="pcd-tab-switcher">
                            <button class="pcd-tab-btn active" data-card="custodian" data-view="chart"><i class="fa fa-chart-simple"></i> ${__("Chart")}</button>
                            <button class="pcd-tab-btn" data-card="custodian" data-view="table"><i class="fa fa-table"></i> ${__("Table")}</button>
                        </div>
                    </div>
                </div>
                <div class="pcd-card-body">
                    <div id="custodian-chart-view" class="pcd-chart-container"><canvas id="custodianChart"></canvas></div>
                    <div id="custodian-table-view" class="pcd-table-wrapper" style="display:none;">
                        <table class="pcd-table"><thead><tr><th>${__("Custody of")}</th><th class="pcd-text-right">${__("Total Amount (SAR)")}</th></tr></thead><tbody id="custodianTableBody"></tbody></table>
                    </div>
                </div>
            </div>
        </div>

        <div class="pcd-dashboard-grid">
            <!-- Project -->
            <div class="pcd-card pcd-col-6">
                <div class="pcd-card-header">
                    <h2><i class="fa fa-building-user" style="color:#28a745"></i> ${__("Petty Cash by Project Location")}</h2>
                    <div class="pcd-card-actions">
                        <button class="pcd-icon-btn pcd-download-chart" data-chart="project" title="${__("Download PNG")}"><i class="fa fa-download"></i></button>
                        <div class="pcd-tab-switcher">
                            <button class="pcd-tab-btn active" data-card="project" data-view="chart"><i class="fa fa-chart-simple"></i> ${__("Chart")}</button>
                            <button class="pcd-tab-btn" data-card="project" data-view="table"><i class="fa fa-table"></i> ${__("Table")}</button>
                        </div>
                    </div>
                </div>
                <div class="pcd-card-body">
                    <div id="project-chart-view" class="pcd-chart-container"><canvas id="projectChart"></canvas></div>
                    <div id="project-table-view" class="pcd-table-wrapper" style="display:none;">
                        <table class="pcd-table"><thead><tr><th>${__("Project Location")}</th><th class="pcd-text-right">${__("Total Amount (SAR)")}</th></tr></thead><tbody id="projectTableBody"></tbody></table>
                    </div>
                </div>
            </div>
            <!-- Vendor -->
            <div class="pcd-card pcd-col-6">
                <div class="pcd-card-header">
                    <h2><i class="fa fa-store" style="color:#ff8c00"></i> ${__("Top 10 Vendors by Petty Cash")}</h2>
                    <div class="pcd-card-actions">
                        <button class="pcd-icon-btn pcd-download-chart" data-chart="vendor" title="${__("Download PNG")}"><i class="fa fa-download"></i></button>
                        <div class="pcd-tab-switcher">
                            <button class="pcd-tab-btn active" data-card="vendor" data-view="chart"><i class="fa fa-chart-simple"></i> ${__("Chart")}</button>
                            <button class="pcd-tab-btn" data-card="vendor" data-view="table"><i class="fa fa-table"></i> ${__("Table")}</button>
                        </div>
                    </div>
                </div>
                <div class="pcd-card-body">
                    <div id="vendor-chart-view" class="pcd-chart-container"><canvas id="vendorChart"></canvas></div>
                    <div id="vendor-table-view" class="pcd-table-wrapper" style="display:none;">
                        <table class="pcd-table"><thead><tr><th>${__("Top 10 Vendors")}</th><th class="pcd-text-right">${__("Total Amount (SAR)")}</th></tr></thead><tbody id="vendorTableBody"></tbody></table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Trend + Workflow -->
        <div class="pcd-dashboard-grid">
            <div class="pcd-card pcd-col-8">
                <div class="pcd-card-header">
                    <h2><i class="fa fa-chart-area" style="color:var(--primary, #2490ef)"></i> ${__("Monthly Petty Cash Spend Trend")} <span class="pcd-badge-new">${__("Proactive")}</span></h2>
                    <button class="pcd-icon-btn pcd-download-chart" data-chart="trend" title="${__("Download PNG")}"><i class="fa fa-download"></i></button>
                </div>
                <div class="pcd-card-body">
                    <div class="pcd-chart-container pcd-chart-container-sm"><canvas id="trendChart"></canvas></div>
                </div>
            </div>
            <div class="pcd-card pcd-col-4">
                <div class="pcd-card-header">
                    <h2><i class="fa fa-diagram-project" style="color:#743ee2"></i> ${__("Workflow Approval Pipeline")}</h2>
                    <button class="pcd-icon-btn pcd-download-chart" data-chart="status" title="${__("Download PNG")}"><i class="fa fa-download"></i></button>
                </div>
                <div class="pcd-card-body">
                    <div class="pcd-chart-container pcd-chart-container-sm"><canvas id="statusChart"></canvas></div>
                </div>
            </div>
        </div>

        <!-- Live Log Grid -->
        <div class="pcd-card">
            <div class="pcd-card-header">
                <h2><i class="fa fa-list-check" style="color:var(--primary, #2490ef)"></i> ${__("Petty Cash Purchase Receipts (Live Log)")}</h2>
                <div style="display:flex;gap:8px;align-items:center;">
                    <div class="pcd-search-box">
                        <i class="fa fa-search"></i>
                        <input type="text" id="pcd-grid-search" placeholder="${__("Search receipt, custodian, project...")}">
                    </div>
                    <span style="font-size:12px;color:#64748b;" id="pcd-grid-count">${__("Showing 0 of 0 Records")}</span>
                </div>
            </div>
            <div class="pcd-card-body" style="padding:0;">
                <div class="pcd-table-wrapper">
                    <table class="pcd-table" id="pcd-receipts-grid">
                        <thead>
                            <tr>
                                <th>${__("Purchase Receipt")}</th>
                                <th>${__("Posting Date")}</th>
                                <th>${__("Custody Employee")}</th>
                                <th>${__("Custody Manager")}</th>
                                <th>${__("Supplier Name")}</th>
                                <th>${__("Project Name")}</th>
                                <th>${__("Items")}</th>
                                <th class="pcd-text-right">${__("Tax (SAR)")}</th>
                                <th class="pcd-text-right">${__("Grand Total (SAR)")}</th>
                                <th class="pcd-text-center">${__("Workflow State")}</th>
                            </tr>
                        </thead>
                        <tbody id="pcd-receipts-body">
                            <tr><td colspan="10" class="pcd-text-center">${__("Loading...")}</td></tr>
                        </tbody>
                    </table>
                </div>
                <div class="pcd-pagination" id="pcd-pagination"></div>
            </div>
        </div>
    `);

    // ── Load Chart.js if not present ──
    function loadChartJS(callback) {
        if (window.Chart) { callback(); return; }
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
        script.onload = callback;
        document.head.appendChild(script);
    }

    // ── Format currency ──
    function fmtSAR(val) {
        return 'SAR ' + parseFloat(val || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function fmtCompactSAR(val) {
        const n = parseFloat(val || 0);
        if (Math.abs(n) >= 1000000) return 'SAR ' + (n / 1000000).toFixed(1) + 'M';
        if (Math.abs(n) >= 1000) return 'SAR ' + (n / 1000).toFixed(0) + 'K';
        return fmtSAR(n);
    }

    const chartValueLabelsPlugin = {
        id: 'pcdValueLabels',
        afterDatasetsDraw(chart, args, pluginOptions) {
            if (!pluginOptions || !pluginOptions.enabled) return;

            const { ctx, chartArea } = chart;
            ctx.save();
            ctx.font = '600 10px Inter, Arial, sans-serif';
            ctx.fillStyle = '#1f272e';
            ctx.textBaseline = 'middle';

            if (chart.config.type === 'doughnut') {
                const meta = chart.getDatasetMeta(0);
                const data = chart.data.datasets[0].data || [];
                meta.data.forEach((arc, index) => {
                    const value = data[index];
                    if (!value) return;
                    const point = arc.tooltipPosition();
                    ctx.textAlign = 'center';
                    ctx.fillText(value, point.x, point.y);
                });
                ctx.restore();
                return;
            }

            chart.data.datasets.forEach((dataset, datasetIndex) => {
                const meta = chart.getDatasetMeta(datasetIndex);
                meta.data.forEach((element, index) => {
                    const value = dataset.data[index];
                    if (value === null || value === undefined) return;
                    const label = pluginOptions.format === 'sar' ? fmtCompactSAR(value) : String(value);
                    const pos = element.tooltipPosition();

                    if (chart.options.indexAxis === 'y') {
                        ctx.textAlign = 'left';
                        ctx.fillText(label, Math.min(pos.x + 6, chartArea.right - 54), pos.y);
                    } else {
                        ctx.textAlign = 'center';
                        ctx.fillText(label, pos.x, Math.max(pos.y - 10, chartArea.top + 8));
                    }
                });
            });

            ctx.restore();
        }
    };

    // ── Status pill HTML ──
    function statusPill(state) {
        const map = {
            'Draft': { cls: 'pcd-status-draft', icon: 'fa-pen' },
            'Pending Approval': { cls: 'pcd-status-pending', icon: 'fa-clock' },
            'Approved': { cls: 'pcd-status-approved', icon: 'fa-check' },
            'To Bill': { cls: 'pcd-status-tobill', icon: 'fa-file-invoice' }
        };
        const m = map[state] || { cls: 'pcd-status-draft', icon: 'fa-circle' };
        return `<span class="pcd-status-pill ${m.cls}"><i class="fa ${m.icon}"></i> ${__(state || 'Draft')}</span>`;
    }

    // ── Fetch filter options ──
    function loadFilterOptions() {
        frappe.call({
            method: "mkan_customization.mkan_customization.page._petty_cash_executiv._petty_cash_executiv.get_filter_options",
            callback: function(r) {
                if (!r.message) return;
                const d = r.message;

                const $company = $('#pcd-filter-company').empty();
                d.companies.forEach(c => $company.append(`<option value="${c.name}">${c.name}</option>`));

                const $custodian = $('#pcd-filter-custodian').empty().append('<option value="All">' + __("All Custodians") + '</option>');
                d.custodians.forEach(c => $custodian.append(`<option value="${c.name}">${c.employee_name || c.name}</option>`));

                const $project = $('#pcd-filter-project').empty().append('<option value="All">' + __("All Projects") + '</option>');
                d.projects.forEach(p => $project.append(`<option value="${p.name}">${p.project_name || p.name}</option>`));
            }
        });
    }

    // ── Fetch dashboard data ──
    function loadDashboard() {
        const filters = {
            company: $('#pcd-filter-company').val(),
            year: $('#pcd-filter-year').val(),
            month: $('#pcd-filter-month').val(),
            from_date: $('#pcd-filter-from').val(),
            to_date: $('#pcd-filter-to').val(),
            custodian: $('#pcd-filter-custodian').val(),
            project: $('#pcd-filter-project').val()
        };

        frappe.call({
            method: "mkan_customization.mkan_customization.page._petty_cash_executiv._petty_cash_executiv.get_dashboard_data",
            args: filters,
            callback: function(r) {
                if (!r.message) return;
                dashboardData = r.message;
                renderKPIs(dashboardData.kpis);
                renderCharts(dashboardData);
                renderTables(dashboardData);
                loadGrid(0);
            }
        });
    }

    // ── Render KPIs ──
    function renderKPIs(k) {
        $('#pcd-kpi-total').text(fmtSAR(k.total_spent));
        $('#pcd-kpi-receipts').text(__('Across {0} Purchase Receipts', [k.total_receipts]));
        $('#pcd-kpi-tax').text(fmtSAR(k.total_tax));
        $('#pcd-kpi-net').text(__('Net: {0}', [fmtSAR(k.net_total)]));
        $('#pcd-kpi-pending').text(k.pending_count + ' ' + __('Receipts'));
        $('#pcd-kpi-pending-amt').text(fmtSAR(k.pending_amount));
        $('#pcd-kpi-custodians').text(k.active_custodians + ' ' + __('Employees'));
        $('#pcd-kpi-top-custodian').text(__('Top: {0} ({1})', [
            k.top_custodian.custodian || '—',
            fmtSAR(k.top_custodian.amount)
        ]));
        $('#pcd-kpi-avg').text(fmtSAR(k.avg_receipt));
        $('#pcd-kpi-qty').text(__('Total Quantity: {0} Units', [parseFloat(k.total_qty || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})]));
    }

    // ── Render Charts ──
    function renderCharts(data) {
        function wrapChartLabel(label, maxLineLength = 24, maxLines = 2) {
            const words = String(label || __('Unnamed')).split(/\s+/);
            const lines = [];
            let line = '';

            words.forEach(word => {
                const next = line ? `${line} ${word}` : word;
                if (next.length > maxLineLength && line) {
                    lines.push(line);
                    line = word;
                } else {
                    line = next;
                }
            });

            if (line) lines.push(line);
            if (lines.length > maxLines) {
                lines.length = maxLines;
                lines[maxLines - 1] = `${lines[maxLines - 1].slice(0, maxLineLength - 1)}...`;
            }
            return lines;
        }

        const commonBarOpts = {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { top: 4, right: 8, bottom: 0, left: 0 } },
            plugins: { pcdValueLabels: { enabled: false, format: 'sar' }, legend: { display: false }, tooltip: {
                callbacks: {
                    title: function(items) {
                        return items[0] && items[0].label ? items[0].label.replaceAll(',', ' ') : '';
                    },
                    label: function(c) { return fmtSAR(c.raw); }
                }
            }},
            scales: {
                x: {
                    grid: { color: '#eef2f7' },
                    ticks: { font: { size: 10 }, maxRotation: 35, minRotation: 0, autoSkip: true, maxTicksLimit: 8 }
                },
                y: {
                    grid: { display: false },
                    ticks: { font: { size: 10 }, crossAlign: 'center', padding: 8 }
                }
            }
        };

        // Destroy existing
        Object.values(chartInstances).forEach(c => c && c.destroy && c.destroy());

        // Custodian Chart
        const cLabels = data.custodian_chart.map(d => wrapChartLabel(d.label || __('Unnamed'), 26, 2));
        const cValues = data.custodian_chart.map(d => parseFloat(d.value || 0));
        chartInstances.custodian = new Chart(document.getElementById('custodianChart'), {
            type: 'bar',
            data: { labels: cLabels, datasets: [{ label: __('Total Amount (SAR)'), data: cValues, backgroundColor: '#2490ef', borderRadius: 4 }] },
            options: commonBarOpts,
            plugins: [chartValueLabelsPlugin]
        });

        // Project Chart
        const pLabels = data.project_chart.map(d => wrapChartLabel(d.label || __('Unnamed'), 18, 2));
        const pValues = data.project_chart.map(d => parseFloat(d.value || 0));
        chartInstances.project = new Chart(document.getElementById('projectChart'), {
            type: 'bar',
            data: { labels: pLabels, datasets: [{ label: __('Total Amount (SAR)'), data: pValues, backgroundColor: '#28a745', borderRadius: 4 }] },
            options: commonBarOpts,
            plugins: [chartValueLabelsPlugin]
        });

        // Vendor Chart
        const vLabels = data.vendor_chart.map(d => wrapChartLabel(d.label || __('Unnamed'), 22, 2));
        const vValues = data.vendor_chart.map(d => parseFloat(d.value || 0));
        chartInstances.vendor = new Chart(document.getElementById('vendorChart'), {
            type: 'bar',
            data: { labels: vLabels, datasets: [{ label: __('Total Amount (SAR)'), data: vValues, backgroundColor: '#ff8c00', borderRadius: 4 }] },
            options: commonBarOpts,
            plugins: [chartValueLabelsPlugin]
        });

        // Trend Chart
        const tLabels = data.trend_chart.map(d => d.label);
        const tValues = data.trend_chart.map(d => parseFloat(d.value || 0));
        chartInstances.trend = new Chart(document.getElementById('trendChart'), {
            type: 'line',
            data: {
                labels: tLabels,
                datasets: [{
                    label: __('Petty Cash Spend (SAR)'),
                    data: tValues,
                    borderColor: '#2490ef',
                    backgroundColor: 'rgba(36,144,239,0.12)',
                    fill: true,
                    tension: 0.3,
                    borderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { pcdValueLabels: { enabled: false, format: 'sar' }, legend: { display: false } },
                scales: {
                    y: { grid: { color: '#eef2f7' }, ticks: { font: { size: 10 } } },
                    x: { grid: { display: false }, ticks: { font: { size: 10 } } }
                }
            },
            plugins: [chartValueLabelsPlugin]
        });

        // Status Chart
        const sLabels = data.status_chart.map(d => d.label || __('Unknown'));
        const sValues = data.status_chart.map(d => parseInt(d.value || 0));
        const fallbackStatusColors = ['#2490ef', '#28a745', '#ff8c00', '#743ee2', '#00a8a8', '#6b7280', '#e83e8c'];
        const statusColors = {
            'Approved': '#28a745',
            'Pending Approval': '#ff8c00',
            'Pending Approval (Project Manager)': '#2490ef',
            'To Bill': '#743ee2',
            'Draft': '#6b7280',
            'Rejected': '#e03131',
            'Cancelled': '#adb5bd'
        };
        const sColors = sLabels.map((l, i) => statusColors[l] || fallbackStatusColors[i % fallbackStatusColors.length]);
        chartInstances.status = new Chart(document.getElementById('statusChart'), {
            type: 'doughnut',
            data: { labels: sLabels, datasets: [{ data: sValues, backgroundColor: sColors, borderWidth: 0 }] },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '60%',
                plugins: { pcdValueLabels: { enabled: false }, legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 }, padding: 10 } } }
            },
            plugins: [chartValueLabelsPlugin]
        });
    }

    // ── Render Table Views ──
    function renderTables(data) {
        // Custodian Table
        let cHtml = '';
        let cTotal = 0;
        data.custodian_chart.forEach(row => {
            cTotal += parseFloat(row.value || 0);
            cHtml += `<tr><td>${row.label || '—'}</td><td class="pcd-text-right">${fmtSAR(row.value)}</td></tr>`;
        });
        cHtml += `<tr class="total-row"><td>${__("Total")}</td><td class="pcd-text-right">${fmtSAR(cTotal)}</td></tr>`;
        $('#custodianTableBody').html(cHtml);

        // Project Table
        let pHtml = '';
        let pTotal = 0;
        data.project_chart.forEach(row => {
            pTotal += parseFloat(row.value || 0);
            pHtml += `<tr><td>${row.label || '—'}</td><td class="pcd-text-right">${fmtSAR(row.value)}</td></tr>`;
        });
        pHtml += `<tr class="total-row"><td>${__("Total")}</td><td class="pcd-text-right">${fmtSAR(pTotal)}</td></tr>`;
        $('#projectTableBody').html(pHtml);

        // Vendor Table
        let vHtml = '';
        let vTotal = 0;
        data.vendor_chart.forEach(row => {
            vTotal += parseFloat(row.value || 0);
            vHtml += `<tr><td>${row.label || '—'}</td><td class="pcd-text-right">${fmtSAR(row.value)}</td></tr>`;
        });
        vHtml += `<tr class="total-row"><td>${__("Total (Top 10)")}</td><td class="pcd-text-right">${fmtSAR(vTotal)}</td></tr>`;
        $('#vendorTableBody').html(vHtml);
    }

    // ── Load Grid Data ──
    function loadGrid(start) {
        currentPage = start;
        const filters = {
            company: $('#pcd-filter-company').val(),
            year: $('#pcd-filter-year').val(),
            month: $('#pcd-filter-month').val(),
            from_date: $('#pcd-filter-from').val(),
            to_date: $('#pcd-filter-to').val(),
            custodian: $('#pcd-filter-custodian').val(),
            project: $('#pcd-filter-project').val(),
            search_term: $('#pcd-grid-search').val(),
            start: start,
            page_length: pageLength
        };

        frappe.call({
            method: "mkan_customization.mkan_customization.page._petty_cash_executiv._petty_cash_executiv.get_receipts_grid",
            args: filters,
            callback: function(r) {
                if (!r.message) return;
                const rows = r.message.data;
                const total = r.message.total;

                let html = '';
                if (!rows || rows.length === 0) {
                    html = `<tr><td colspan="10" class="pcd-text-center">${__("No records found")}</td></tr>`;
                } else {
                    rows.forEach(row => {
                        html += `<tr>
                            <td><a href="/app/purchase-receipt/${row.purchase_receipt}" style="color:var(--primary, #2490ef);font-weight:600;">${row.purchase_receipt}</a></td>
                            <td>${row.posting_date || '—'}</td>
                            <td>${row.custody_employee || '—'}</td>
                            <td>${row.custody_manager || '—'}</td>
                            <td>${row.supplier_name || '—'}</td>
                            <td>${row.project_name || '—'}</td>
                            <td>${row.items || '—'}</td>
                            <td class="pcd-text-right">${fmtSAR(row.tax_amount)}</td>
                            <td class="pcd-text-right" style="font-weight:600;">${fmtSAR(row.grand_total)}</td>
                            <td class="pcd-text-center">${statusPill(row.workflow_state)}</td>
                        </tr>`;
                    });
                }
                $('#pcd-receipts-body').html(html);

                const end = Math.min(start + pageLength, total);
                $('#pcd-grid-count').text(__('Showing {0}–{1} of {2} Records', [start + 1, end, total]));

                // Pagination with page-size selector and jump
                const totalPages = Math.max(1, Math.ceil(total / pageLength));
                const currentPageNum = Math.floor(start / pageLength) + 1;

                let pgHtml = `<div style="display:flex;gap:8px;align-items:center;justify-content:center;flex-wrap:wrap;">`;
                // First / Prev
                pgHtml += `<button ${currentPage === 0 ? 'disabled' : ''} onclick="window.pcdLoadGrid(0)"><i class=\"fa fa-angle-double-left\"></i></button>`;
                pgHtml += `<button ${currentPage === 0 ? 'disabled' : ''} onclick="window.pcdLoadGrid(${Math.max(0, currentPage - pageLength)})"><i class=\"fa fa-chevron-left\"></i></button>`;

                // Page info + jump input
                pgHtml += `<span style=\"display:flex;gap:8px;align-items:center;\">${__("Page")} <input id=\"pcd-page-input\" type=\"number\" min=1 max=${totalPages} value=${currentPageNum} style=\"width:64px;padding:6px;border:1px solid #e2e8f0;border-radius:4px;\"> ${__("of")} ${totalPages}</span>`;

                // Next / Last
                pgHtml += `<button ${end >= total ? 'disabled' : ''} onclick="window.pcdLoadGrid(${Math.min((totalPages - 1) * pageLength, currentPage + pageLength)})"><i class=\"fa fa-chevron-right\"></i></button>`;
                pgHtml += `<button ${end >= total ? 'disabled' : ''} onclick="window.pcdLoadGrid(${Math.max(0, (totalPages - 1) * pageLength)})"><i class=\"fa fa-angle-double-right\"></i></button>`;

                // Page length selector
                const lengths = [10, 25, 50, 100];
                let sel = `<select id=\"pcd-page-length\" style=\"padding:6px;border:1px solid #e2e8f0;border-radius:4px;\">`;
                lengths.forEach(l => { sel += `<option value=\"${l}\" ${l === pageLength ? 'selected' : ''}>${l} / page</option>`; });
                sel += `</select>`;
                pgHtml += sel;

                pgHtml += `</div>`;
                $('#pcd-pagination').html(pgHtml);

                // Attach in-page handlers (safe to rebind)
                $('#pcd-page-input').off('change').on('change', function() {
                    let v = parseInt($(this).val() || 1, 10);
                    if (isNaN(v) || v < 1) v = 1;
                    if (v > totalPages) v = totalPages;
                    const newStart = (v - 1) * pageLength;
                    window.pcdLoadGrid(newStart);
                });

                $('#pcd-page-input').off('keypress').on('keypress', function(e) {
                    if (e.key === 'Enter') { $(this).trigger('change'); }
                });

                $('#pcd-page-length').off('change').on('change', function() {
                    const newLen = parseInt($(this).val() || pageLength, 10);
                    pageLength = newLen;
                    window.pcdLoadGrid(0);
                });
            }
        });
    }
    window.pcdLoadGrid = loadGrid;

    function buildGridRows() {
        const rows = [];
        const $rows = $('#pcd-receipts-grid tbody tr');
        $rows.each(function() {
            const $cells = $(this).find('td');
            if (!$cells.length) return;
            const row = [];
            $cells.each(function() {
                row.push($(this).text().trim().replace(/\s+/g, ' '));
            });
            rows.push(row);
        });
        return rows;
    }

    function downloadFile(filename, content, mimeType) {
        const blob = new Blob([content], { type: mimeType });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    }

    function downloadChartPNG(chartKey) {
        const chart = chartInstances[chartKey];
        if (!chart) {
            frappe.msgprint(__('Chart is not available yet.'));
            return;
        }

        const valueOptions = chart.options.plugins.pcdValueLabels || {};
        const wasEnabled = valueOptions.enabled;
        valueOptions.enabled = true;
        chart.options.plugins.pcdValueLabels = valueOptions;
        chart.update('none');

        const source = chart.canvas;
        const exportCanvas = document.createElement('canvas');
        exportCanvas.width = source.width;
        exportCanvas.height = source.height;
        const ctx = exportCanvas.getContext('2d');
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
        ctx.drawImage(source, 0, 0);

        const link = document.createElement('a');
        link.href = exportCanvas.toDataURL('image/png');
        link.download = `petty_cash_${chartKey}_chart.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        valueOptions.enabled = wasEnabled;
        chart.options.plugins.pcdValueLabels = valueOptions;
        chart.update('none');
    }

    function exportGridToCSV() {
        const headers = $('#pcd-receipts-grid thead th').map(function() {
            return $(this).text().trim();
        }).get();

        const rows = buildGridRows();
        if (!rows.length) {
            frappe.msgprint(__('No data available to export.'));
            return;
        }

        const escapeCell = value => `"${value.replace(/"/g, '""')}"`;
        const csv = [headers, ...rows].map(r => r.map(escapeCell).join(',')).join('\r\n');
        downloadFile('petty_cash_receipts.csv', '\uFEFF' + csv, 'text/csv;charset=utf-8;');
    }

    function exportGridToExcel() {
        const tableHtml = document.querySelector('#pcd-receipts-grid').outerHTML;
        const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>${tableHtml}</body></html>`;
        downloadFile('petty_cash_receipts.xls', html, 'application/vnd.ms-excel;charset=utf-8;');
    }

    function printGrid() {
        const tableHtml = document.querySelector('#pcd-receipts-grid').outerHTML;
        const title = __('Petty Cash Purchase Receipts');
        const styles = `
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
                th { background: #f3f4f6; }
            </style>`;
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`<!DOCTYPE html><html><head><title>${title}</title>${styles}</head><body><h1>${title}</h1>${tableHtml}</body></html>`);
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
    }

    // ── Tab Switcher ──
    $(document).on('click', '.pcd-tab-btn', function() {
        const card = $(this).data('card');
        const view = $(this).data('view');
        $(`.pcd-tab-btn[data-card="${card}"]`).removeClass('active');
        $(this).addClass('active');
        $(`#${card}-chart-view`).toggle(view === 'chart');
        $(`#${card}-table-view`).toggle(view === 'table');
    });

    $(document).on('click', '.pcd-download-chart', function() {
        downloadChartPNG($(this).data('chart'));
    });

    // ── Event Bindings ──
    $('#pcd-reset-filters').on('click', function() {
        $('#pcd-filter-year').val('2026');
        $('#pcd-filter-month').val('All');
        $('#pcd-filter-from').val('2026-01-01');
        $('#pcd-filter-to').val('2026-04-30');
        $('#pcd-filter-custodian').val('All');
        $('#pcd-filter-project').val('All');
        $('#pcd-grid-search').val('');
        loadDashboard();
    });

    let searchTimeout;
    $('#pcd-grid-search').on('keyup', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => loadGrid(0), 400);
    });

    let filterTimeout;
    function queueDashboardRefresh() {
        clearTimeout(filterTimeout);
        filterTimeout = setTimeout(loadDashboard, 350);
    }

    function syncDateRangeFromYearMonth() {
        const year = $('#pcd-filter-year').val();
        const month = $('#pcd-filter-month').val();

        if (month && month !== 'All') {
            const monthNumber = parseInt(month, 10);
            const lastDay = new Date(year, monthNumber, 0).getDate();
            $('#pcd-filter-from').val(`${year}-${String(monthNumber).padStart(2, '0')}-01`);
            $('#pcd-filter-to').val(`${year}-${String(monthNumber).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`);
        } else {
            $('#pcd-filter-from').val(`${year}-01-01`);
            $('#pcd-filter-to').val(`${year}-12-31`);
        }
    }

    // ── Auto-update date range on year/month change ──
    $('#pcd-filter-year, #pcd-filter-month').on('change', function() {
        syncDateRangeFromYearMonth();
        queueDashboardRefresh();
    });

    $('#pcd-filter-company, #pcd-filter-from, #pcd-filter-to, #pcd-filter-custodian, #pcd-filter-project').on('change', queueDashboardRefresh);

    // ── Initialize ──
    loadChartJS(function() {
        loadFilterOptions();
        loadDashboard();
    });
};
