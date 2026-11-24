# Copyright (c) 2026, Jaisurya and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime
from frappe.utils.dashboard import cache_source
from frappe.utils.dateutils import (
	get_dates_from_timegrain,
	get_from_date_from_timespan,
	get_period,
	get_period_beginning,
	get_period_ending,
)

VERDICT_STATUSES = ("Accepted", "Rejected")


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
	chart_doc = None
	if chart_name:
		chart_doc = frappe.get_doc("Dashboard Chart", chart_name)

	timespan = timespan or (chart_doc.timespan if chart_doc else None) or "Last Month"
	timegrain = time_interval or (chart_doc.time_interval if chart_doc else None) or "Daily"

	to_date = getdate(to_date) if to_date else getdate(now_datetime())
	if from_date:
		from_date = get_period_beginning(getdate(from_date), timegrain)
	else:
		from_date = get_period_beginning(
			get_from_date_from_timespan(to_date, timespan), timegrain
		)

	buckets = get_dates_from_timegrain(from_date, to_date, timegrain)
	if not buckets:
		return _empty_chart(timegrain)

	rows = frappe.db.sql(
		"""
		SELECT report_date, status, COUNT(*) AS cnt
		FROM `tabQuality Inspection`
		WHERE docstatus = 1
			AND status IN %(statuses)s
			AND report_date BETWEEN %(from_date)s AND %(to_date)s
		GROUP BY report_date, status
		""",
		{
			"statuses": VERDICT_STATUSES,
			"from_date": from_date,
			"to_date": to_date,
		},
		as_dict=True,
	)

	counts = {}
	for row in rows:
		bucket = get_period_ending(getdate(row.report_date), timegrain)
		key = (bucket, row.status)
		counts[key] = counts.get(key, 0) + row.cnt

	labels = [get_period(d, timegrain) for d in buckets]
	datasets = [
		{"name": _(status), "values": [counts.get((b, status), 0) for b in buckets]}
		for status in VERDICT_STATUSES
	]

	if not any(v for ds in datasets for v in ds["values"]):
		return _empty_chart(timegrain)

	return {"labels": labels, "datasets": datasets}


def _empty_chart(timegrain):
	return {
		"labels": [get_period(getdate(now_datetime()), timegrain)],
		"datasets": [{"name": _("Accepted"), "values": [0]}, {"name": _("Rejected"), "values": [0]}],
	}