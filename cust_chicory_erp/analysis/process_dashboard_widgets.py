import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt

MAX_WIDGET_ROWS = 5


def _get_stock_by_item(item_codes, warehouses=None):
	if not item_codes:
		return {}
	bin_dt = frappe.qb.DocType("Bin")
	query = (
		frappe.qb.from_(bin_dt)
		.select(bin_dt.item_code, Sum(bin_dt.actual_qty).as_("qty"))
		.where(bin_dt.item_code.isin(item_codes))
	)
	if warehouses:
		query = query.where(bin_dt.warehouse.isin(warehouses))
	rows = query.groupby(bin_dt.item_code).run(as_dict=True)
	return {row.item_code: flt(row.qty) for row in rows}


@frappe.whitelist()
def get_process_dashboard_widgets(dashboard_name: str = "Chicory Manufacturing"):
	return {
		"widgets": [
			{
				"title": _("Raw Chicory Roots Low Stock"),
				"categories": ["All", "Raw Material", "Semi-Finished", "Critical"],
				"active_category": "All",
				"category_method": "cust_chicory_erp.analysis.process_dashboard_widgets.get_raw_roots_by_category",
				"primary_action": {"label": _("Procure Roots"), "doctype": "Chicory Root Inward"},
				"footer_action": {
					"label": _("View All Raw Materials"),
					"route": ["List", "Item", {"item_group": "Chicory Raw Material"}],
				},
				"rows": get_raw_roots_by_category("All"),
			},
			{
				"title": _("Packaging Materials Low Stock"),
				"categories": ["All", "Pouches", "Bags & Boxes", "Critical"],
				"active_category": "All",
				"category_method": "cust_chicory_erp.analysis.process_dashboard_widgets.get_packaging_by_category",
				"primary_action": {"label": _("Create PO"), "doctype": "Purchase Order"},
				"footer_action": {
					"label": _("View All Packaging"),
					"route": ["List", "Item", {"item_group": "Chicory Packaging"}],
				},
				"rows": get_packaging_by_category("All"),
			},
			{
				"title": _("Finished Chicory Powder Low Stock"),
				"categories": ["All", "Retail Packs", "Bulk Powder", "Critical"],
				"active_category": "All",
				"category_method": "cust_chicory_erp.analysis.process_dashboard_widgets.get_powder_by_category",
				"primary_action": {"label": _("Start Work Order"), "doctype": "Work Order"},
				"footer_action": {
					"label": _("View Finished Goods"),
					"route": ["List", "Item", {"item_group": "Chicory Finished Goods"}],
				},
				"rows": get_powder_by_category("All"),
			},
		],
		"operations_queue": _get_operations_queue(),
	}


@frappe.whitelist()
def get_raw_roots_by_category(category: str = "All"):
	items = [
		{
			"code": "RAW-CHICORY-ROOT",
			"name": "Raw Chicory Root",
			"group": "Chicory Raw Material",
			"uom": "Kg",
			"threshold_critical": 50,
			"threshold_low": 200,
		},
		{
			"code": "DRIED-CHICORY",
			"name": "Dried Chicory",
			"group": "Chicory Semi-Finished",
			"uom": "Kg",
			"threshold_critical": 30,
			"threshold_low": 100,
		},
		{
			"code": "ROASTED-CHICORY",
			"name": "Roasted Chicory",
			"group": "Chicory Semi-Finished",
			"uom": "Kg",
			"threshold_critical": 20,
			"threshold_low": 80,
		},
	]
	return _build_low_stock_rows(items, category)


@frappe.whitelist()
def get_packaging_by_category(category: str = "All"):
	items = [
		{
			"code": "POUCH-1KG",
			"name": "Pouch 1Kg",
			"group": "Chicory Packaging",
			"uom": "Nos",
			"threshold_critical": 200,
			"threshold_low": 1000,
		},
		{
			"code": "CORRUGATED-BOX-20KG",
			"name": "Corrugated Box 20Kg",
			"group": "Chicory Packaging",
			"uom": "Nos",
			"threshold_critical": 50,
			"threshold_low": 250,
		},
		{
			"code": "BAG-50KG",
			"name": "PP Woven Bag 50Kg",
			"group": "Chicory Packaging",
			"uom": "Nos",
			"threshold_critical": 30,
			"threshold_low": 150,
		},
	]
	return _build_low_stock_rows(items, category)


@frappe.whitelist()
def get_powder_by_category(category: str = "All"):
	items = [
		{
			"code": "CHICORY-POWDER-1KG",
			"name": "Chicory Powder 1Kg",
			"group": "Chicory Finished Goods",
			"uom": "Nos",
			"threshold_critical": 100,
			"threshold_low": 500,
		},
		{
			"code": "BULK-CHICORY-POWDER",
			"name": "Bulk Chicory Powder",
			"group": "Chicory Semi-Finished",
			"uom": "Kg",
			"threshold_critical": 100,
			"threshold_low": 300,
		},
	]
	return _build_low_stock_rows(items, category)


def get_low_stock_bar_rows():
	"""Rows for the Low Stock dashboard bar chart (low/critical first, else lowest on-hand)."""
	rows = []
	rows.extend(get_raw_roots_by_category("All"))
	rows.extend(get_packaging_by_category("All"))
	rows.extend(get_powder_by_category("All"))
	rows.sort(key=lambda x: (x.get("priority", 2), x.get("stock_qty", 0)))
	low_rows = [r for r in rows if r.get("priority", 2) <= 1]
	display_rows = low_rows[:12] if low_rows else rows[:12]
	bar_rows = []
	for row in display_rows:
		title = row.get("title") or ""
		label = title.split(" - ", 1)[0] if " - " in title else title
		bar_rows.append({"label": label, "stock_qty": row.get("stock_qty", 0)})
	return bar_rows


