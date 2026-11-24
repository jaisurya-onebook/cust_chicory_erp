import frappe

SUPPORTED = ("Purchase Receipt", "Sales Invoice", "Payment Entry")


def build_voucher(doctype, name):
	"""Build one Tally voucher dict for a document."""
	document = frappe.get_doc(doctype, name)
	builders = {
		"Purchase Receipt": _purchase,
		"Sales Invoice": _sales,
		"Payment Entry": _payment_entry,
	}
	if doctype not in builders:
		frappe.throw(f"{doctype} cannot be exported to Tally.")
	return builders[doctype](document)


def _purchase(document):
	total = document.grand_total or document.total or 0.0
	supplier = document.supplier or "Supplier"
	delivery_no = getattr(document, "supplier_delivery_note", None) or document.name
	return {
		"type": "Purchase",
		"date": document.posting_date,
		"number": delivery_no,
		"party": supplier,
		"narration": f"Chicory root purchase {document.name}",
		"entries": [
			{"ledger": supplier, "amount": total, "is_debit": False},
			{"ledger": "Stock Received But Not Billed", "amount": total, "is_debit": True},
		],
	}


def _sales(document):
	total = document.grand_total or document.total or 0.0
	customer = document.customer or "Customer"
	return {
		"type": "Sales",
		"date": document.posting_date,
		"number": document.name,
		"party": customer,
		"narration": f"Chicory powder invoice {document.name}",
		"entries": [
			{"ledger": customer, "amount": total, "is_debit": True},
			{"ledger": "Sales - Chicory", "amount": total, "is_debit": False},
		],
	}


def _payment_entry(document):
	amount = document.paid_amount or document.received_amount or 0.0
	party = document.party or "Party"
	paid_from = document.paid_from or "Cash"
	paid_to = document.paid_to or "Bank"
	if getattr(document, "payment_type", "") == "Receive":
		return {
			"type": "Receipt",
			"date": document.posting_date,
			"number": document.name,
			"party": party,
			"narration": f"Payment receipt {document.name}",
			"entries": [
				{"ledger": paid_to, "amount": amount, "is_debit": True},
				{"ledger": party, "amount": amount, "is_debit": False},
			],
		}
	else:
		return {
			"type": "Payment",
			"date": document.posting_date,
			"number": document.name,
			"party": party,
			"narration": f"Payment entry {document.name}",
			"entries": [
				{"ledger": party, "amount": amount, "is_debit": True},
				{"ledger": paid_from, "amount": amount, "is_debit": False},
			],
		}
