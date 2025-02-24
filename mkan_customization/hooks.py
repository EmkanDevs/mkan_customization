app_name = "mkan_customization"
app_title = "Mkan Customization"
app_publisher = "Finbyz"
app_description = "Mkan"
app_email = "info@finbyz.tech"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "mkan_customization",
# 		"logo": "/assets/mkan_customization/logo.png",
# 		"title": "Mkan Customization",
# 		"route": "/mkan_customization",
# 		"has_permission": "mkan_customization.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/mkan_customization/css/mkan_customization.css"
# app_include_js = "/assets/mkan_customization/js/mkan_customization.js"

# include js, css files in header of web template
# web_include_css = "/assets/mkan_customization/css/mkan_customization.css"
# web_include_js = "/assets/mkan_customization/js/mkan_customization.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "mkan_customization/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
            "Request for Quotation":"public/js/request_for_quotation.js",
            "Purchase Order":"public/js/purchase_order.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "mkan_customization/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "mkan_customization.utils.jinja_methods",
# 	"filters": "mkan_customization.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "mkan_customization.install.before_install"
# after_install = "mkan_customization.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "mkan_customization.uninstall.before_uninstall"
# after_uninstall = "mkan_customization.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "mkan_customization.utils.before_app_install"
# after_app_install = "mkan_customization.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "mkan_customization.utils.before_app_uninstall"
# after_app_uninstall = "mkan_customization.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mkan_customization.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Purchase Order":{
        "validate":"mkan_customization.mkan_customization.doc_events.purchase_order.after_insert"
    },
    "Material Request":{
        "validate":"mkan_customization.mkan_customization.doc_events.material_request.validate"
    },

}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"all": [
		"mkan_customization.mkan_customization.doctype.lodge_available_rooms.lodge_available_rooms.update_room_capacities"
	],
}

# Testing
# -------

# before_tests = "mkan_customization.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"erpnext.stock.doctype.material_request.material_request.make_request_for_quotation": "mkan_customization.mkan_customization.override.material_request.make_request_for_quotation",
    "erpnext.buying.doctype.request_for_quotation.request_for_quotation.make_supplier_quotation_from_rfq":"mkan_customization.mkan_customization.override.request_for_quotation.make_supplier_quotation_from_rfq",
    "frappe.desk.form.assign_to.add":"mkan_customization.mkan_customization.override.assign_to.add"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mkan_customization.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["mkan_customization.utils.before_request"]
# after_request = ["mkan_customization.utils.after_request"]

# Job Events
# ----------
# before_job = ["mkan_customization.utils.before_job"]
# after_job = ["mkan_customization.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"mkan_customization.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    {
        "dt": "Custom Field",
        "filters": {"module": ["in", ["Mkan Customization"]]},
    },
    {
        "dt": "Property Setter",
        "filters": {"module": ["in", ["Mkan Customization"]]},
    }
]

