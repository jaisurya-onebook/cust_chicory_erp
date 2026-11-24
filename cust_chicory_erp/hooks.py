app_name = "cust_chicory_erp"
app_title = "Chicory ERP"
app_publisher = "Jaisurya"
app_description = "Chicory Powder Manufacturing ERP"
app_email = "admin@chicory.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext", "india_compliance"]

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "cust_chicory_erp",
		"logo": "/assets/cust_chicory_erp/images/chicory-logo.svg",
		"title": "Chicory ERP",
		"route": "/desk/chicory-food-manufacturing",
		"sequence_id": 3,
	}
]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `cust_chicory_erp/dock/cust_chicory_erp/cust_chicory_erp.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/cust_chicory_erp/css/cust_chicory_erp.css"
# app_include_js = "/assets/cust_chicory_erp/js/cust_chicory_erp.js"

# include js, css files in header of web template
# web_include_css = "/assets/cust_chicory_erp/css/cust_chicory_erp.css"
# web_include_js = "/assets/cust_chicory_erp/js/cust_chicory_erp.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "cust_chicory_erp/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Purchase Receipt": "public/js/purchase_receipt.js",
	"Job Card": "public/js/job_card.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "cust_chicory_erp/public/icons.svg"

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

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "cust_chicory_erp.utils.jinja_methods",
# 	"filters": "cust_chicory_erp.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "cust_chicory_erp.install.before_install"
after_install = "cust_chicory_erp.setup.custom_fields.setup_custom_fields"
after_migrate = "cust_chicory_erp.setup.custom_fields.setup_custom_fields"

# Uninstallation
# ------------

# before_uninstall = "cust_chicory_erp.uninstall.before_uninstall"
# after_uninstall = "cust_chicory_erp.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "cust_chicory_erp.utils.before_app_install"
# after_app_install = "cust_chicory_erp.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "cust_chicory_erp.utils.before_app_uninstall"
# after_app_uninstall = "cust_chicory_erp.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "cust_chicory_erp.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "cust_chicory_erp.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "cust_chicory_erp.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["cust_chicory_erp.search.awesomebar_results"]

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

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Purchase Receipt": {
		"validate": "cust_chicory_erp.controllers.weighbridge.calculate_weighbridge_weights",
	},
	"Job Card": {
		"validate": "cust_chicory_erp.controllers.job_card.calculate_job_card_loss",
	},
	"Stock Entry": {
		"validate": "cust_chicory_erp.controllers.quality_gate.validate_batch_quality",
	},
	"Delivery Note": {
		"validate": "cust_chicory_erp.controllers.quality_gate.validate_batch_quality",
	},
	"Landed Cost Voucher": {
		"validate": "cust_chicory_erp.controllers.landed_cost.validate_duplicate_freight",
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"cust_chicory_erp.tasks.all"
# 	],
# 	"daily": [
# 		"cust_chicory_erp.tasks.daily"
# 	],
# 	"hourly": [
# 		"cust_chicory_erp.tasks.hourly"
# 	],
# 	"weekly": [
# 		"cust_chicory_erp.tasks.weekly"
# 	],
# 	"monthly": [
# 		"cust_chicory_erp.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "cust_chicory_erp.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "cust_chicory_erp.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "cust_chicory_erp.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "cust_chicory_erp.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["cust_chicory_erp.utils.before_request"]
# after_request = ["cust_chicory_erp.utils.after_request"]

# Job Events
# ----------
# before_job = ["cust_chicory_erp.utils.before_job"]
# after_job = ["cust_chicory_erp.utils.after_job"]

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
# 	"cust_chicory_erp.auth.validate"
# ]

# on_social_login = "cust_chicory_erp.auth.on_social_login"

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

