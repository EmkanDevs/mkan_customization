(() => {
    "use strict";

    const BUTTON_LABEL = __("Download Excel");
    const BUTTON_CLASS = "custom-download-excel-btn";
    const REPORT_URL = "/api/method/mkan_customization.mkan_customization.api.export_query_report";
    const LIST_URL   = "/api/method/mkan_customization.mkan_customization.api.export_list_view";

    function post_download(url, params) {
        const payload = { form_params: JSON.stringify(params) };
        if (typeof open_url_post === "function") {
            open_url_post(url, payload);
        } else {
            const form = document.createElement("form");
            form.method = "POST";
            form.action = url;
            form.style.display = "none";
            const input = document.createElement("input");
            input.name = "form_params";
            input.value = payload.form_params;
            form.appendChild(input);
            if (frappe.csrf_token && frappe.csrf_token !== "None") {
                const csrf = document.createElement("input");
                csrf.name = "csrf_token";
                csrf.value = frappe.csrf_token;
                form.appendChild(csrf);
            }
            document.body.appendChild(form);
            form.submit();
            form.remove();
        }
    }

    // ------------------------- Query / Script Report -------------------------
    function download_report_excel(report) {
        report = report || frappe.query_report;
        if (!report || !report.report_name) {
            frappe.show_alert({ message: __("Could not detect the current report."), indicator: "red" });
            return;
        }

        let filters = {};
        try {
            if (typeof report.get_filter_values === "function") {
                filters = report.get_filter_values(true) || {};
            } else if (typeof report.get_values === "function") {
                filters = report.get_values() || {};
            }
        } catch (e) {
            return;
        }

        frappe.show_alert({ message: __("Preparing Excel..."), indicator: "green" });
        post_download(REPORT_URL, {
            report_name: report.report_name,
            filters: filters,
        });
    }

    function add_report_button(report) {
        report = report || frappe.query_report;
        if (!report?.page?.wrapper) return;
        if (report.page.wrapper.find("." + BUTTON_CLASS).length) return;
        const $btn = report.page.add_inner_button(BUTTON_LABEL, () => download_report_excel(report));
        if ($btn) $btn.addClass(BUTTON_CLASS);
    }

    function patch_query_report() {
        const QR = frappe.views?.QueryReport;
        if (!QR) return false;
        if (QR.prototype._custom_export_patched) return true;
        QR.prototype._custom_export_patched = true;

        ["refresh_report", "show"].forEach((fn) => {
            const original = QR.prototype[fn];
            if (!original) return;
            QR.prototype[fn] = async function (...args) {
                const result = await original.apply(this, args);
                add_report_button(this);
                return result;
            };
        });

        const original_render = QR.prototype.render;
        if (original_render) {
            QR.prototype.render = function (...args) {
                const result = original_render.apply(this, args);
                add_report_button(this);
                return result;
            };
        }
        return true;
    }

    // ------------------------------ Report View ------------------------------
    function download_report_view_excel(view) {
        if (!view?.doctype) {
            frappe.show_alert({ message: __("Could not detect the current view."), indicator: "red" });
            return;
        }

        // Report View columns keep their field info in `docfield`
        const columns = (view.columns || [])
            .map((c) => c.docfield || c.df)
            .filter((df) => df && df.fieldname && (!df.parent || df.parent === view.doctype))
            .map((df) => ({ fieldname: df.fieldname, label: df.label }));

        if (!columns.some((c) => c.fieldname === "name")) {
            columns.unshift({ fieldname: "name", label: __("ID") });
        }

        const filters = view.get_filters_for_args ? view.get_filters_for_args() : [];

        frappe.show_alert({ message: __("Preparing Excel..."), indicator: "green" });
        post_download(LIST_URL, {
            doctype: view.doctype,
            filters: filters,
            columns: columns,
            sort_by: view.sort_by,
            sort_order: view.sort_order,
        });
    }

    function add_report_view_button(view) {
        if (!view?.page?.wrapper) return;
        if (view.page.wrapper.find("." + BUTTON_CLASS).length) return;
        if (frappe.model.can_export && !frappe.model.can_export(view.doctype)) return;

        const $btn = view.page.add_inner_button(BUTTON_LABEL, () => download_report_view_excel(view));
        if ($btn) $btn.addClass(BUTTON_CLASS);
    }

    function try_add_report_view_button() {
        const v = window.cur_list;
        if (!v || !v.page || !v.page.wrapper) return;

        // remove any stale button, then add it only on Report View
        v.page.wrapper.find("." + BUTTON_CLASS).remove();
        if (v.doctype && v.view_name === "Report") {
            add_report_view_button(v);
        }
    }

    // ------------------------------- Bootstrap -------------------------------
    frappe.download_report_excel = download_report_excel;
    frappe.download_report_view_excel = download_report_view_excel;

    patch_query_report();

    $(document).on("page-change", () => {
        patch_query_report();
        setTimeout(try_add_report_view_button, 400);
        const route = frappe.get_route();
        if (frappe.query_report && route?.[0] === "query-report") {
            setTimeout(() => add_report_button(frappe.query_report), 100);
        }
    });

    if (frappe.router?.on) {
        frappe.router.on("change", () => setTimeout(try_add_report_view_button, 600));
    }
})();