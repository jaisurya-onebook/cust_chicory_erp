import frappe
from frappe import _
from frappe.utils.xlsxutils import make_xlsx

from cust_chicory_erp.tally.voucher_builders import SUPPORTED, build_voucher
from cust_chicory_erp.tally.xml import build_envelope


def _tally_company():
	return frappe.defaults.get_global_default("company") or "Chicory Agro Industries Ltd"


def get_documents(doctype, from_date=None, to_date=None):
	filters = {"docstatus": 1}
	if from_date and to_date:
		filters["posting_date"] = ["between", [from_date, to_date]]
	elif from_date:
		filters["posting_date"] = [">=", from_date]
	elif to_date:
		filters["posting_date"] = ["<=", to_date]
	return frappe.get_list(
		doctype, filters=filters, pluck="name", order_by="posting_date, creation", limit=500
	)


def _build_vouchers(doctype, names):
	check_supported(doctype)
	vouchers = []
	for name in names:
		frappe.has_permission(doctype, "read", doc=name, throw=True)
		vouchers.append(build_voucher(doctype, name))
	return vouchers


def get_preview(doctype, names):
	company = _tally_company()
	vouchers = _build_vouchers(doctype, names)
	return {
		"company": company,
		"count": len(vouchers),
		"xml": build_envelope(company, vouchers),
		"rows": [_row(voucher) for voucher in vouchers],
	}


def get_xml_bytes(doctype, names):
	company = _tally_company()
	vouchers = _build_vouchers(doctype, names)
	return build_envelope(company, vouchers).encode("utf-8")


def get_workbook(doctype, names):
	vouchers = _build_vouchers(doctype, names)
	rows = [
		["Date", "Voucher Type", "Number", "Party", "Debit Ledger", "Credit Ledger", "Amount", "Narration"]
	]
	rows += [
		[
			row["date"],
			row["type"],
			row["number"],
			row["party"],
			row["debit"],
			row["credit"],
			row["amount"],
			row["narration"],
		]
		for row in (_row(voucher) for voucher in vouchers)
	]
	return make_xlsx(rows, "Tally Vouchers").getvalue()


def _row(voucher):
	debit = next((entry for entry in voucher["entries"] if entry["is_debit"]), None) or voucher["entries"][0]
	credit = next((entry for entry in voucher["entries"] if not entry["is_debit"]), None) or voucher["entries"][-1]
	return {
		"date": str(voucher["date"]),
		"type": voucher["type"],
		"number": voucher["number"],
		"party": voucher["party"],
		"debit": debit["ledger"],
		"credit": credit["ledger"],
		"amount": debit["amount"],
		"narration": voucher["narration"],
	}


def check_supported(doctype):
	if doctype not in SUPPORTED:
		frappe.throw(_("{0} cannot be exported to Tally.").format(doctype))
