# Copyright (c) 2026, Jaisurya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.dashboard import cache_source


@frappe.whitelist()
@cache_source
def get(
	chart_name=None,
	chart=None,
	no_cache=None,
	filters=None,
	from_date=None,
	to_date=None,
	timespan=None,
	time_interval=None,
	heatmap_year=None,
):
	if filters and isinstance(filters, str):
		filters = frappe.parse_json(filters)

	from cust_chicory_erp.analysis.process_dashboard_widgets import get_low_stock_bar_rows

	rows = get_low_stock_bar_rows()
	if not rows:
		return {
			"labels": [_("No tracked items")],
			"datasets": [{"name": _("On Hand"), "values": [1]}],
		}

	labels = [row["label"] for row in rows]
	values = [row["stock_qty"] for row in rows]

	return {
		"labels": labels,
		"datasets": [{"name": _("On Hand"), "values": values}],
	}