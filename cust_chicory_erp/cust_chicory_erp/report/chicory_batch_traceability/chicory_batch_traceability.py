import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	return columns, data, None, chart


def get_columns():
	return [
		{
			"label": _("Finished Batch"),
			"fieldname": "finished_batch",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 160,
		},
		{
			"label": _("Item"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 180,
		},
		{
			"label": _("Production Work Order"),
			"fieldname": "work_order",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 170,
		},
		{
			"label": _("Consumed Raw Batch"),
			"fieldname": "consumed_raw_batch",
			"fieldtype": "Link",
			"options": "Batch",
			"width": 170,
		},
		{
			"label": _("Raw Root Item"),
			"fieldname": "raw_root_item",
			"fieldtype": "Link",
			"options": "Item",
			"width": 160,
		},
		{
			"label": _("Purchase Receipt"),
			"fieldname": "purchase_receipt",
			"fieldtype": "Link",
			"options": "Purchase Receipt",
			"width": 170,
		},
		{
			"label": _("Supplier"),
			"fieldname": "supplier",
			"fieldtype": "Link",
			"options": "Supplier",
			"width": 200,
		},
		{
			"label": _("Inward Date"),
			"fieldname": "inward_date",
			"fieldtype": "Date",
			"width": 110,
		},
		{
			"label": _("Landed Cost Rate"),
			"fieldname": "landed_cost_rate",
			"fieldtype": "Currency",
			"width": 140,
		},
	]


def get_data(filters):
	"""
	Traces batches backward from Finished Goods Stock Entry (Manufacture)
	to raw material consumed batches and root Purchase Receipts / Chicory Root Inward.
	"""
	se = DocType("Stock Entry")
	sed = DocType("Stock Entry Detail")
	pr = DocType("Purchase Receipt")
	pri = DocType("Purchase Receipt Item")
	sbe = DocType("Serial and Batch Entry")

	# Step 1: Query Inward Batches from Purchase Receipt & CRI
	inward_receipts_map = {}

	# Fetch from Purchase Receipt Items using frappe.qb
	pr_query = (
		frappe.qb.from_(pr)
		.inner_join(pri).on(pri.parent == pr.name)
		.select(
			pr.name.as_("purchase_receipt"),
			pr.supplier,
			pr.posting_date.as_("inward_date"),
			pri.item_code.as_("raw_root_item"),
			pri.batch_no,
			pri.serial_and_batch_bundle,
			pri.valuation_rate.as_("landed_cost_rate"),
			pri.rate.as_("rate"),
		)
		.where(pr.docstatus == 1)
	)

	pr_rows = pr_query.run(as_dict=True)
	pr_bundles = [r.serial_and_batch_bundle for r in pr_rows if not r.get("batch_no") and r.get("serial_and_batch_bundle")]
	pr_bundle_map = {}
	if pr_bundles:
		bundle_rows = (
			frappe.qb.from_(sbe)
			.select(sbe.parent, sbe.batch_no)
			.where(sbe.parent.isin(pr_bundles))
		).run(as_dict=True)
		for s in bundle_rows:
			if s.parent not in pr_bundle_map and s.batch_no:
				pr_bundle_map[s.parent] = s.batch_no

	for r in pr_rows:
		batch = r.get("batch_no") or pr_bundle_map.get(r.get("serial_and_batch_bundle"))
		if batch:
			inward_receipts_map[batch] = {
				"purchase_receipt": r.purchase_receipt,
				"supplier": r.supplier,
				"inward_date": r.inward_date,
				"raw_root_item": r.raw_root_item,
				"landed_cost_rate": flt(r.landed_cost_rate or r.rate),
			}

	# Check Chicory Root Inward for enriched landed cost rate & batch links
	if frappe.db.exists("DocType", "Chicory Root Inward"):
		cri = DocType("Chicory Root Inward")
		cri_query = (
			frappe.qb.from_(cri)
			.select(
				cri.name,
				cri.batch_no,
				cri.item_code.as_("raw_root_item"),
				cri.purchase_receipt,
				cri.supplier,
				cri.posting_date.as_("inward_date"),
				cri.rate_per_kg,
				cri.total_landed_cost,
				cri.payable_weight,
			)
			.where(cri.docstatus == 1)
		)
		for r in cri_query.run(as_dict=True):
			batch = r.get("batch_no")
			if batch:
				l_rate = flt(r.rate_per_kg)
				if flt(r.payable_weight) > 0 and flt(r.total_landed_cost) > 0:
					l_rate = flt(r.total_landed_cost) / flt(r.payable_weight)

				existing = inward_receipts_map.get(batch, {})
				inward_receipts_map[batch] = {
					"purchase_receipt": r.purchase_receipt or existing.get("purchase_receipt"),
					"supplier": r.supplier or existing.get("supplier"),
					"inward_date": r.inward_date or existing.get("inward_date"),
					"raw_root_item": r.raw_root_item or existing.get("raw_root_item"),
					"landed_cost_rate": l_rate or existing.get("landed_cost_rate", 0.0),
				}

	# Step 2: Query Stock Entries for Manufacture
	se_mfg_query = (
		frappe.qb.from_(se)
		.inner_join(sed).on(sed.parent == se.name)
		.select(
			se.name.as_("stock_entry"),
			se.work_order,
			se.posting_date,
			sed.item_code,
			sed.batch_no,
			sed.serial_and_batch_bundle,
			sed.is_finished_item,
			sed.t_warehouse,
			sed.s_warehouse,
		)
		.where(se.docstatus == 1)
		.where(se.purpose == "Manufacture")
	)

	if filters.get("from_date"):
		se_mfg_query = se_mfg_query.where(se.posting_date >= filters.get("from_date"))
	if filters.get("to_date"):
		se_mfg_query = se_mfg_query.where(se.posting_date <= filters.get("to_date"))

	mfg_rows = se_mfg_query.run(as_dict=True)

	# Group by Stock Entry: separate FG rows and Consumed raw rows
	entries_fg = {}
	entries_consumed = {}
	work_orders_consumed = {}

	mfg_bundles = [row.serial_and_batch_bundle for row in mfg_rows if not row.batch_no and row.serial_and_batch_bundle]
	mfg_bundle_map = {}
	if mfg_bundles:
		bundle_rows = (
			frappe.qb.from_(sbe)
			.select(sbe.parent, sbe.batch_no)
			.where(sbe.parent.isin(mfg_bundles))
		).run(as_dict=True)
		for s in bundle_rows:
			if s.parent not in mfg_bundle_map and s.batch_no:
				mfg_bundle_map[s.parent] = s.batch_no

	for row in mfg_rows:
		entry = row.stock_entry
		is_fg = row.is_finished_item or (row.t_warehouse and not row.s_warehouse)

		batch = row.batch_no or mfg_bundle_map.get(row.serial_and_batch_bundle)

		if is_fg:
			entries_fg.setdefault(entry, []).append({
				"item_code": row.item_code,
				"finished_batch": batch,
				"work_order": row.work_order,
				"posting_date": row.posting_date,
			})
		else:
			consumed_item = {
				"item_code": row.item_code,
				"raw_batch": batch,
			}
			entries_consumed.setdefault(entry, []).append(consumed_item)
			if row.work_order:
				work_orders_consumed.setdefault(row.work_order, []).append(consumed_item)

	# Also check Material Transfer for Manufacture stock entries linked to Work Orders
	se_transfer_query = (
		frappe.qb.from_(se)
		.inner_join(sed).on(sed.parent == se.name)
		.select(
			se.name.as_("stock_entry"),
			se.work_order,
			sed.item_code,
			sed.batch_no,
			sed.serial_and_batch_bundle,
		)
		.where(se.docstatus == 1)
		.where(se.purpose.isin(["Material Transfer for Manufacture", "Material Transfer"]))
		.where(se.work_order.isnotnull() & (se.work_order != ""))
	)
	transfer_rows = se_transfer_query.run(as_dict=True)
	transfer_bundles = [row.serial_and_batch_bundle for row in transfer_rows if not row.batch_no and row.serial_and_batch_bundle]
	transfer_bundle_map = {}
	if transfer_bundles:
		bundle_rows = (
			frappe.qb.from_(sbe)
			.select(sbe.parent, sbe.batch_no)
			.where(sbe.parent.isin(transfer_bundles))
		).run(as_dict=True)
		for s in bundle_rows:
			if s.parent not in transfer_bundle_map and s.batch_no:
				transfer_bundle_map[s.parent] = s.batch_no

	for row in transfer_rows:
		batch = row.batch_no or transfer_bundle_map.get(row.serial_and_batch_bundle)
		if row.work_order:
			work_orders_consumed.setdefault(row.work_order, []).append({
				"item_code": row.item_code,
				"raw_batch": batch,
			})

	# Step 3: Build output rows correlating Finished Goods to Raw Inward
	data = []

	for entry, fg_list in entries_fg.items():
		consumed_list = entries_consumed.get(entry) or []
		for fg in fg_list:
			wo = fg.get("work_order")
			if not consumed_list and wo:
				consumed_list = work_orders_consumed.get(wo, [])

			if consumed_list:
				for c in consumed_list:
					raw_batch = c.get("raw_batch")
					inward_info = inward_receipts_map.get(raw_batch, {})

					row = {
						"finished_batch": fg.get("finished_batch"),
						"item_code": fg.get("item_code"),
						"work_order": wo,
						"consumed_raw_batch": raw_batch,
						"raw_root_item": inward_info.get("raw_root_item") or c.get("item_code"),
						"purchase_receipt": inward_info.get("purchase_receipt"),
						"supplier": inward_info.get("supplier"),
						"inward_date": inward_info.get("inward_date"),
						"landed_cost_rate": inward_info.get("landed_cost_rate", 0.0),
					}
					data.append(row)
			else:
				data.append({
					"finished_batch": fg.get("finished_batch"),
					"item_code": fg.get("item_code"),
					"work_order": wo,
					"consumed_raw_batch": None,
					"raw_root_item": None,
					"purchase_receipt": None,
					"supplier": None,
					"inward_date": None,
					"landed_cost_rate": 0.0,
				})

	# Apply user filters
	filtered_data = []
	for row in data:
		if filters.get("batch_no"):
			b_filter = filters.get("batch_no").strip()
			if b_filter != row.get("finished_batch") and b_filter != row.get("consumed_raw_batch"):
				continue
		if filters.get("item_code"):
			i_filter = filters.get("item_code").strip()
			if i_filter != row.get("item_code") and i_filter != row.get("raw_root_item"):
				continue
		filtered_data.append(row)

	return filtered_data


def get_chart(data):
	if not data:
		return None

	suppliers = {}
	for d in data:
		supp = d.get("supplier") or _("Unknown")
		suppliers[supp] = suppliers.get(supp, 0) + 1

	return {
		"data": {
			"labels": list(suppliers.keys())[:10],
			"datasets": [{"name": _("Batches Traced"), "values": list(suppliers.values())[:10]}],
		},
		"type": "bar",
	}
