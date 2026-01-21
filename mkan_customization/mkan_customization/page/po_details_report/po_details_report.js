frappe.pages['po-details-report'].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'PO Details Report',
		single_column: true
	});

	// Add enhanced custom CSS
	frappe.dom.set_style(
		'.status-badge { display: inline-flex; align-items: center; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }' +
		'.doc-box { transition: all 0.3s ease; cursor: pointer; }' +
		'.doc-box:hover { transform: translateY(-2px); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }' +
		'.loading-spinner { border: 3px solid #f3f3f3; border-top: 3px solid #3498db; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 0 auto; }' +
		'@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }' +
		'.po-report-container { padding: 20px; background: #f8f9fa; }' +
		/* Enhanced styles for cards */
		'.po-card { margin-bottom: 20px !important; transition: all 0.3s ease; border-radius: 8px !important; }' +
		'.po-card:hover { box-shadow: 0 8px 16px rgba(0,0,0,0.1) !important; }' +
		'.card-header { cursor: pointer; padding: 16px 20px !important; }' +
		'.card-body { padding: 20px !important; }' +
		'.card-header h5 { margin: 0; }' +
		/* Document flow layout from image */
		'.doc-flow-track { display: flex; overflow-x: auto; padding: 20px 0; gap: 15px; margin-bottom: 25px; }' +
		'.doc-flow-step { min-width: 150px; flex-shrink: 0; }' +
		'.step-number { width: 30px; height: 30px; background: #3498db; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-bottom: 10px; }' +
		'.step-title { font-weight: 600; margin-bottom: 15px; color: #2c3e50; }' +
		'.step-content { min-height: 100px; }' +
		'.flow-arrow {font-size: 22px;color: #95a5a6;display: flex;align-items: center;}' +

		/* Status colors - Dull version */
		'.status-draft { background-color: rgba(149, 165, 166, 0.15) !important; color: #7f8c8d !important; border-color: rgba(149, 165, 166, 0.4) !important; }' +
		'.status-pending { background-color: rgba(243, 156, 18, 0.15) !important; color: #d68910 !important; border-color: rgba(243, 156, 18, 0.4) !important; }' +
		'.status-approved { background-color: rgba(39, 174, 96, 0.15) !important; color: #27ae60 !important; border-color: rgba(39, 174, 96, 0.4) !important; }' +
		'.status-cancelled { background-color: rgba(231, 76, 60, 0.15) !important; color: #c0392b !important; border-color: rgba(231, 76, 60, 0.4) !important; }' +
		'.status-received { background-color: rgba(52, 152, 219, 0.15) !important; color: #2980b9 !important; border-color: rgba(52, 152, 219, 0.4) !important; }' +
		'.status-submitted { background-color: rgba(241, 196, 15, 0.15) !important; color: #f39c12 !important; border-color: rgba(241, 196, 15, 0.4) !important; }' +
		'.status-completed { background-color: rgba(46, 204, 113, 0.15) !important; color: #27ae60 !important; border-color: rgba(46, 204, 113, 0.4) !important; }' +
		'.status-paid { background-color: rgba(155, 89, 182, 0.15) !important; color: #8e44ad !important; border-color: rgba(155, 89, 182, 0.4) !important; }' +
		'.status-quotation { background-color: rgba(52, 152, 219, 0.15) !important; color: #2980b9 !important; border-color: rgba(52, 152, 219, 0.4) !important; }' +
		'.status-ordered { background-color: rgba(39, 174, 96, 0.15) !important; color: #27ae60 !important; border-color: rgba(39, 174, 96, 0.4) !important; }' +
		'.status-awarded { background-color: rgba(155, 89, 182, 0.15) !important; color: #8e44ad !important; border-color: rgba(155, 89, 182, 0.4) !important; }' +
		/* Workflow border colors */
		'.border-draft { border-left: 5px solid rgba(149, 165, 166, 0.7) !important; }' +
		'.border-pending { border-left: 5px solid rgba(243, 156, 18, 0.7) !important; }' +
		'.border-approved { border-left: 5px solid rgba(39, 174, 96, 0.7) !important; }' +
		'.border-cancelled { border-left: 5px solid rgba(231, 76, 60, 0.7) !important; }' +
		'.border-received { border-left: 5px solid rgba(52, 152, 219, 0.7) !important; }' +
		/* Workflow states on card */
		'.workflow-states { display: flex; gap: 10px; flex-wrap: wrap; }' +
		'.workflow-state-item { background: #f8f9fa; border-radius: 4px; padding: 4px 8px; font-size: 12px; }' +
		'.workflow-state-label { color: #6c757d; }' +
		'.workflow-state-value { font-weight: 600; }' +
		/* Count badges */
		'.count-badge { background-color: #e74c3c; color: white; border-radius: 10px; padding: 1px 6px; font-size: 11px; font-weight: bold; margin-left: 5px; }' +
		'.empty-doc { color: #95a5a6; font-style: italic; font-size: 0.9rem; padding: 10px; background: #f8f9fa; border-radius: 4px; }' +
		/* Collapsible items */
		'.items-toggle { cursor: pointer; color: #3498db; font-weight: 600; display: flex; align-items: center; gap: 5px; }' +
		'.items-container { display: none; margin-top: 15px; }' +
		'.items-container.expanded { display: block; }' +
		/* Card styles matching image */
		'.mr-card { border: 1px solid #dee2e6; border-radius: 8px; padding: 15px; margin-bottom: 15px; background: white; }' +
		'.mr-id { font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 8px; }' +
		'.mr-meta { color: #6c757d; font-size: 14px; margin-bottom: 10px; }' +
		'.mr-workflow-status { display: flex; gap: 20px; margin-top: 10px; }' +
		'.status-section { flex: 1; }' +
		'.status-label { font-size: 12px; color: #6c757d; margin-bottom: 4px; }' +
		'.status-value { font-weight: 600; }' +
		/* RFQ and BT specific */
		'.child-row { margin-left: 30px; border-left: 2px solid #dee2e6; padding-left: 15px; margin-top: 10px; }' +
		'.child-doc { font-size: 14px; color: #6c757d; }'
	);

	// Create HTML structure matching the image
	$(page.main).html(
		'<div class="po-report-container">' +
		'<div class="d-flex justify-content-between align-items-center mb-4">' +
		'<h3 style="margin: 0;">Purchase Order Details Report</h3>' +
		'<button id="btn-refresh" class="btn btn-success">' +
		'<i class="fa fa-refresh"></i> Refresh' +
		'</button>' +
		'</div>' +
		'<hr style="margin: 30px 0;">' +

		'<!-- Filters Section -->' +
		'<div class="card mb-4">' +
		'<div class="card-body">' +
		'<h5 class="card-title mb-3">Filters</h5>' +
		'<div class="row">' +
		'<div class="col-md-3 mb-3">' +
		'<label class="form-label">From Date</label>' +
		'<input type="date" id="filter-from-date" class="form-control">' +
		'</div>' +
		'<div class="col-md-3 mb-3">' +
		'<label class="form-label">To Date</label>' +
		'<input type="date" id="filter-to-date" class="form-control">' +
		'</div>' +
		'<div class="col-md-3 mb-3">' +
		'<label class="form-label">Purpose</label>' +
		'<select id="filter-purpose" class="form-control">' +
		'<option value="">All</option>' +
		'<option value="Purchase" selected>Purchase</option>' +
		'<option value="Material Transfer">Material Transfer</option>' +
		'<option value="Material Issue">Material Issue</option>' +
		'<option value="Manufacture">Manufacture</option>' +
		'<option value="Customer Provided">Customer Provided</option>' +
		'</select>' +
		'</div>' +
		'<div class="col-md-3 mb-3">' +
		'<label class="form-label">Material Request</label>' +
		'<input type="text" id="filter-material-request" class="form-control" placeholder="Search Material Request...">' +
		'</div>' +
		'</div>' +
		'<div class="row">' +
		'<div class="col-md-4 mb-3">' +
		'<div id="project-filter"></div>' +
		'</div> ' +
		'<div class="col-md-8 mb-3">' +
		'<label class="form-label">&nbsp;</label>' +
		'<div style="padding-top: 8px;">' +
		'<button id="btn-fetch-data" class="btn btn-primary mr-2">' +
		'<i class="fa fa-search"></i> Fetch Report' +
		'</button>' +
		'<button id="btn-clear-filters" class="btn btn-secondary">' +
		'<i class="fa fa-times"></i> Clear Filters' +
		'</button>' +
		'</div>' +
		'</div>' +
		'</div>' +
		'</div>' +
		'</div>' +
		'<!-- Status Legend -->' +
		'<div class="card mb-4">' +
		'<div class="card-body">' +
		'<h5 class="card-title mb-3">Status</h5>' +
		'<div class="row">' +
		'<div class="col-md-2 mb-2">' +
		'<span class="status-badge status-draft">Draft</span>' +
		'</div>' +
		'<div class="col-md-2 mb-2">' +
		'<span class="status-badge status-pending">Pending</span>' +
		'</div>' +
		'<div class="col-md-2 mb-2">' +
		'<span class="status-badge status-approved">Approved</span>' +
		'</div>' +
		'<div class="col-md-2 mb-2">' +
		'<span class="status-badge status-cancelled">Cancelled</span>' +
		'</div>' +
		'<div class="col-md-2 mb-2">' +
		'<span class="status-badge status-quotation">Quotation</span>' +
		'</div>' +
		'<div class="col-md-2 mb-2">' +
		'<span class="status-badge status-awarded">Awarded</span>' +
		'</div>' +
		'</div>' +
		'</div>' +
		'</div>' +
		'<!-- Loading Indicator -->' +
		'<div id="loading" class="text-center py-5" style="display: none;">' +
		'<div class="loading-spinner"></div>' +
		'<p class="mt-3 text-muted">Loading data...</p>' +
		'</div>' +

		'<!-- Report Data Container -->' +
		'<div id="report-data"></div>' +
		'</div>'
	);

	// Initialize page
	po_details_report.init(page);
};

