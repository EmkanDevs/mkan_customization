const PCD_DEFAULT_PAGE_LENGTH = 50;
const PCD_PAGE_LENGTHS = [10, 25, 50, 100];
const PCD_SEARCH_DELAY = 400;
const PCD_FILTER_DELAY = 350;
const PCD_FILTER_ALL = 'All';

const PCD_COLORS = {
	primary: '#2490ef',
	green: '#28a745',
	orange: '#ff8c00',
	purple: '#743ee2',
	teal: '#00a8a8',
	gray: '#6b7280'
};

const PCD_STATUS_META = {
	'Draft': { cls: 'pcd-status-draft', icon: 'fa-pen', color: PCD_COLORS.gray },
	'Pending Approval': { cls: 'pcd-status-pending', icon: 'fa-clock', color: PCD_COLORS.orange },
	'Pending Approval (Project Manager)': { cls: 'pcd-status-pending', icon: 'fa-clock', color: PCD_COLORS.primary },
	'Approved': { cls: 'pcd-status-approved', icon: 'fa-check', color: PCD_COLORS.green },
	'To Bill': { cls: 'pcd-status-tobill', icon: 'fa-file-invoice', color: PCD_COLORS.purple },
	'Rejected': { cls: 'pcd-status-draft', icon: 'fa-xmark', color: '#e03131' },
	'Cancelled': { cls: 'pcd-status-draft', icon: 'fa-ban', color: '#adb5bd' }
};

const PCD_FALLBACK_CHART_COLORS = ['#2490ef', '#28a745', '#ff8c00', '#743ee2', '#00a8a8', '#6b7280', '#e83e8c'];

// ── Generic helpers (pure functions, no DOM/page state) ──

function pcdEscapeHtml(value) {
	return String(value === null || value === undefined ? '' : value)
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#39;');
}

