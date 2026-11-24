#!/usr/bin/env python3
"""Seed Chicory purchase-to-delivery flow using only Frappe REST + token auth."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

COMPANY = "chicory"
SUPPLIER_NAME = "Anandapur Kheda Chicory Producers Company Ltd"
CUSTOMER_NAME = "ITC Limited"
TRANSPORTER_NAME = "VRL Logistics Ltd"
WEIGHBRIDGE_OPERATOR = "Anil Sharma"
UNLOADING_WORKER = "Mahesh Yadav"
RAW_WH = "Raw Material - Cc"
WIP_WH = "WIP Production - Cc"
FG_WH = "Finished Goods - Cc"
PACK_WH = "Packaging Stores - Cc"
ROOT_ITEM = "RAW-CHICORY-ROOT"
POUCH_ITEM = "POUCH-1KG"
FG_ITEM = "CHICORY-POWDER-1KG"
QUALITY_PARAMS = [
	"Moisture %",
	"Foreign Matter / Dirt",
	"Damaged Roots",
	"Aqueous Extract",
	"Total Ash %",
]


class FrappeRestClient:
	def __init__(self, base_url: str, token: str):
		self.base_url = base_url.rstrip("/")
		self.session = requests.Session()
		self.session.headers.update(
			{
				"Authorization": f"token {token}",
				"Content-Type": "application/json",
				"Accept": "application/json",
			}
		)

	def _raise(self, response: requests.Response) -> None:
		if response.ok:
			return
		try:
			payload = response.json()
			exc = payload.get("exception") or payload.get("message") or payload
		except Exception:
			exc = response.text
		raise RuntimeError(f"HTTP {response.status_code}: {exc}")

	def method(self, path: str, **kwargs: Any) -> Any:
		url = f"{self.base_url}/api/method/{path}"
		response = self.session.post(url, json=kwargs, timeout=120)
		self._raise(response)
		data = response.json()
		if data.get("exc"):
			raise RuntimeError(data["exc"])
		return data.get("message")

	def get_doc(self, doctype: str, name: str) -> dict:
		url = f"{self.base_url}/api/resource/{requests.utils.quote(doctype)}/{requests.utils.quote(name)}"
		response = self.session.get(url, timeout=60)
		self._raise(response)
		return response.json()["data"]

	def insert(self, doc: dict) -> dict:
		return self.method("frappe.client.insert", doc=doc)

	def save(self, doc: dict) -> dict:
		return self.method("frappe.client.save", doc=doc)

	def submit(self, doc: dict) -> dict:
		return self.method("frappe.client.submit", doc=doc)

	def set_value(self, doctype: str, name: str, fieldname: str, value: Any) -> None:
		self.method(
			"frappe.client.set_value",
			doctype=doctype,
			name=name,
			fieldname=fieldname,
			value=value,
		)

	def get_value(self, doctype: str, filters: dict, fieldname: str) -> Any:
		value = self.method(
			"frappe.client.get_value",
			doctype=doctype,
			filters=filters,
			fieldname=fieldname,
		)
		if isinstance(value, dict) and fieldname in value:
			return value[fieldname]
		if isinstance(value, dict) and len(value) == 1:
			return next(iter(value.values()))
		return value

	def get_list(
		self, doctype: str, filters: dict | None = None, fields: list | None = None, order_by: str | None = None
	) -> list:
		return self.method(
			"frappe.client.get_list",
			doctype=doctype,
			filters=filters or {},
			fields=fields or ["name"],
			order_by=order_by,
			limit_page_length=500,
		)

	def today(self) -> str:
		return datetime.now().strftime("%Y-%m-%d")

	def run_doc_method(self, doc: dict, method: str) -> dict:
		if doc.get("name"):
			self.method(
				"frappe.handler.run_doc_method",
				dt=doc["doctype"],
				dn=doc["name"],
				method=method,
			)
			return self.get_doc(doc["doctype"], doc["name"])
		updated = self.method("frappe.handler.run_doc_method", docs=doc, method=method)
		if isinstance(updated, dict) and updated.get("doctype"):
			return updated
		return doc


def ensure_quality_parameter(client: FrappeRestClient, param_name: str) -> None:
	exists = client.get_value("Quality Inspection Parameter", {"parameter": param_name}, "name")
	if not exists:
		client.insert(
			{
				"doctype": "Quality Inspection Parameter",
				"parameter": param_name,
				"description": param_name,
			}
		)


def resolve_employee(client: FrappeRestClient, first_name: str) -> str:
	name = client.get_value("Employee", {"first_name": first_name, "company": COMPANY, "status": "Active"}, "name")
	if not name:
		name = client.get_list(
			"Employee",
			filters={"first_name": first_name, "company": COMPANY},
			fields=["name"],
			order_by="creation desc",
		)[0]["name"]
	return name


def create_chicory_root_inward(
	client: FrappeRestClient,
	*,
	today: str,
	supplier: str,
	transporter: str,
	root_batch_id: str,
	purchase_receipt: str,
	landed_cost_voucher: str,
) -> dict:
	operator = resolve_employee(client, WEIGHBRIDGE_OPERATOR)
	unloading_worker = resolve_employee(client, UNLOADING_WORKER)
	gross_weight = 5200.0
	tare_weight = 5000.0
	net_weight = 200.0
	payable_weight = 200.0
	rate_per_kg = 40.0
	material_amount = payable_weight * rate_per_kg
	freight_amount = 800.0
	loading_charges = 200.0
	unloading_charges = 100.0
	total_landed_cost = freight_amount + loading_charges + unloading_charges
	net_payable_to_farmer = material_amount

	doc = client.insert(
		{
			"doctype": "Chicory Root Inward",
			"naming_series": "CRI-.YYYY.-.#####",
			"company": COMPANY,
			"supplier": supplier,
			"posting_date": today,
			"vehicle_no": "GJ-06-RM-4521",
			"operator": operator,
			"unloading_worker": unloading_worker,
			"item_code": ROOT_ITEM,
			"warehouse": RAW_WH,
			"batch_no": root_batch_id,
			"purchase_receipt": purchase_receipt,
			"landed_cost_voucher": landed_cost_voucher,
			"gross_weight": gross_weight,
			"tare_weight": tare_weight,
			"net_weight": net_weight,
			"mud_deduction_pct": 0.0,
			"moisture_deduction_pct": 0.0,
			"deduction_weight": 0.0,
			"payable_weight": payable_weight,
			"rate_per_kg": rate_per_kg,
			"material_amount": material_amount,
			"transporter": transporter,
			"freight_rate_type": "Fixed",
			"freight_rate": freight_amount,
			"freight_amount": freight_amount,
			"loading_charges": loading_charges,
			"unloading_charges": unloading_charges,
			"freight_borne_by": "Company (Landed Cost)",
			"net_payable_to_farmer": net_payable_to_farmer,
			"total_landed_cost": total_landed_cost,
		}
	)
	return client.submit(doc)


def resolve_party_name(client: FrappeRestClient, doctype: str, display_name: str) -> str:
	field = "supplier_name" if doctype == "Supplier" else "customer_name"
	name = client.get_value(doctype, {field: display_name}, "name")
	if not name:
		raise RuntimeError(f"{doctype} not found: {display_name}")
	return name


def seed_purchase_to_delivery(client: FrappeRestClient) -> dict:
	today = client.today()
	supplier = resolve_party_name(client, "Supplier", SUPPLIER_NAME)
	customer = resolve_party_name(client, "Customer", CUSTOMER_NAME)
	transporter = resolve_party_name(client, "Supplier", TRANSPORTER_NAME)

	# 1 — Purchase Order
	po = client.insert(
		{
			"doctype": "Purchase Order",
			"company": COMPANY,
			"supplier": supplier,
			"transaction_date": today,
			"schedule_date": today,
			"items": [
				{
					"item_code": ROOT_ITEM,
					"qty": 200,
					"rate": 40.0,
					"uom": "Kg",
					"stock_uom": "Kg",
					"warehouse": RAW_WH,
					"schedule_date": today,
				},
				{
					"item_code": POUCH_ITEM,
					"qty": 100,
					"rate": 2.0,
					"uom": "Nos",
					"stock_uom": "Nos",
					"warehouse": PACK_WH,
					"schedule_date": today,
				},
			],
		}
	)
	po = client.submit(po)

	# 2 — Raw root batch + Purchase Receipt
	root_batch_id = f"ROOT-ANAND-{datetime.now().strftime('%Y%m%d%H%M%S')}"
	client.insert(
		{
			"doctype": "Batch",
			"batch_id": root_batch_id,
			"item": ROOT_ITEM,
			"quality_status": "Passed",
			"supplier_lot_no": f"KHC-INWARD-{today.replace('-', '')}",
		}
	)

	client.set_value("Item", ROOT_ITEM, "inspection_required_before_purchase", 1)

	pr = client.insert(
		{
			"doctype": "Purchase Receipt",
			"company": COMPANY,
			"supplier": supplier,
			"posting_date": today,
			"weighbridge_slip_no": f"WBS-AN-{today.replace('-', '')}-1147",
			"vehicle_no": "GJ-06-RM-4521",
			"gross_weight": 5200.0,
			"tare_weight": 5000.0,
			"dirt_moisture_deduction_pct": 0.0,
			"freight_paid_by": "Company (Landed Cost)",
			"items": [
				{
					"purchase_order": po["name"],
					"purchase_order_item": po["items"][0]["name"],
					"item_code": ROOT_ITEM,
					"qty": 200,
					"rate": 40.0,
					"uom": "Kg",
					"stock_uom": "Kg",
					"warehouse": RAW_WH,
					"batch_no": root_batch_id,
				},
				{
					"purchase_order": po["name"],
					"purchase_order_item": po["items"][1]["name"],
					"item_code": POUCH_ITEM,
					"qty": 100,
					"rate": 2.0,
					"uom": "Nos",
					"stock_uom": "Nos",
					"warehouse": PACK_WH,
				},
			],
		}
	)

	for param in QUALITY_PARAMS[:3]:
		ensure_quality_parameter(client, param)

	qi_inward = client.insert(
		{
			"doctype": "Quality Inspection",
			"inspection_type": "Incoming",
			"inspected_by": "Administrator",
			"reference_type": "Purchase Receipt",
			"reference_name": pr["name"],
			"item_code": ROOT_ITEM,
			"batch_no": root_batch_id,
			"sample_size": 10,
			"manual_inspection": 1,
			"status": "Accepted",
			"readings": [
				{"specification": "Moisture %", "manual_inspection": 1, "status": "Accepted", "reading_1": "72.5"},
				{
					"specification": "Foreign Matter / Dirt",
					"manual_inspection": 1,
					"status": "Accepted",
					"reading_1": "1.2",
				},
				{"specification": "Damaged Roots", "manual_inspection": 1, "status": "Accepted", "reading_1": "0.5"},
			],
		}
	)
	client.submit(qi_inward)

	pr = client.get_doc("Purchase Receipt", pr["name"])
	pr = client.submit(pr)

	# 3 — Landed Cost Voucher
	freight_acc = "Freight and Forwarding Charges - Cc"
	loading_acc = "Expenses Included In Valuation - Cc"
	lcv = client.insert(
		{
			"doctype": "Landed Cost Voucher",
			"company": COMPANY,
			"posting_date": today,
			"distribute_charges_based_on": "Amount",
			"purchase_receipts": [
				{
					"receipt_document_type": "Purchase Receipt",
					"receipt_document": pr["name"],
					"supplier": supplier,
					"grand_total": pr["grand_total"],
					"posting_date": pr["posting_date"],
				}
			],
			"taxes": [
				{"expense_account": freight_acc, "description": "Gandhidham to Anand freight", "amount": 800.0},
				{"expense_account": loading_acc, "description": "Loading at supplier yard", "amount": 200.0},
				{"expense_account": loading_acc, "description": "Unloading at factory gate", "amount": 100.0},
			],
		}
	)
	lcv = client.run_doc_method(lcv, "get_items_from_purchase_receipts")
	lcv["items"] = [row for row in lcv.get("items", []) if row.get("item_code") == ROOT_ITEM]
	lcv = client.save(lcv)
	lcv = client.submit(lcv)

	cri = create_chicory_root_inward(
		client,
		today=today,
		supplier=supplier,
		transporter=transporter,
		root_batch_id=root_batch_id,
		purchase_receipt=pr["name"],
		landed_cost_voucher=lcv["name"],
	)

	# 4 — Work Order
	bom = client.get_value(
		"BOM",
		{"item": FG_ITEM, "is_active": 1, "is_default": 1, "docstatus": 1},
		"name",
	)
	if not bom:
		bom = client.get_value("BOM", {"item": FG_ITEM, "docstatus": 1}, "name")

	wo = client.insert(
		{
			"doctype": "Work Order",
			"company": COMPANY,
			"production_item": FG_ITEM,
			"bom_no": bom,
			"qty": 100,
			"wip_warehouse": WIP_WH,
			"fg_warehouse": FG_WH,
			"source_warehouse": RAW_WH,
			"planned_start_date": today,
		}
	)
	wo = client.method(
		"cust_chicory_erp.api.transaction_lifecycle.finalize_and_submit_work_order",
		work_order=wo["name"],
	)

	# 5 — Material transfer
	ste_transfer = client.method(
		"erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry",
		work_order_id=wo["name"],
		purpose="Material Transfer for Manufacture",
		qty=100,
	)
	for row in ste_transfer.get("items", []):
		if row.get("item_code") == ROOT_ITEM:
			row["s_warehouse"] = RAW_WH
			row["batch_no"] = root_batch_id
		elif row.get("item_code") == POUCH_ITEM:
			row["s_warehouse"] = PACK_WH
	ste_transfer = client.insert(ste_transfer)
	ste_transfer = client.submit(ste_transfer)

	# 6 — Job cards with stage losses
	job_cards = client.get_list(
		"Job Card",
		filters={"work_order": wo["name"]},
		fields=["name", "operation", "sequence_id"],
		order_by="sequence_id asc",
	)
	loss_profiles = {
		"Washing": {"in": 200.0, "out": 195.0, "loss": 5.0, "reason": "Wash Dirt & Debris", "moist": 74.0, "temp": 0.0},
		"Slicing": {"in": 195.0, "out": 192.0, "loss": 3.0, "reason": "Wash Dirt & Debris", "moist": 74.0, "temp": 0.0},
		"Drying": {"in": 192.0, "out": 120.0, "loss": 72.0, "reason": "Moisture Evaporation (Drying)", "moist": 12.0, "temp": 75.0},
		"Roasting": {"in": 120.0, "out": 105.0, "loss": 15.0, "reason": "Roasting Process Loss", "moist": 4.5, "temp": 185.0},
		"Grinding & Sieving": {"in": 105.0, "out": 100.0, "loss": 5.0, "reason": "Grinding Dust / Sieve Reject", "moist": 4.0, "temp": 30.0},
		"Packing": {"in": 100.0, "out": 100.0, "loss": 0.0, "reason": "", "moist": 3.8, "temp": 25.0},
	}
	base = datetime.now(timezone.utc)
	for idx, jc_meta in enumerate(job_cards):
		jc = client.get_doc("Job Card", jc_meta["name"])
		op = jc.get("operation")
		if op not in loss_profiles:
			continue
		prof = loss_profiles[op]
		jc["stage_input_qty"] = prof["in"]
		jc["stage_output_qty"] = prof["out"]
		jc["stage_process_loss_qty"] = prof["loss"]
		jc["process_loss_reason"] = prof["reason"]
		jc["moisture_pct"] = prof["moist"]
		jc["roast_temp_celsius"] = prof["temp"]
		jc["total_completed_qty"] = 100
		start_mins = 720 + (idx * 90)
		from_time = (base - timedelta(minutes=start_mins)).strftime("%Y-%m-%d %H:%M:%S")
		to_time = (base - timedelta(minutes=start_mins - 45)).strftime("%Y-%m-%d %H:%M:%S")
		jc["time_logs"] = [
			{
				"from_time": from_time,
				"to_time": to_time,
				"time_in_mins": 30,
				"completed_qty": 100,
			}
		]
		jc = client.save(jc)
		jc = client.submit(jc)

	# 7 — FG batch, quality, manufacture
	for param in ("Aqueous Extract", "Total Ash %"):
		ensure_quality_parameter(client, param)

	fg_batch_id = f"CP1K-ANAND-{datetime.now().strftime('%Y%m%d%H%M%S')}"
	expiry = (datetime.strptime(today, "%Y-%m-%d") + timedelta(days=365)).strftime("%Y-%m-%d")
	client.insert(
		{
			"doctype": "Batch",
			"batch_id": fg_batch_id,
			"item": FG_ITEM,
			"quality_status": "Passed",
			"expiry_date": expiry,
			"manufacturing_date": today,
		}
	)

	qi_fg = client.insert(
		{
			"doctype": "Quality Inspection",
			"inspection_type": "In Process",
			"inspected_by": "Administrator",
			"reference_type": "Job Card",
			"reference_name": job_cards[-1]["name"],
			"item_code": FG_ITEM,
			"batch_no": fg_batch_id,
			"sample_size": 5,
			"manual_inspection": 1,
			"status": "Accepted",
			"readings": [
				{"specification": "Aqueous Extract", "manual_inspection": 1, "status": "Accepted", "reading_1": "71.5"},
				{"specification": "Total Ash %", "manual_inspection": 1, "status": "Accepted", "reading_1": "5.1"},
				{"specification": "Moisture %", "manual_inspection": 1, "status": "Accepted", "reading_1": "3.8"},
			],
		}
	)
	client.submit(qi_fg)

	ste_mfg = client.method(
		"erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry",
		work_order_id=wo["name"],
		purpose="Manufacture",
		qty=100,
	)
	for row in ste_mfg.get("items", []):
		if row.get("item_code") == FG_ITEM:
			row["batch_no"] = fg_batch_id
		elif row.get("item_code") == ROOT_ITEM:
			row["batch_no"] = root_batch_id
	for cost in ste_mfg.get("additional_costs", []):
		if not cost.get("expense_account"):
			cost["expense_account"] = "Expenses Included In Valuation - Cc"
	ste_mfg = client.insert(ste_mfg)
	ste_mfg = client.get_doc("Stock Entry", ste_mfg["name"])
	for row in ste_mfg.get("items", []):
		if row.get("serial_and_batch_bundle") and row.get("batch_no"):
			del row["batch_no"]
	ste_mfg = client.submit(ste_mfg)

	# 8 — Sales order → Delivery → Invoice → Payment
	so = client.insert(
		{
			"doctype": "Sales Order",
			"company": COMPANY,
			"customer": customer,
			"transaction_date": today,
			"delivery_date": today,
			"items": [
				{
					"item_code": FG_ITEM,
					"qty": 20,
					"rate": 120.0,
					"warehouse": FG_WH,
					"delivery_date": today,
				}
			],
		}
	)
	so = client.submit(so)

	dn = client.insert(
		{
			"doctype": "Delivery Note",
			"company": COMPANY,
			"customer": customer,
			"posting_date": today,
			"items": [
				{
					"against_sales_order": so["name"],
					"so_detail": so["items"][0]["name"],
					"item_code": FG_ITEM,
					"qty": 20,
					"rate": 120.0,
					"warehouse": FG_WH,
					"batch_no": fg_batch_id,
				}
			],
		}
	)
	dn = client.submit(dn)

	si = client.insert(
		{
			"doctype": "Sales Invoice",
			"company": COMPANY,
			"customer": customer,
			"posting_date": today,
			"items": [
				{
					"delivery_note": dn["name"],
					"dn_detail": dn["items"][0]["name"],
					"item_code": FG_ITEM,
					"qty": 20,
					"rate": 120.0,
				}
			],
		}
	)
	si = client.submit(si)

	pe = client.method(
		"erpnext.accounts.doctype.payment_entry.payment_entry.get_payment_entry",
		dt="Sales Invoice",
		dn=si["name"],
	)
	pe["paid_to"] = "Cash - Cc"
	pe["reference_no"] = f"NEFT/HDFC/{today.replace('-', '')}884521"
	pe["reference_date"] = today
	pe = client.insert(pe)
	pe = client.submit(pe)

	return {
		"chicory_root_inward": cri["name"],
		"purchase_order": po["name"],
		"purchase_receipt": pr["name"],
		"landed_cost_voucher": lcv["name"],
		"work_order": wo["name"],
		"material_transfer": ste_transfer["name"],
		"manufacture_entry": ste_mfg["name"],
		"sales_order": so["name"],
		"delivery_note": dn["name"],
		"sales_invoice": si["name"],
		"payment_entry": pe["name"],
		"root_batch": root_batch_id,
		"finished_batch": fg_batch_id,
	}


def seed_root_inward_from_latest_pr(client: FrappeRestClient) -> dict:
	"""Submit one Chicory Root Inward linked to the latest submitted root purchase receipt."""
	today = client.today()
	supplier = resolve_party_name(client, "Supplier", SUPPLIER_NAME)
	transporter = resolve_party_name(client, "Supplier", TRANSPORTER_NAME)
	pr_rows = client.get_list(
		"Purchase Receipt",
		filters={"docstatus": 1, "company": COMPANY},
		fields=["name", "posting_date"],
		order_by="posting_date desc, creation desc",
	)
	if not pr_rows:
		raise RuntimeError("No submitted Purchase Receipt found; run full seed first.")
	pr = client.get_doc("Purchase Receipt", pr_rows[0]["name"])
	root_line = next((row for row in pr.get("items", []) if row.get("item_code") == ROOT_ITEM), None)
	if not root_line:
		raise RuntimeError(f"No {ROOT_ITEM} line on purchase receipt {pr['name']}")
	root_batch_id = root_line.get("batch_no")
	if not root_batch_id:
		raise RuntimeError("Purchase receipt has no batch on root item")

	lcv_name = client.get_list(
		"Landed Cost Voucher",
		filters={"docstatus": 1, "company": COMPANY},
		fields=["name"],
		order_by="posting_date desc, creation desc",
	)
	lcv = lcv_name[0]["name"] if lcv_name else ""

	cri = create_chicory_root_inward(
		client,
		today=today,
		supplier=supplier,
		transporter=transporter,
		root_batch_id=root_batch_id,
		purchase_receipt=pr["name"],
		landed_cost_voucher=lcv,
	)
	return {"chicory_root_inward": cri["name"], "purchase_receipt": pr["name"], "batch_no": root_batch_id}


def main() -> int:
	parser = argparse.ArgumentParser(description="Clear site and seed Chicory data via REST API token")
	parser.add_argument("--base-url", default="http://localhost:8003")
	parser.add_argument("--token", required=True, help="API key pair as key:secret")
	parser.add_argument(
		"--root-inward-only",
		action="store_true",
		help="Create and submit Chicory Root Inward from the latest purchase receipt",
	)
	parser.add_argument(
		"--skip-reset",
		action="store_true",
		help="Skip clearing data (use when retrying a failed seed)",
	)
	parser.add_argument(
		"--refresh-masters",
		action="store_true",
		help="Also run ensure_chicory_masters after clear",
	)
	args = parser.parse_args()

	client = FrappeRestClient(args.base_url, args.token)

	if args.root_inward_only:
		result = seed_root_inward_from_latest_pr(client)
		print(json.dumps(result, indent=2))
		print("Chicory Root Inward submitted via API.")
		return 0

	if not args.skip_reset:
		print("Clearing transactional data via API…")
		clear = client.method("cust_chicory_erp.api.transaction_lifecycle.clear_transactional_data")
		print(json.dumps(clear, indent=2))
		if args.refresh_masters:
			print("Refreshing chicory masters via API…")
			masters = client.method("cust_chicory_erp.api.transaction_lifecycle.ensure_chicory_masters")
			print(json.dumps(masters, indent=2))

	print("Running purchase → delivery workflow via API…")
	result = seed_purchase_to_delivery(client)
	print(json.dumps(result, indent=2))
	print("Completed successfully.")
	return 0


if __name__ == "__main__":
	sys.exit(main())