// Enhanced Report module matching image
var po_details_report = {
	page: null,
	reportData: [], // Store raw report data

	STATUS_COLORS: {
		'Draft': 'status-draft',
		'Pending': 'status-pending',
		'Pending Approval': 'status-pending',
		'Approved': 'status-approved',
		'Cancelled': 'status-cancelled',
		'Submitted': 'status-submitted',
		'Received': 'status-received',
		'Completed': 'status-completed',
		'Paid': 'status-paid',
		'Initiated': 'status-pending',
		'Open': 'status-pending',
		'Closed': 'status-completed',
		'To Receive': 'status-pending',
		'To Bill': 'status-pending',
		'To Receive and Bill': 'status-pending',
		'Unpaid': 'status-pending',
		'Partially Paid': 'status-pending',
		'Return': 'status-cancelled',
		'Requested': 'status-pending',
		'Payment Ordered': 'status-approved',
		'Partially Ordered': 'status-pending',
		'Partially Received': 'status-pending',
		'Delivered': 'status-approved',
		'Partially Delivered': 'status-pending',
		'Stopped': 'status-cancelled',
		'Rejected': 'status-cancelled',
		'Transfer': 'status-approved',
		'Issue': 'status-cancelled',
		'Manufacture': 'status-pending',
		'Quotation': 'status-quotation',
		'Ordered': 'status-ordered',
		'Awarded': 'status-awarded',
		'Evaluated': 'status-awarded',
		'Expired': 'status-cancelled',
		'Under Review': 'status-pending'
	},

	WORKFLOW_BORDERS: {
		'Draft': 'border-draft',
		'Pending': 'border-pending',
		'Pending Approval': 'border-pending',
		'Approved': 'border-approved',
		'Cancelled': 'border-cancelled',
		'Received': 'border-received',
		'Open': 'border-pending',
		'Closed': 'border-approved',
		'Quotation': 'border-pending',
		'Awarded': 'border-approved'
	},

	init: function (page) {
		this.page = page;
		this.setup_events();
		this.setup_project_link();
		this.set_default_dates();

		// Check for route param (Material Request ID)
		const route = frappe.get_route();
		if (route.length > 1 && route[0] === 'po-details-report') {
			const mrId = route[1];
			$('#filter-material-request').val(mrId);
			// Also clear date filters if coming from specific MR to show all history
			// or keep default dates? User asked for default current month. 
			// But if viewing specific MR, we usually want to see everything for it.
			// Let's keep date filters for now but maybe we should clear them if an MR is passed?
			// For now, adhering to user request of default dates being current month.
		} else if (frappe.route_options) {
			if (frappe.route_options.project && this.project_control) {
				this.project_control.set_value(frappe.route_options.project);
			}
			// Clear route options so they don't persist on refresh if not desired, 
			// though usually frappe handles this.
			frappe.route_options = null;
		}

		this.fetch_report_data();
	},

	setup_events: function () {
		const self = this;

		$('#btn-fetch-data').on('click', function () {
			self.fetch_report_data();
		});

		$('#btn-refresh').on('click', function () {
			self.fetch_report_data();
		});

		$('#btn-clear-filters').on('click', function () {
			self.clear_filters();
		});

		// Add keyup support for real-time search
		$('#filter-material-request').on('keyup', function (e) {
			self.apply_mr_search();
		});
	},

	setup_project_link: function () {
		this.project_control = frappe.ui.form.make_control({
			parent: $('#project-filter'),
			df: {
				fieldtype: 'Link',
				label: 'Project',
				fieldname: 'project',
				options: 'Project',
				placeholder: 'Select Project'
			},
			render_input: true
		});
	},

	set_default_dates: function () {
		const today = frappe.datetime.get_today();

		// Default to current month first and last date
		const from_date = frappe.datetime.month_start();
		const to_date = frappe.datetime.month_end();

		$('#filter-from-date').val(from_date);
		$('#filter-to-date').val(to_date);
	},

	clear_filters: function () {
		$('#filter-material-request').val('');
		$('#filter-purpose').val('Purchase');
		if (this.project_control) {
			this.project_control.set_value('');
		}
		this.set_default_dates();
		this.apply_mr_search();
	},

	get_filters: function () {
		return {
			project: this.project_control ? (this.project_control.get_value() || null) : null,
			from_date: $('#filter-from-date').val() || null,
			to_date: $('#filter-to-date').val() || null,
			material_request_purpose: $('#filter-purpose').val() || 'Purchase'
		};
	},

	fetch_report_data: function () {
		const self = this;
		const filters = this.get_filters();

		$('#loading').show();
		$('#report-data').html('');

		frappe.call({
			method: 'frappe.desk.query_report.run',
			args: {
				report_name: 'Purchase Orde Details',
				filters: filters,
				ignore_prepared_report: 1
			},
			callback: function (r) {
				$('#loading').hide();

				if (r.message) {
					self.reportData = r.message.result || [];
					const processedData = self.process_data(self.reportData);
					self.render_report_data(processedData);
					self.apply_mr_search(); // Re-apply search if text exists
				} else {
					$('#report-data').html('<div class="alert alert-warning">No data found</div>');
				}
			},
			error: function (err) {
				$('#loading').hide();
				$('#report-data').html('<div class="alert alert-danger">Error loading report data</div>');
				console.error(err);
			}
		});
	},

	process_data: function (rows) {
		const groupedData = {};

		if (!rows || rows.length === 0) {
			return [];
		}

		// First, group by material request (rows with indent=0)
		rows.forEach(row => {
			if (row.indent === 0) {
				// This is a Material Request parent row
				groupedData[row.material_request] = {
					materialRequest: row.material_request,
					mrStatus: row.mr_status,
					mrWorkflowState: row.mr_workflow_state,
					documents: {
						materialRequest: row.material_request,
						mrStatus: row.mr_status,

						// RFQ, BT, SQ documents
						requestForQuotation: null,
						rfqStatus: null,
						rfqWorkflowState: null,
						bidTabulation: null,
						btStatus: null,
						btWorkflowState: null,
						supplierQuotation: null,
						sqStatus: null,
						sqWorkflowState: null,

						// Purchase documents
						purchaseOrder: null,
						poStatus: null,
						poWorkflowState: null,
						poApprovalDate: row.po_approval_date,
						poTransactionDate: row.po_transaction_date,

						purchaseReceipt: null,
						prStatus: null,
						prWorkflowState: null,

						purchaseInvoice: null,
						piStatus: null,
						piWorkflowState: null,

						paymentRequest: null,
						payreqStatus: null,
						payreqWorkflowState: null,

						paymentEntry: null,
						peStatus: null,
						peWorkflowState: null
					},
					rfqs: [],
					purchaseOrders: [],
					items: []
				};
			}
		});

		// Now, process child rows (indent > 0)
		rows.forEach(row => {
			const mr = groupedData[row.material_request];
			if (!mr) return;

			if (row.indent === 1 && row.document_type === "Request for Quotation") {
				// This is a Request for Quotation row
				const rfqObj = {
					requestForQuotation: row.request_for_quotation,
					rfqStatus: row.rfq_status,
					rfqWorkflowState: row.rfq_workflow_state,
					bidTabulation: row.bid_tabulation,
					btStatus: row.bt_status,
					btWorkflowState: row.bt_workflow_state,
					supplierQuotation: row.supplier_quotation,
					sqStatus: row.sq_status,
					sqWorkflowState: row.sq_workflow_state
				};

				// Add to MR's RFQs list
				mr.rfqs.push(rfqObj);

				// Update MR's document references with the first RFQ found
				if (!mr.documents.requestForQuotation) {
					mr.documents.requestForQuotation = row.request_for_quotation;
					mr.documents.rfqStatus = row.rfq_status;
					mr.documents.rfqWorkflowState = row.rfq_workflow_state;
					mr.documents.bidTabulation = row.bid_tabulation;
					mr.documents.btStatus = row.bt_status;
					mr.documents.btWorkflowState = row.bt_workflow_state;
					mr.documents.supplierQuotation = row.supplier_quotation;
					mr.documents.sqStatus = row.sq_status;
					mr.documents.sqWorkflowState = row.sq_workflow_state;
				}
			} else if (row.indent === 1 && row.document_type === "Purchase Order") {
				// This is a Purchase Order row
				const poObj = {
					purchaseOrder: row.purchase_order,
					poStatus: row.po_status,
					poWorkflowState: row.po_workflow_state,
					poApprovalDate: row.po_approval_date,
					poTransactionDate: row.po_transaction_date,
					requestForQuotation: row.request_for_quotation,
					rfqStatus: row.rfq_status,
					rfqWorkflowState: row.rfq_workflow_state,
					bidTabulation: row.bid_tabulation,
					btStatus: row.bt_status,
					btWorkflowState: row.bt_workflow_state,
					supplierQuotation: row.supplier_quotation,
					sqStatus: row.sq_status,
					sqWorkflowState: row.sq_workflow_state,
					purchaseReceipt: row.purchase_receipt,
					prStatus: row.pr_status,
					prWorkflowState: row.pr_workflow_state,
					purchaseInvoice: row.purchase_invoice,
					piStatus: row.pi_status,
					piWorkflowState: row.pi_workflow_state,
					paymentRequest: row.payment_request,
					payreqStatus: row.payreq_status,
					payreqWorkflowState: row.payreq_workflow_state,
					paymentEntry: row.payment_entry,
					peStatus: row.pe_status,
					peWorkflowState: row.pe_workflow_state,
					items: []
				};

				// Add to MR's purchase orders list
				mr.purchaseOrders.push(poObj);

				// Update MR's document references with the first PO found
				if (!mr.documents.purchaseOrder) {
					mr.documents.purchaseOrder = row.purchase_order;
					mr.documents.poStatus = row.po_status;
					mr.documents.poWorkflowState = row.po_workflow_state;
					mr.documents.purchaseReceipt = row.purchase_receipt;
					mr.documents.prStatus = row.pr_status;
					mr.documents.prWorkflowState = row.pr_workflow_state;
					mr.documents.purchaseInvoice = row.purchase_invoice;
					mr.documents.piStatus = row.pi_status;
					mr.documents.piWorkflowState = row.pi_workflow_state;
					mr.documents.paymentRequest = row.payment_request;
					mr.documents.payreqStatus = row.payreq_status;
					mr.documents.payreqWorkflowState = row.payreq_workflow_state;
					mr.documents.paymentEntry = row.payment_entry;
					mr.documents.peStatus = row.pe_status;
					mr.documents.peWorkflowState = row.pe_workflow_state;
				}
			} else if (row.indent === 2 && row.document_type === "Purchase Order Item") {
				// This is a Purchase Order Item row
				// Find the last PO in the MR to add this item to
				if (mr.purchaseOrders.length > 0) {
					const lastPO = mr.purchaseOrders[mr.purchaseOrders.length - 1];
					lastPO.items.push({
						itemCode: row.item_code,
						itemName: row.item_name,
						itemGroup: row.item_group,
						qty: row.qty,
						project: row.project,
						scheduleDate: row.schedule_date
					});

					// Also add to MR's combined items list
					mr.items.push({
						itemCode: row.item_code,
						itemName: row.item_name,
						itemGroup: row.item_group,
						qty: row.qty,
						project: row.project,
						scheduleDate: row.schedule_date
					});
				}
			}
		});

		return Object.values(groupedData);
	},

	render_report_data: function (data) {
		let html = '';

		if (data.length === 0) {
			html = '<div class="alert alert-info">No data found for the selected filters.</div>';
		} else {
			data.forEach((mr, index) => {
				// Determine workflow border class
				const workflowClass = this.WORKFLOW_BORDERS[mr.mrWorkflowState] || 'border-pending';

				// Create Material Request Card
				html += '<div class="mr-card ' + workflowClass + '">';

				// Header
				html += '<div class="d-flex justify-content-between align-items-center mb-2">';
				html += '<div class="mr-id" style="margin-bottom:0;">' +
					'<a href="/app/material-request/' + mr.materialRequest + '" style="color: inherit; text-decoration: none;">' +
					mr.materialRequest + '</a>' +
					'</div>';

				// Workflow & Status Badges
				html += '<div class="mr-workflow-status" style="margin-top:0;">';
				html += '<div class="status-section text-right mr-3">';
				html += '<div class="status-label">MR Workflow</div>';
				html += '<div class="status-value">' + this.create_status_badge(mr.mrWorkflowState) + '</div>';
				html += '</div>';
				html += '<div class="status-section text-right">';
				html += '<div class="status-label">MR Status</div>';
				html += '<div class="status-value">' + this.create_status_badge(mr.mrStatus) + '</div>';
				html += '</div>';
				html += '</div>';
				html += '</div>';

				// DOCUMENT FLOW section
				html += '<h6 style="margin-bottom: 20px; font-weight:600; color:#6c757d; font-size: 14px;">DOCUMENT FLOW</h6>';
				html += '<div class="doc-flow-track">';

				// Step 1: Material Request
				html += this.create_document_flow_step(1, 'Material Request', mr.materialRequest, mr.mrStatus, '#9b59b6', 'Material Request', mr.mrWorkflowState);

				// Arrow
				html += '<div class="flow-arrow">→</div>';

				// Step 2: Request for Quotation
				html += this.create_document_flow_step(2, 'Request for Quotation', mr.documents.requestForQuotation, mr.documents.rfqStatus, '#3498db', 'Request for Quotation', mr.documents.rfqWorkflowState);

				// Arrow
				html += '<div class="flow-arrow">→</div>';

				// Step 3: Bid Tabulation / Supplier Quotation
				// Show whichever is available
				const bidDoc = mr.documents.bidTabulation || mr.documents.supplierQuotation;
				const bidStatus = mr.documents.btStatus || mr.documents.sqStatus;
				const bidWorkflow = mr.documents.bidTabulation ? mr.documents.btWorkflowState : mr.documents.sqWorkflowState;
				const bidTitle = mr.documents.bidTabulation ? 'Bid Tabulation' : 'Supplier Quotation';
				html += this.create_document_flow_step(3, bidTitle, bidDoc, bidStatus, '#16a085', bidTitle, bidWorkflow);

				// Arrow
				html += '<div class="flow-arrow">→</div>';

				// Step 4: Purchase Order
				html += this.create_document_flow_step(4, 'Purchase Order', mr.documents.purchaseOrder, mr.documents.poStatus, '#e67e22', 'Purchase Order', mr.documents.poWorkflowState);

				// Arrow
				html += '<div class="flow-arrow">→</div>';

				// Step 5: Purchase Receipt
				html += this.create_document_flow_step(5, 'Purchase Receipt', mr.documents.purchaseReceipt, mr.documents.prStatus, '#8e44ad', 'Purchase Receipt', mr.documents.prWorkflowState);

				// Arrow
				html += '<div class="flow-arrow">→</div>';

				// Step 6: Purchase Invoice
				html += this.create_document_flow_step(6, 'Purchase Invoice', mr.documents.purchaseInvoice, mr.documents.piStatus, '#f39c12', 'Purchase Invoice', mr.documents.piWorkflowState);

				// Arrow
				html += '<div class="flow-arrow">→</div>';

				// Step 7: Payment Request
				html += this.create_document_flow_step(7, 'Payment Request', mr.documents.paymentRequest, mr.documents.payreqStatus, '#e74c3c', 'Payment Request', mr.documents.payreqWorkflowState);

				// Arrow
				html += '<div class="flow-arrow">→</div>';

				// Step 8: Payment Entry
				html += this.create_document_flow_step(8, 'Payment Entry', mr.documents.paymentEntry, mr.documents.peStatus, '#27ae60', 'Payment Entry', mr.documents.peWorkflowState);

				html += '</div>'; // End doc-flow-track

				// Show RFQs if any
				if (mr.rfqs.length > 0) {
					html += '<div style="margin-top: 20px;">';
					html += '<h6 style="font-weight:600; color:#6c757d; font-size: 14px;">REQUEST FOR QUOTATIONS</h6>';

					mr.rfqs.forEach((rfq, rfqIndex) => {
						html += '<div class="child-row">';
						html += '<div class="d-flex justify-content-between align-items-center mb-1">';
						html += '<div class="child-doc">';
						html += '<a href="/app/request-for-quotation/' + rfq.requestForQuotation + '" class="font-weight-bold" style="color: #2c3e50;">' +
							rfq.requestForQuotation + '</a>';
						html += ' <span class="text-muted">' + this.create_status_badge(rfq.rfqStatus) + '</span>';
						html += '</div>';

						// Show Bid Tabulation if exists
						if (rfq.bidTabulation) {
							html += '<div class="child-doc">';
							html += 'Bid Tab: <a href="/app/bid-tabulation-discussion/' + rfq.bidTabulation + '" style="color: #16a085;">' +
								rfq.bidTabulation + '</a>';
							html += ' <span class="text-muted">' + this.create_status_badge(rfq.btStatus) + '</span>';
							html += '</div>';
						} else if (rfq.supplierQuotation) {
							html += '<div class="child-doc">';
							html += 'Supplier Quote: <a href="/app/supplier-quotation/' + rfq.supplierQuotation + '" style="color: #16a085;">' +
								rfq.supplierQuotation + '</a>';
							html += ' <span class="text-muted">' + this.create_status_badge(rfq.sqStatus) + '</span>';
							html += '</div>';
						}
						html += '</div>';
						html += '</div>';
					});
					html += '</div>';
				}

				// Purchase Order Items (Collapsible)
				if (mr.items.length > 0) {
					html += this.create_purchase_order_items(index, mr.items);
				}

				// Show all Purchase Orders for this MR
				if (mr.purchaseOrders.length > 0) {
					html += '<div style="margin-top: 20px; border-top: 1px dashed #dee2e6; padding-top: 15px;">';
					html += '<h6 style="font-weight:600; color:#6c757d; font-size: 14px;">PURCHASE ORDERS</h6>';

					mr.purchaseOrders.forEach((po, poIndex) => {
						html += '<div class="card mb-2" style="border-left: 4px solid #3498db;">';
						html += '<div class="card-body p-3">';
						html += '<div class="d-flex justify-content-between align-items-center">';
						html += '<div>';
						html += '<a href="/app/purchase-order/' + po.purchaseOrder + '" class="font-weight-bold" style="color: #2c3e50; text-decoration: none;">' + po.purchaseOrder + '</a>';
						html += '<div class="text-muted small mt-1">';
						html += 'Status: ' + this.create_status_badge(po.poStatus) + ' | ';
						html += 'Workflow: ' + (po.poWorkflowState || '-') + ' | ';
						html += 'Approval: ' + (po.poApprovalDate || '-') + ' | ';
						html += 'Items: ' + po.items.length;
						html += '</div>';
						html += '</div>';
						html += '<div>';
						if (po.purchaseReceipt) {
							html += '<div class="text-success small"><i class="fa fa-check-circle"></i> Receipt: ' + po.purchaseReceipt + '</div>';
						}
						if (po.purchaseInvoice) {
							html += '<div class="text-info small"><i class="fa fa-file-invoice"></i> Invoice: ' + po.purchaseInvoice + '</div>';
						}
						html += '</div>';
						html += '</div>';
						html += '</div>';
						html += '</div>';
					});
					html += '</div>';
				}

				html += '</div>'; // End mr-card
			});
		}

		$('#report-data').html(html);
	},

	create_document_flow_step: function (stepNumber, title, docValue, status, color, docType, workflowState) {
		let html = '<div class="doc-flow-step">';
		html += '<div class="step-title" style="text-align:center; font-size:12px; margin-bottom:5px;">' + title + '</div>';

		if (!docValue || docValue === 'None' || docValue === 'NULL' || docValue === '-') {
			html += '<div class="doc-box p-3 text-center" style="border: 1px dashed #dee2e6; border-radius: 8px; background: #f8f9fa;">';
			html += '<div style="color: #dee2e6; font-size: 20px; margin-bottom: 5px;">📄</div>';
			html += '<div class="empty-doc">-</div>';
			html += '</div>';
		} else {
			// Clean the status (remove HTML formatting from report)
			const cleanStatus = String(status || '').replace(/<[^>]*>/g, '').replace(/●\s*/g, '').trim();

			// Handle multiple docs (comma separated)
			const docs = docValue.split(', ');
			const mainDoc = docs[0].trim();
			const count = docs.length;

			html += '<div class="doc-box p-3 text-center" style="border: 1px solid ' + color + '; border-radius: 8px; background: white;" ' +
				'onclick="po_details_report.open_document(\'' + mainDoc + '\', \'' + (docType || title) + '\')">';

			html += '<div style="color: ' + color + '; font-size: 20px; margin-bottom: 5px;">📄</div>';

			html += '<div style="font-weight: bold; font-size: 13px; margin-bottom: 5px; word-break: break-all;">' +
				mainDoc +
				(count > 1 ? ' <span class="count-badge">+' + (count - 1) + '</span>' : '') +
				'</div>';

			if (cleanStatus) {
				html += '<div style="margin-bottom: 5px;">' + this.create_status_badge(cleanStatus) + '</div>';
			}

			html += '<div style="font-size: 11px; color: #3498db; cursor: pointer;">';
			html += '<i class="fa fa-external-link"></i> Click to open';
			html += '</div>';

			if (workflowState && workflowState !== 'None' && workflowState !== 'NULL') {
				const cleanWorkflow = String(workflowState || '').replace(/<[^>]*>/g, '').trim();
				const cleanWorkflowShort = cleanWorkflow.split(',')[0].trim();
				html += '<div class="mt-1" style="font-size: 11px;">Workflow: ' + this.create_status_badge(cleanWorkflowShort) + '</div>';
			}

			html += '</div>';
		}

		html += '</div>';
		return html;
	},

	create_purchase_order_items: function (index, items) {
		if (!items || items.length === 0) return '';

		let html = '<div style="margin-top: 15px; border-top: 1px dashed #dee2e6; padding-top: 15px;">';
		html += '<div class="items-toggle" onclick="po_details_report.toggleItems(' + index + ')" style="font-size: 13px;">';
		html += '<span id="toggle-icon-' + index + '" style="margin-right: 5px;">▶</span>';
		html += '<span><strong>Purchase Order Items</strong> (' + items.length + ' items)</span>';
		html += '</div>';

		html += '<div class="items-container" id="items-container-' + index + '">';
		html += '<div class="table-responsive" style="margin-top: 10px;">';
		html += '<table class="table table-bordered table-sm" style="font-size: 12px;">';
		html += '<thead class="thead-light"><tr>';
		html += '<th>Item Code</th><th>Item Name</th><th>Item Group</th><th>Quantity</th><th>Project</th><th>Schedule Date</th>';
		html += '</tr></thead><tbody>';

		items.forEach((item, idx) => {
			html += '<tr>';
			html += '<td>' + (item.itemCode || '-') + '</td>';
			html += '<td>' + (item.itemName || '-') + '</td>';
			html += '<td>' + (item.itemGroup || '-') + '</td>';
			html += '<td>' + (item.qty || '-') + '</td>';
			html += '<td>' + (item.project || '-') + '</td>';
			html += '<td>' + (item.scheduleDate || '-') + '</td>';
			html += '</tr>';
		});

		html += '</tbody></table>';
		html += '</div></div></div>';

		return html;
	},

	create_status_badge: function (status) {
		if (!status) return '-';

		// Extract the first status if there are multiple
		const firstStatus = status.split(',')[0].trim();
		const statusClass = this.STATUS_COLORS[firstStatus] || 'status-pending';

		return '<span class="status-badge ' + statusClass + '">' +
			'<span style="margin-right:4px;">●</span>' + firstStatus +
			'</span>';
	},

	toggleItems: function (index) {
		const container = $('#items-container-' + index);
		const icon = $('#toggle-icon-' + index);

		if (container.hasClass('expanded')) {
			container.removeClass('expanded');
			icon.text('▶');
		} else {
			container.addClass('expanded');
			icon.text('▼');
		}
	},

	apply_mr_search: function () {
		const txt = $('#filter-material-request').val().toLowerCase();
		if (!txt) {
			$('.mr-card').show();
			return;
		}
		$('.mr-card').each(function () {
			const mrId = $(this).find('.mr-id a').text().toLowerCase();
			$(this).toggle(mrId.includes(txt));
		});
	},

	open_document: function (docId, docType) {
		if (docId && docId !== '-' && docId !== 'None' && docId !== 'NULL') {
			// Map document types to Frappe doctypes
			const doctypeMap = {
				'Material Request': 'Material Request',
				'Request for Quotation': 'Request for Quotation',
				'Bid Tabulation': 'Bid Tabulation Discussion',
				'Supplier Quotation': 'Supplier Quotation',
				'Purchase Order': 'Purchase Order',
				'Purchase Receipt': 'Purchase Receipt',
				'Purchase Invoice': 'Purchase Invoice',
				'Payment Request': 'Payment Request',
				'Payment Entry': 'Payment Entry'
			};

			const doctype = doctypeMap[docType] || docType;
			frappe.set_route('Form', doctype, docId);
		}
	}
};