function pcdFmtSAR(val) {
	return 'SAR ' + parseFloat(val || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function pcdFmtCompactSAR(val) {
	const n = parseFloat(val || 0);
	if (Math.abs(n) >= 1000000) return 'SAR ' + (n / 1000000).toFixed(1) + 'M';
	if (Math.abs(n) >= 1000) return 'SAR ' + (n / 1000).toFixed(0) + 'K';
	return pcdFmtSAR(n);
}

function pcdWrapChartLabel(label, maxLineLength = 24, maxLines = 2) {
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

function pcdStatusPill(state) {
	const meta = PCD_STATUS_META[state] || { cls: 'pcd-status-draft', icon: 'fa-circle' };
	return `<span class="pcd-status-pill ${meta.cls}"><i class="fa ${meta.icon}"></i> ${__(state || 'Draft')}</span>`;
}

function pcdDownloadFile(filename, content, mimeType) {
	const blob = new Blob([content], { type: mimeType });
	const link = document.createElement('a');
	link.href = URL.createObjectURL(blob);
	link.download = filename;
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
	URL.revokeObjectURL(link.href);
}

function pcdDefaultDateRange() {
	const year = new Date().getFullYear();
	return {
		year: String(year),
		from_date: `${year}-01-01`,
		to_date: frappe.datetime.get_today()
	};
}

const pcdChartValueLabelsPlugin = {
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
				const label = pluginOptions.format === 'sar' ? pcdFmtCompactSAR(value) : String(value);
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

function pcdCreateHorizontalBarChart(canvasEl, labels, values, color) {
	return new Chart(canvasEl, {
		type: 'bar',
		data: {
			labels: labels.map(l => pcdWrapChartLabel(l, 24, 2)),
			datasets: [{ label: __('Total Amount (SAR)'), data: values, backgroundColor: color, borderRadius: 4 }]
		},
		options: {
			indexAxis: 'y',
			responsive: true,
			maintainAspectRatio: false,
			layout: { padding: { top: 4, right: 8, bottom: 0, left: 0 } },
			plugins: {
				pcdValueLabels: { enabled: false, format: 'sar' },
				legend: { display: false },
				tooltip: {
					callbacks: {
						title: items => (items[0] && items[0].label ? items[0].label.replaceAll(',', ' ') : ''),
						label: c => pcdFmtSAR(c.raw)
					}
				}
			},
			scales: {
				x: { grid: { color: '#eef2f7' }, ticks: { font: { size: 10 }, maxRotation: 35, minRotation: 0, autoSkip: true, maxTicksLimit: 8 } },
				y: { grid: { display: false }, ticks: { font: { size: 10 }, crossAlign: 'center', padding: 8 } }
			}
		},
		plugins: [pcdChartValueLabelsPlugin]
	});
}

function pcdRenderSimpleTable($tbody, rows, totalLabel) {
	const parts = [];
	let total = 0;

	rows.forEach(row => {
		total += parseFloat(row.value || 0);
		parts.push(`<tr><td>${pcdEscapeHtml(row.label || '—')}</td><td class="pcd-text-right">${pcdFmtSAR(row.value)}</td></tr>`);
	});
	parts.push(`<tr class="total-row"><td>${__(totalLabel)}</td><td class="pcd-text-right">${pcdFmtSAR(total)}</td></tr>`);

	$tbody.html(parts.join(''));
}

// ── Dashboard controller ──

class PettyCashDashboard {
	constructor(page) {
		this.page = page;
		this.dashboardData = {};
		this.chartInstances = {};
		this.currentPage = 0;
		this.pageLength = PCD_DEFAULT_PAGE_LENGTH;

		this.buildLayout();
		this.cacheElements();
		this.bindEvents();
		this.loadChartJS(() => {
			this.loadFilterOptions();
			this.loadDashboard();
		});
	}

	// ── Layout ──

	buildLayout() {
		const $page = $(this.page.body);
		$page.addClass('pcd-container');
		const { year, from_date, to_date } = pcdDefaultDateRange();

		$page.html(`
			<div class="pcd-card">
				<div class="pcd-card-header">
					<h2><i class="fa fa-filter" style="color:${PCD_COLORS.primary}"></i> ${__('Dashboard Filters')}</h2>
					<div style="display:flex;gap:8px;">
						<button class="pcd-btn pcd-btn-outline" id="pcd-reset-filters">
							<i class="fa fa-undo"></i> ${__('Reset')}
						</button>
					</div>
				</div>
				<div class="pcd-card-body">
					<div class="pcd-filters-grid">
						<div class="pcd-filter-group">
							<label>${__('Company')}</label>
							<select id="pcd-filter-company"><option value="">${__('Loading...')}</option></select>
						</div>
						<div class="pcd-filter-group">
							<label>${__('Year')} *</label>
							<select id="pcd-filter-year">${this.buildYearOptions(year)}</select>
						</div>
						<div class="pcd-filter-group">
							<label>${__('Month')}</label>
							<select id="pcd-filter-month">${this.buildMonthOptions()}</select>
						</div>
						<div class="pcd-filter-group">
							<label>${__('From Date')}</label>
							<input type="date" id="pcd-filter-from" value="${from_date}">
						</div>
						<div class="pcd-filter-group">
							<label>${__('To Date')}</label>
							<input type="date" id="pcd-filter-to" value="${to_date}">
						</div>
						<div class="pcd-filter-group">
							<label>${__('Custodian (Employee)')}</label>
							<select id="pcd-filter-custodian"><option value="All">${__('All Custodians')}</option></select>
						</div>
						<div class="pcd-filter-group">
							<label>${__('Project')}</label>
							<select id="pcd-filter-project"><option value="All">${__('All Projects')}</option></select>
						</div>
					</div>
				</div>
			</div>

			<div class="pcd-kpi-grid" id="pcd-kpi-section">
				<div class="pcd-kpi-card blue">
					<div class="pcd-kpi-label">${__('Total Petty Cash Spent')} <i class="fa fa-coins"></i></div>
					<div class="pcd-kpi-value" id="pcd-kpi-total">SAR 0.00</div>
					<div class="pcd-kpi-subtext">
						<span id="pcd-kpi-receipts">${__('Across 0 Purchase Receipts')}</span>
					</div>
				</div>
				<div class="pcd-kpi-card green">
					<div class="pcd-kpi-label">${__('Total Tax / VAT')} <i class="fa fa-file-invoice-dollar"></i></div>
					<div class="pcd-kpi-value" id="pcd-kpi-tax">SAR 0.00</div>
					<div class="pcd-kpi-subtext">
						<span class="pcd-badge neutral" id="pcd-kpi-net">${__('Net: SAR 0.00')}</span>
					</div>
				</div>
				<div class="pcd-kpi-card orange">
					<div class="pcd-kpi-label">${__('Pending Approvals')} <i class="fa fa-clock-rotate-left"></i></div>
					<div class="pcd-kpi-value" id="pcd-kpi-pending">0 ${__('Receipts')}</div>
					<div class="pcd-kpi-subtext">
						<span style="color:${PCD_COLORS.orange};font-weight:600;" id="pcd-kpi-pending-amt">SAR 0.00</span> ${__('awaiting signature')}
					</div>
				</div>
				<div class="pcd-kpi-card purple">
					<div class="pcd-kpi-label">${__('Active Custodians')} <i class="fa fa-user-shield"></i></div>
					<div class="pcd-kpi-value" id="pcd-kpi-custodians">0 ${__('Employees')}</div>
					<div class="pcd-kpi-subtext">
						<span id="pcd-kpi-top-custodian">${__('Top: —')}</span>
					</div>
				</div>
				<div class="pcd-kpi-card teal">
					<div class="pcd-kpi-label">${__('Average Receipt Value')} <i class="fa fa-chart-line"></i></div>
					<div class="pcd-kpi-value" id="pcd-kpi-avg">SAR 0.00</div>
					<div class="pcd-kpi-subtext">
						<span id="pcd-kpi-qty">${__('Total Quantity: 0 Units')}</span>
					</div>
				</div>
			</div>

			<div class="pcd-dashboard-grid">
				<div class="pcd-card pcd-col-12">
					<div class="pcd-card-header">
						<h2><i class="fa fa-id-badge" style="color:${PCD_COLORS.primary}"></i> ${__('Petty Cash by Custodian')}</h2>
						<div class="pcd-card-actions">
							<button class="pcd-icon-btn pcd-download-chart" data-chart="custodian" title="${__('Download PNG')}"><i class="fa fa-download"></i></button>
							<div class="pcd-tab-switcher">
								<button class="pcd-tab-btn active" data-card="custodian" data-view="chart"><i class="fa fa-chart-simple"></i> ${__('Chart')}</button>
								<button class="pcd-tab-btn" data-card="custodian" data-view="table"><i class="fa fa-table"></i> ${__('Table')}</button>
							</div>
						</div>
					</div>
					<div class="pcd-card-body">
						<div id="custodian-chart-view" class="pcd-chart-container"><canvas id="custodianChart"></canvas></div>
						<div id="custodian-table-view" class="pcd-table-wrapper" style="display:none;">
							<table class="pcd-table"><thead><tr><th>${__('Custody of')}</th><th class="pcd-text-right">${__('Total Amount (SAR)')}</th></tr></thead><tbody id="custodianTableBody"></tbody></table>
						</div>
					</div>
				</div>
			</div>

			<div class="pcd-dashboard-grid">
				<div class="pcd-card pcd-col-6">
					<div class="pcd-card-header">
						<h2><i class="fa fa-building-user" style="color:${PCD_COLORS.green}"></i> ${__('Petty Cash by Project Location')}</h2>
						<div class="pcd-card-actions">
							<button class="pcd-icon-btn pcd-download-chart" data-chart="project" title="${__('Download PNG')}"><i class="fa fa-download"></i></button>
							<div class="pcd-tab-switcher">
								<button class="pcd-tab-btn active" data-card="project" data-view="chart"><i class="fa fa-chart-simple"></i> ${__('Chart')}</button>
								<button class="pcd-tab-btn" data-card="project" data-view="table"><i class="fa fa-table"></i> ${__('Table')}</button>
							</div>
						</div>
					</div>
					<div class="pcd-card-body">
						<div id="project-chart-view" class="pcd-chart-container"><canvas id="projectChart"></canvas></div>
						<div id="project-table-view" class="pcd-table-wrapper" style="display:none;">
							<table class="pcd-table"><thead><tr><th>${__('Project Location')}</th><th class="pcd-text-right">${__('Total Amount (SAR)')}</th></tr></thead><tbody id="projectTableBody"></tbody></table>
						</div>
					</div>
				</div>
				<div class="pcd-card pcd-col-6">
					<div class="pcd-card-header">
						<h2><i class="fa fa-store" style="color:${PCD_COLORS.orange}"></i> ${__('Top 10 Vendors by Petty Cash')}</h2>
						<div class="pcd-card-actions">
							<button class="pcd-icon-btn pcd-download-chart" data-chart="vendor" title="${__('Download PNG')}"><i class="fa fa-download"></i></button>
							<div class="pcd-tab-switcher">
								<button class="pcd-tab-btn active" data-card="vendor" data-view="chart"><i class="fa fa-chart-simple"></i> ${__('Chart')}</button>
								<button class="pcd-tab-btn" data-card="vendor" data-view="table"><i class="fa fa-table"></i> ${__('Table')}</button>
							</div>
						</div>
					</div>
					<div class="pcd-card-body">
						<div id="vendor-chart-view" class="pcd-chart-container"><canvas id="vendorChart"></canvas></div>
						<div id="vendor-table-view" class="pcd-table-wrapper" style="display:none;">
							<table class="pcd-table"><thead><tr><th>${__('Top 10 Vendors')}</th><th class="pcd-text-right">${__('Total Amount (SAR)')}</th></tr></thead><tbody id="vendorTableBody"></tbody></table>
						</div>
					</div>
				</div>
			</div>

			<div class="pcd-dashboard-grid">
				<div class="pcd-card pcd-col-8">
					<div class="pcd-card-header">
						<h2><i class="fa fa-chart-area" style="color:${PCD_COLORS.primary}"></i> ${__('Monthly Petty Cash Spend Trend')}</h2>
						<button class="pcd-icon-btn pcd-download-chart" data-chart="trend" title="${__('Download PNG')}"><i class="fa fa-download"></i></button>
					</div>
					<div class="pcd-card-body">
						<div class="pcd-chart-container pcd-chart-container-sm"><canvas id="trendChart"></canvas></div>
					</div>
				</div>
				<div class="pcd-card pcd-col-4">
					<div class="pcd-card-header">
						<h2><i class="fa fa-diagram-project" style="color:${PCD_COLORS.purple}"></i> ${__('Workflow Approval Pipeline')}</h2>
						<button class="pcd-icon-btn pcd-download-chart" data-chart="status" title="${__('Download PNG')}"><i class="fa fa-download"></i></button>
					</div>
					<div class="pcd-card-body">
						<div class="pcd-chart-container pcd-chart-container-sm"><canvas id="statusChart"></canvas></div>
					</div>
				</div>
			</div>

			<div class="pcd-card">
				<div class="pcd-card-header">
					<h2><i class="fa fa-list-check" style="color:${PCD_COLORS.primary}"></i> ${__('Petty Cash Purchase Receipts (Live Log)')}</h2>
					<div style="display:flex;gap:8px;align-items:center;">
						<div class="pcd-search-box">
							<i class="fa fa-search"></i>
							<input type="text" id="pcd-grid-search" placeholder="${__('Search receipt, custodian, project...')}">
						</div>
						<span style="font-size:12px;color:${PCD_COLORS.gray};" id="pcd-grid-count">${__('Showing 0 of 0 Records')}</span>
					</div>
				</div>
				<div class="pcd-card-body" style="padding:0;">
					<div class="pcd-table-wrapper">
						<table class="pcd-table" id="pcd-receipts-grid">
							<thead>
								<tr>
									<th>${__('Purchase Receipt')}</th>
									<th>${__('Posting Date')}</th>
									<th>${__('Custody Employee')}</th>
									<th>${__('Custody Manager')}</th>
									<th>${__('Supplier Name')}</th>
									<th>${__('Project Name')}</th>
									<th>${__('Items')}</th>
									<th class="pcd-text-right">${__('Tax (SAR)')}</th>
									<th class="pcd-text-right">${__('Grand Total (SAR)')}</th>
									<th class="pcd-text-center">${__('Workflow State')}</th>
								</tr>
							</thead>
							<tbody id="pcd-receipts-body">
								<tr><td colspan="10" class="pcd-text-center">${__('Loading...')}</td></tr>
							</tbody>
						</table>
					</div>
					<div class="pcd-pagination" id="pcd-pagination"></div>
				</div>
			</div>
		`);
	}

	buildYearOptions(defaultYear) {
		const current = new Date().getFullYear();
		const years = [current + 1, current, current - 1];
		return years.map(y => `<option value="${y}" ${String(y) === String(defaultYear) ? 'selected' : ''}>${y}</option>`).join('');
	}

	buildMonthOptions() {
		const months = [
			'January', 'February', 'March', 'April', 'May', 'June',
			'July', 'August', 'September', 'October', 'November', 'December'
		];
		let html = `<option value="All">${__('All Months')}</option>`;
		months.forEach((m, i) => {
			html += `<option value="${i + 1}">${__(m)}</option>`;
		});
		return html;
	}

	// ── Element cache ──

	cacheElements() {
		this.$el = {
			company: $('#pcd-filter-company'),
			year: $('#pcd-filter-year'),
			month: $('#pcd-filter-month'),
			from: $('#pcd-filter-from'),
			to: $('#pcd-filter-to'),
			custodian: $('#pcd-filter-custodian'),
			project: $('#pcd-filter-project'),
			search: $('#pcd-grid-search'),
			gridBody: $('#pcd-receipts-body'),
			gridCount: $('#pcd-grid-count'),
			pagination: $('#pcd-pagination')
		};
	}

	// ── Chart.js loader ──

	loadChartJS(callback) {
		if (window.Chart) { callback(); return; }
		const script = document.createElement('script');
		script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
		script.onload = callback;
		document.head.appendChild(script);
	}

	// ── Data loading ──

	getFilters() {
		return {
			company: this.$el.company.val(),
			year: this.$el.year.val(),
			month: this.$el.month.val(),
			from_date: this.$el.from.val(),
			to_date: this.$el.to.val(),
			custodian: this.$el.custodian.val(),
			project: this.$el.project.val()
		};
	}

	validateFilters(filters) {
		if (filters.from_date && filters.to_date && filters.from_date > filters.to_date) {
			frappe.msgprint(__('"From Date" cannot be after "To Date".'));
			return false;
		}
		return true;
	}

	loadFilterOptions() {
		frappe.call({
			method: 'mkan_customization.mkan_customization.page._petty_cash_executiv._petty_cash_executiv.get_filter_options'
		}).then(r => {
			if (!r.message) return;
			const d = r.message;

			const companyOptions = d.companies.map(c => `<option value="${c.name}">${pcdEscapeHtml(c.name)}</option>`).join('');
			this.$el.company.html(companyOptions);

			const custodianOptions = [`<option value="All">${__('All Custodians')}</option>`]
				.concat(d.custodians.map(c => `<option value="${c.name}">${pcdEscapeHtml(c.employee_name || c.name)}</option>`))
				.join('');
			this.$el.custodian.html(custodianOptions);

			const projectOptions = [`<option value="All">${__('All Projects')}</option>`]
				.concat(d.projects.map(p => `<option value="${p.name}">${pcdEscapeHtml(p.project_name || p.name)}</option>`))
				.join('');
			this.$el.project.html(projectOptions);
		}).catch(() => {
			frappe.msgprint(__('Could not load filter options.'));
		});
	}

	loadDashboard() {
		const filters = this.getFilters();
		if (!this.validateFilters(filters)) return;

		frappe.call({
			method: 'mkan_customization.mkan_customization.page._petty_cash_executiv._petty_cash_executiv.get_dashboard_data',
			args: filters,
			freeze: true,
			freeze_message: __('Loading Dashboard...')
		}).then(r => {
			if (!r.message) return;
			this.dashboardData = r.message;
			this.renderKPIs(this.dashboardData.kpis);
			this.renderCharts(this.dashboardData);
			this.renderTables(this.dashboardData);
			this.loadGrid(0);
		}).catch(() => {
			frappe.msgprint(__('Could not load dashboard data. Please try again.'));
		});
	}

	loadGrid(start) {
		this.currentPage = start;
		const filters = Object.assign(this.getFilters(), {
			search_term: this.$el.search.val(),
			start,
			page_length: this.pageLength
		});

		frappe.call({
			method: 'mkan_customization.mkan_customization.page._petty_cash_executiv._petty_cash_executiv.get_receipts_grid',
			args: filters
		}).then(r => {
			if (!r.message) return;
			this.renderGridRows(r.message.data);
			this.renderPagination(start, r.message.total);
		}).catch(() => {
			this.$el.gridBody.html(`<tr><td colspan="10" class="pcd-text-center">${__('Could not load records.')}</td></tr>`);
		});
	}

	// ── Rendering: KPIs ──

	renderKPIs(k) {
		$('#pcd-kpi-total').text(pcdFmtSAR(k.total_spent));
		$('#pcd-kpi-receipts').text(__('Across {0} Purchase Receipts', [k.total_receipts]));
		$('#pcd-kpi-tax').text(pcdFmtSAR(k.total_tax));
		$('#pcd-kpi-net').text(__('Net: {0}', [pcdFmtSAR(k.net_total)]));
		$('#pcd-kpi-pending').text(k.pending_count + ' ' + __('Receipts'));
		$('#pcd-kpi-pending-amt').text(pcdFmtSAR(k.pending_amount));
		$('#pcd-kpi-custodians').text(k.active_custodians + ' ' + __('Employees'));
		$('#pcd-kpi-top-custodian').text(__('Top: {0} ({1})', [
			k.top_custodian.custodian || '—',
			pcdFmtSAR(k.top_custodian.amount)
		]));
		$('#pcd-kpi-avg').text(pcdFmtSAR(k.avg_receipt));
		$('#pcd-kpi-qty').text(__('Total Quantity: {0} Units', [
			parseFloat(k.total_qty || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
		]));
	}

	// ── Rendering: Charts ──

	renderCharts(data) {
		Object.values(this.chartInstances).forEach(c => c && c.destroy && c.destroy());
		this.chartInstances = {};

		this.chartInstances.custodian = pcdCreateHorizontalBarChart(
			document.getElementById('custodianChart'),
			data.custodian_chart.map(d => d.label),
			data.custodian_chart.map(d => parseFloat(d.value || 0)),
			PCD_COLORS.primary
		);

		this.chartInstances.project = pcdCreateHorizontalBarChart(
			document.getElementById('projectChart'),
			data.project_chart.map(d => d.label),
			data.project_chart.map(d => parseFloat(d.value || 0)),
			PCD_COLORS.green
		);

		this.chartInstances.vendor = pcdCreateHorizontalBarChart(
			document.getElementById('vendorChart'),
			data.vendor_chart.map(d => d.label),
			data.vendor_chart.map(d => parseFloat(d.value || 0)),
			PCD_COLORS.orange
		);

		this.chartInstances.trend = new Chart(document.getElementById('trendChart'), {
			type: 'line',
			data: {
				labels: data.trend_chart.map(d => d.label),
				datasets: [{
					label: __('Petty Cash Spend (SAR)'),
					data: data.trend_chart.map(d => parseFloat(d.value || 0)),
					borderColor: PCD_COLORS.primary,
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
			plugins: [pcdChartValueLabelsPlugin]
		});

		const sLabels = data.status_chart.map(d => d.label || __('Unknown'));
		const sColors = sLabels.map((l, i) => (PCD_STATUS_META[l] && PCD_STATUS_META[l].color) || PCD_FALLBACK_CHART_COLORS[i % PCD_FALLBACK_CHART_COLORS.length]);

		this.chartInstances.status = new Chart(document.getElementById('statusChart'), {
			type: 'doughnut',
			data: {
				labels: sLabels,
				datasets: [{ data: data.status_chart.map(d => parseInt(d.value || 0, 10)), backgroundColor: sColors, borderWidth: 0 }]
			},
			options: {
				responsive: true,
				maintainAspectRatio: false,
				cutout: '60%',
				plugins: { pcdValueLabels: { enabled: false }, legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 }, padding: 10 } } }
			},
			plugins: [pcdChartValueLabelsPlugin]
		});
	}

	// ── Rendering: Tables ──

	renderTables(data) {
		pcdRenderSimpleTable($('#custodianTableBody'), data.custodian_chart, 'Total');
		pcdRenderSimpleTable($('#projectTableBody'), data.project_chart, 'Total');
		pcdRenderSimpleTable($('#vendorTableBody'), data.vendor_chart, 'Total (Top 10)');
	}

	// ── Rendering: Grid ──

	renderGridRows(rows) {
		if (!rows || rows.length === 0) {
			this.$el.gridBody.html(`<tr><td colspan="10" class="pcd-text-center">${__('No records found')}</td></tr>`);
			return;
		}

		const parts = rows.map(row => `<tr>
			<td><a href="/app/purchase-receipt/${encodeURIComponent(row.purchase_receipt)}" style="color:${PCD_COLORS.primary};font-weight:600;">${pcdEscapeHtml(row.purchase_receipt)}</a></td>
			<td>${pcdEscapeHtml(row.posting_date || '—')}</td>
			<td>${pcdEscapeHtml(row.custody_employee || '—')}</td>
			<td>${pcdEscapeHtml(row.custody_manager || '—')}</td>
			<td>${pcdEscapeHtml(row.supplier_name || '—')}</td>
			<td>${pcdEscapeHtml(row.project_name || '—')}</td>
			<td>${pcdEscapeHtml(row.items || '—')}</td>
			<td class="pcd-text-right">${pcdFmtSAR(row.tax_amount)}</td>
			<td class="pcd-text-right" style="font-weight:600;">${pcdFmtSAR(row.grand_total)}</td>
			<td class="pcd-text-center">${pcdStatusPill(row.workflow_state)}</td>
		</tr>`);

		this.$el.gridBody.html(parts.join(''));
	}

	renderPagination(start, total) {
		const pageLength = this.pageLength;
		const end = Math.min(start + pageLength, total);
		this.$el.gridCount.text(__('Showing {0}–{1} of {2} Records', [total ? start + 1 : 0, end, total]));

		const totalPages = Math.max(1, Math.ceil(total / pageLength));
		const currentPageNum = Math.floor(start / pageLength) + 1;

		const parts = ['<div style="display:flex;gap:8px;align-items:center;justify-content:center;flex-wrap:wrap;">'];
		parts.push(`<button data-start="0" ${start === 0 ? 'disabled' : ''}><i class="fa fa-angle-double-left"></i></button>`);
		parts.push(`<button data-start="${Math.max(0, start - pageLength)}" ${start === 0 ? 'disabled' : ''}><i class="fa fa-chevron-left"></i></button>`);
		parts.push(`<span style="display:flex;gap:8px;align-items:center;">${__('Page')} <input id="pcd-page-input" type="number" min="1" max="${totalPages}" value="${currentPageNum}" style="width:64px;padding:6px;border:1px solid #e2e8f0;border-radius:4px;"> ${__('of')} ${totalPages}</span>`);
		parts.push(`<button data-start="${Math.min((totalPages - 1) * pageLength, start + pageLength)}" ${end >= total ? 'disabled' : ''}><i class="fa fa-chevron-right"></i></button>`);
		parts.push(`<button data-start="${Math.max(0, (totalPages - 1) * pageLength)}" ${end >= total ? 'disabled' : ''}><i class="fa fa-angle-double-right"></i></button>`);

		let sel = '<select id="pcd-page-length" style="padding:6px;border:1px solid #e2e8f0;border-radius:4px;">';
		PCD_PAGE_LENGTHS.forEach(l => { sel += `<option value="${l}" ${l === pageLength ? 'selected' : ''}>${l} / page</option>`; });
		sel += '</select>';
		parts.push(sel, '</div>');

		this.$el.pagination.html(parts.join(''));
	}

	// ── Export / print ──

	exportGridToExcel() {
		const tableHtml = document.querySelector('#pcd-receipts-grid').outerHTML;
		const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"></head><body>${tableHtml}</body></html>`;
		pcdDownloadFile('petty_cash_receipts.xls', html, 'application/vnd.ms-excel;charset=utf-8;');
	}

	printGrid() {
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

	downloadChartPNG(chartKey) {
		const chart = this.chartInstances[chartKey];
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

	// ── Events ──

	bindEvents() {
		const $page = $(this.page.body);

		$page.on('click', '.pcd-tab-btn', function () {
			const card = $(this).data('card');
			const view = $(this).data('view');
			$(`.pcd-tab-btn[data-card="${card}"]`).removeClass('active');
			$(this).addClass('active');
			$(`#${card}-chart-view`).toggle(view === 'chart');
			$(`#${card}-table-view`).toggle(view === 'table');
		});

		$page.on('click', '.pcd-download-chart', e => {
			this.downloadChartPNG($(e.currentTarget).data('chart'));
		});

		$page.on('click', '#pcd-pagination button[data-start]', e => {
			const start = parseInt($(e.currentTarget).data('start'), 10);
			if (!isNaN(start)) this.loadGrid(start);
		});

		$page.on('change', '#pcd-page-input', e => {
			const totalRecords = this.dashboardData && this.dashboardData.kpis ? this.dashboardData.kpis.total_receipts : 0;
			const totalPages = Math.max(1, Math.ceil(totalRecords / this.pageLength));
			let v = parseInt($(e.currentTarget).val() || 1, 10);
			if (isNaN(v) || v < 1) v = 1;
			if (v > totalPages) v = totalPages;
			this.loadGrid((v - 1) * this.pageLength);
		});
		$page.on('keypress', '#pcd-page-input', e => {
			if (e.key === 'Enter') $(e.currentTarget).trigger('change');
		});

		$page.on('change', '#pcd-page-length', e => {
			this.pageLength = parseInt($(e.currentTarget).val(), 10) || PCD_DEFAULT_PAGE_LENGTH;
			this.loadGrid(0);
		});

		$page.on('click', '#pcd-reset-filters', () => this.resetFilters());

		let searchTimeout;
		$page.on('input', '#pcd-grid-search', () => {
			clearTimeout(searchTimeout);
			searchTimeout = setTimeout(() => this.loadGrid(0), PCD_SEARCH_DELAY);
		});

		let filterTimeout;
		const queueDashboardRefresh = () => {
			clearTimeout(filterTimeout);
			filterTimeout = setTimeout(() => this.loadDashboard(), PCD_FILTER_DELAY);
		};

		$page.on('change', '#pcd-filter-year, #pcd-filter-month', () => {
			this.syncDateRangeFromYearMonth();
			queueDashboardRefresh();
		});

		$page.on('change', '#pcd-filter-company, #pcd-filter-from, #pcd-filter-to, #pcd-filter-custodian, #pcd-filter-project', queueDashboardRefresh);
	}

	resetFilters() {
		const { year, from_date, to_date } = pcdDefaultDateRange();
		this.$el.year.val(year);
		this.$el.month.val('All');
		this.$el.from.val(from_date);
		this.$el.to.val(to_date);
		this.$el.custodian.val('All');
		this.$el.project.val('All');
		this.$el.search.val('');
		this.loadDashboard();
	}

	syncDateRangeFromYearMonth() {
		const year = this.$el.year.val();
		const month = this.$el.month.val();

		if (month && month !== PCD_FILTER_ALL) {
			const monthNumber = parseInt(month, 10);
			const lastDay = new Date(year, monthNumber, 0).getDate();
			this.$el.from.val(`${year}-${String(monthNumber).padStart(2, '0')}-01`);
			this.$el.to.val(`${year}-${String(monthNumber).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`);
		} else {
			this.$el.from.val(`${year}-01-01`);
			this.$el.to.val(`${year}-12-31`);
		}
	}
}

frappe.pages['-petty-cash-executiv'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Petty Cash Executive Dashboard'),
		single_column: true
	});

	const dashboard = new PettyCashDashboard(page);

	const $refreshBtn = page.add_inner_button(__('Refresh'), () => dashboard.loadDashboard());
	const $printBtn = page.add_inner_button(__('Print'), () => dashboard.printGrid());
	const $excelBtn = page.add_inner_button(__('Excel'), () => dashboard.exportGridToExcel());
	$refreshBtn.html(`<i class="fa fa-refresh"></i> ${__('Refresh')}`);
	$excelBtn.html(`<i class="fa fa-file-excel-o"></i> ${__('Excel')}`);
	$printBtn.html(`<i class="fa fa-print"></i> ${__('Print')}`);
};