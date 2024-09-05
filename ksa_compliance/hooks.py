app_name = "ksa_compliance"
app_title = "KSA Compliance"
app_publisher = "LavaLoon"
app_description = "KSA Compliance app for E-invoice"
app_email = "info@lavaloon.com"
app_license = "Copyright (c) 2023 LavaLoon"
# required_apps = []

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ksa_compliance/css/ksa_compliance.css"
# app_include_js = "/assets/ksa_compliance/js/ksa_compliance.js"

# include js, css files in header of web template
# web_include_css = "/assets/ksa_compliance/css/ksa_compliance.css"
# web_include_js = "/assets/ksa_compliance/js/ksa_compliance.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ksa_compliance/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

doctype_js = {"Customer": "public/js/customer.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ksa_compliance/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# "Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
    "methods": "ksa_compliance.jinja.get_zatca_phase_1_qr_for_invoice",
}

# Installation
# ------------

# before_install = "ksa_compliance.install.before_install"
# after_install = "ksa_compliance.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ksa_compliance.uninstall.before_uninstall"
# after_uninstall = "ksa_compliance.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ksa_compliance.utils.before_app_install"
# after_app_install = "ksa_compliance.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ksa_compliance.utils.before_app_uninstall"
# after_app_uninstall = "ksa_compliance.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ksa_compliance.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# "Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# "Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# "ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# "*": {
# "on_update": "method",
# "on_cancel": "method",
# "on_trash": "method"
# }
# }

doc_events = {
    "Sales Invoice": {
        "on_submit": "ksa_compliance.standard_doctypes.sales_invoice.create_sales_invoice_additional_fields_doctype",
        "validate": "ksa_compliance.standard_doctypes.sales_invoice.validate_sales_invoice",
        "before_cancel": "ksa_compliance.standard_doctypes.sales_invoice.prevent_cancellation_of_sales_invoice"
    },
    "POS Invoice": {
        "on_submit": "ksa_compliance.standard_doctypes.sales_invoice.create_sales_invoice_additional_fields_doctype",
        "validate": "ksa_compliance.standard_doctypes.sales_invoice.validate_sales_invoice",
        "before_cancel": "ksa_compliance.standard_doctypes.sales_invoice.prevent_cancellation_of_sales_invoice",
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "hourly_long": [
        "ksa_compliance.background_jobs.sync_e_invoices"
    ]
}
# "all": [
# "ksa_compliance.tasks.all"
# ],
# "daily": [
# "ksa_compliance.tasks.daily"
# ],
# "hourly": [
# "ksa_compliance.tasks.hourly"
# ],
# "weekly": [
# "ksa_compliance.tasks.weekly"
# ],
# "monthly": [
# "ksa_compliance.tasks.monthly"
# ],
# }

# Testing
# -------

# before_tests = "ksa_compliance.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# "frappe.desk.doctype.event.event.get_events": "ksa_compliance.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# "Task": "ksa_compliance.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ksa_compliance.utils.before_request"]
# after_request = ["ksa_compliance.utils.after_request"]

# Job Events
# ----------
# before_job = ["ksa_compliance.utils.before_job"]
# after_job = ["ksa_compliance.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# {
# "doctype": "{doctype_1}",
# "filter_by": "{filter_by}",
# "redact_fields": ["{field_1}", "{field_2}"],
# "partial": 1,
# },
# {
# "doctype": "{doctype_2}",
# "filter_by": "{filter_by}",
# "partial": 1,
# },
# {
# "doctype": "{doctype_3}",
# "strict": False,
# },
# {
# "doctype": "{doctype_4}"
# }
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# "ksa_compliance.auth.validate"
# ]

# fixtures = [
# ]

# Auto generate type annotations for doctypes
# Reference: https://github.com/frappe/frappe/pull/21776
export_python_type_annotations = True
