import frappe
from frappe import _
from frappe.utils import flt


def validate_duplicate_freight(doc, method=None):
	"""Validate Landed Cost Voucher on validate.

	Checks linked Purchase Receipts:
	1. If a receipt already has freight accounts in its taxes child table,
	   raises frappe.ValidationError preventing duplicate capitalization.
	2. If an existing submitted LCV already capitalized the same expense account
	   for the same receipt, raises frappe.ValidationError.
	"""
	if not doc.get("taxes") or not doc.get("purchase_receipts"):
		return

	lcv = frappe.qb.DocType("Landed Cost Voucher")
	lcv_pr = frappe.qb.DocType("Landed Cost Purchase Receipt")
	lcv_tax = frappe.qb.DocType("Landed Cost Taxes and Charges")

	receipt_names = [
		pr_row.receipt_document
		for pr_row in doc.get("purchase_receipts", [])
		if pr_row.receipt_document and (pr_row.receipt_document_type or "Purchase Receipt") == "Purchase Receipt"
	]
	expense_accounts = [
		tax_row.expense_account
		for tax_row in doc.get("taxes", [])
		if tax_row.expense_account
	]

	if not receipt_names or not expense_accounts:
		return

	# 1. Check if linked receipts already have freight accounts in their taxes table
	for receipt_name in receipt_names:
		if not frappe.db.exists("Purchase Receipt", receipt_name):
			continue
		pr_doc = frappe.get_doc("Purchase Receipt", receipt_name)

		for pr_tax in pr_doc.get("taxes", []):
			account_head = pr_tax.account_head or ""
			tax_has_amount = flt(pr_tax.tax_amount) > 0 or flt(pr_tax.base_tax_amount) > 0

			for expense_account in expense_accounts:
				is_exact_match = account_head == expense_account
				is_freight_match = (
					"freight" in expense_account.lower()
					and (
						"freight" in account_head.lower()
						or "freight" in (pr_tax.description or "").lower()
					)
				)

				if (is_exact_match or is_freight_match) and (tax_has_amount or is_exact_match):
					matched_account = account_head or pr_tax.description or expense_account
					frappe.throw(
						_(
							"Purchase Receipt {0} already contains freight/charges for account {1} in its taxes table. Cannot capitalize duplicate freight via Landed Cost Voucher."
						).format(receipt_name, matched_account),
						frappe.ValidationError,
					)

	# 2. Check if an existing submitted LCV exists for same receipts and expense accounts in a single query
	query = (
		frappe.qb.from_(lcv)
		.join(lcv_pr).on(lcv_pr.parent == lcv.name)
		.join(lcv_tax).on(lcv_tax.parent == lcv.name)
		.select(lcv.name, lcv_pr.receipt_document, lcv_tax.expense_account)
		.where(
			(lcv.docstatus == 1)
			& (lcv.name != (doc.name or ""))
			& (lcv_pr.receipt_document.isin(receipt_names))
			& (lcv_tax.expense_account.isin(expense_accounts))
		)
	)
	existing = query.run(as_dict=True)
	if existing:
		first = existing[0]
		frappe.throw(
			_(
				"Purchase Receipt {0} already has charges capitalized via submitted Landed Cost Voucher {1} for expense account {2}."
			).format(first.receipt_document, first.name, first.expense_account),
			frappe.ValidationError,
		)
