# Copyright (c) 2026, Jaisurya and contributors

import frappe
from frappe.desk.doctype.dashboard_chart.dashboard_chart import has_permission as frappe_has_permission


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if doc.chart_type == "Custom" and doc.source and str(doc.source).startswith("Chicory"):
		roles = frappe.get_roles(user)
		if "System Manager" in roles:
			return True
		if doc.roles:
			allowed = {d.role for d in doc.roles}
			if set(roles) & allowed:
				return True
		# Chicory custom charts are summary widgets — any desk user with Item access
		if frappe.has_permission("Item", "read", user=user):
			return True
		return False
	return frappe_has_permission(doc, ptype, user)