def _build_low_stock_rows(item_defs, category="All"):
	item_codes = [it["code"] for it in item_defs]
	stock_map = _get_stock_by_item(item_codes)
	rows = []
	for it in item_defs:
		code = it["code"]
		stock_qty = flt(stock_map.get(code, 0.0), 2)
		tcrit = it["threshold_critical"]
		tlow = it["threshold_low"]

		if stock_qty <= tcrit:
			badge_label = (
				_("Procure Now")
				if "Raw" in it["group"]
				else (_("Order Now") if "Packaging" in it["group"] else _("Produce Now"))
			)
			badge_color = "red"
			priority = 0
		elif stock_qty <= tlow:
			badge_label = _("Low Stock")
			badge_color = "orange"
			priority = 1
		else:
			badge_label = _("Adequate")
			badge_color = "green"
			priority = 2

		row = {
			"priority": priority,
			"stock_qty": stock_qty,
			"title": f"{code} - {it['name']}",
			"subtitle": f"{it['group']} • Stock UOM: {it['uom']}",
			"metric_primary": f"{stock_qty:,.1f} {it['uom']}",
			"badge_label": badge_label,
			"badge_color": badge_color,
			"doctype": "Item",
			"docname": code,
		}

		cat = (category or "All").strip()
		if cat == "Critical" and priority != 0:
			continue
		if cat == "Raw Material" and "Raw" not in it["group"]:
			continue
		if cat == "Semi-Finished" and "Semi" not in it["group"]:
			continue
		if cat == "Pouches" and "POUCH" not in code:
			continue
		if cat == "Bags & Boxes" and "POUCH" in code:
			continue
		if cat == "Retail Packs" and "POWDER-1KG" not in code:
			continue
		if cat == "Bulk Powder" and "BULK" not in code:
			continue

		rows.append(row)

	rows.sort(key=lambda x: (x["priority"], x["stock_qty"]))
	return rows[:MAX_WIDGET_ROWS]


def _get_operations_queue():
	inwards = frappe.get_all(
		"Chicory Root Inward",
		fields=["name", "supplier", "net_weight", "docstatus", "posting_date", "vehicle_no"],
		order_by="creation desc",
		limit=5,
	)
	inward_rows = [
		{
			"title": f"{inv.name} • {inv.vehicle_no or 'Vehicle'}",
			"subtitle": f"{inv.supplier or 'Direct Farmer'} • {inv.posting_date}",
			"metric_primary": f"{flt(inv.net_weight, 1):,.1f} Kg",
			"badge_label": "Submitted" if inv.docstatus == 1 else "Draft",
			"badge_color": "green" if inv.docstatus == 1 else "blue",
			"doctype": "Chicory Root Inward",
			"docname": inv.name,
		}
		for inv in inwards
	]

	work_orders = frappe.get_all(
		"Work Order",
		filters={"docstatus": ["in", [0, 1]], "status": ["not in", ["Cancelled", "Closed"]]},
		fields=["name", "production_item", "qty", "produced_qty", "status"],
		order_by="creation desc",
		limit=5,
	)
	wo_rows = [
		{
			"title": f"{wo.name} ({wo.production_item})",
			"subtitle": f"Status: {wo.status} • Planned: {flt(wo.qty, 1)}",
			"metric_primary": f"{flt(wo.produced_qty, 1)} / {flt(wo.qty, 1)} Nos",
			"badge_label": wo.status,
			"badge_color": "blue" if wo.status == "In Process" else "orange",
			"doctype": "Work Order",
			"docname": wo.name,
		}
		for wo in work_orders
	]

	invoices = frappe.get_all(
		"Sales Invoice",
		fields=["name", "customer", "grand_total", "status", "posting_date"],
		order_by="creation desc",
		limit=5,
	)
	inv_rows = [
		{
			"title": f"{inv.name} • {inv.customer or 'Customer'}",
			"subtitle": f"Date: {inv.posting_date} • {inv.status}",
			"metric_primary": f"₹ {flt(inv.grand_total, 2):,.2f}",
			"badge_label": inv.status or "Submitted",
			"badge_color": "green" if inv.status == "Paid" else "blue",
			"doctype": "Sales Invoice",
			"docname": inv.name,
		}
		for inv in invoices
	]

	return [
		{
			"title": _("Recent Root Inward Slips"),
			"doctype": "Chicory Root Inward",
			"primary_action": {"label": _("New Inward"), "doctype": "Chicory Root Inward"},
			"footer_action": {"label": _("View All Inwards"), "route": ["List", "Chicory Root Inward"]},
			"rows": inward_rows,
		},
		{
			"title": _("Active Production Work Orders"),
			"doctype": "Work Order",
			"primary_action": {"label": _("New Order"), "doctype": "Work Order"},
			"footer_action": {"label": _("View Work Orders"), "route": ["List", "Work Order"]},
			"rows": wo_rows,
		},
		{
			"title": _("Recent Powder Dispatches & Bills"),
			"doctype": "Sales Invoice",
			"primary_action": {"label": _("New Invoice"), "doctype": "Sales Invoice"},
			"footer_action": {"label": _("View Invoices"), "route": ["List", "Sales Invoice"]},
			"rows": inv_rows,
		},
	]
