# Copyright (c) 2026, Jaisurya and contributors
# For license information, please see license.txt

import frappe
from frappe import _

_CANCEL_ORDER = [
	"Payment Entry",
	"Sales Invoice",
	"Delivery Note",
	"Sales Order",
	"Stock Entry",
	"Job Card",
	"Quality Inspection",
	"Chicory Root Inward",
	"Landed Cost Voucher",
	"Purchase Receipt",
	"Work Order",
	"Purchase Order",
]


def _cancel_submitted(doctype: str) -> int:
	cancelled = 0
	for _ in range(12):
		names = frappe.get_all(doctype, filters={"docstatus": 1}, pluck="name", limit_page_length=500)
		if not names:
			break
		progress = False
		for name in names:
			doc = frappe.get_doc(doctype, name)
			doc.flags.ignore_links = True
			try:
				doc.cancel()
				cancelled += 1
				progress = True
			except frappe.LinkValidationError:
				frappe.db.rollback()
			except frappe.ValidationError as exc:
				if "Cancel" in str(exc) and "first" in str(exc):
					frappe.db.rollback()
				else:
					raise
		if progress:
			frappe.db.commit()
		else:
			break
	return cancelled


def _delete_drafts(doctype: str) -> int:
	deleted = 0
	for name in frappe.get_all(doctype, filters={"docstatus": 0}, pluck="name", limit_page_length=500):
		frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
		deleted += 1
	if deleted:
		frappe.db.commit()
	return deleted


@frappe.whitelist(methods=["POST"])
def clear_transactional_data() -> dict:
	"""Cancel submitted and delete draft manufacturing / trading documents."""
	frappe.only_for("System Manager")
	summary = {}
	for dt in _CANCEL_ORDER:
		summary[f"cancelled_{dt.replace(' ', '_').lower()}"] = _cancel_submitted(dt)
		summary[f"deleted_draft_{dt.replace(' ', '_').lower()}"] = _delete_drafts(dt)
	frappe.clear_cache()
	return {"status": "ok", "summary": summary}


@frappe.whitelist(methods=["POST"])
def ensure_chicory_masters(company: str | None = None) -> dict:
	"""Idempotent production masters (items, BOM, parties, warehouses)."""
	frappe.only_for("System Manager")
	from cust_chicory_erp.setup.setup_masters import setup_chicory_masters

	setup_chicory_masters(company=company)
	frappe.db.commit()
	company = company or frappe.db.get_single_value("Global Defaults", "default_company")
	return {"status": "ok", "company": company}


@frappe.whitelist(methods=["POST"])
def finalize_and_submit_work_order(work_order: str) -> dict:
	"""Populate operations from BOM/routing and submit the work order (REST helper)."""
	frappe.only_for("System Manager")
	wo = frappe.get_doc("Work Order", work_order)
	wo.set_work_order_operations()
	wo.save(ignore_permissions=True)
	wo.submit()
	return wo.as_dict()


@frappe.whitelist(methods=["POST"])
def reset_site_for_api_seed(company: str | None = None) -> dict:
	"""Clear transactional data then refresh chicory masters."""
	clear_summary = clear_transactional_data()
	master_summary = ensure_chicory_masters(company=company)
	return {"status": "ok", "clear": clear_summary, "masters": master_summary}