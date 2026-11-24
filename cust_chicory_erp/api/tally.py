import json
import frappe
from cust_chicory_erp.tally import preview


def _as_name_list(names):
	if isinstance(names, str):
		try:
			return json.loads(names)
		except Exception:
			return [names]
	return names or []


@frappe.whitelist()
def tally_list_documents(doctype, from_date=None, to_date=None):
	preview.check_supported(doctype)
	frappe.has_permission(doctype, "read", throw=True)
	return preview.get_documents(doctype, from_date, to_date)


@frappe.whitelist()
def tally_preview(doctype, names):
	preview.check_supported(doctype)
	frappe.has_permission(doctype, "read", throw=True)
	return preview.get_preview(doctype, _as_name_list(names))


@frappe.whitelist()
def tally_download_excel(doctype, names):
	from frappe.desk.utils import provide_binary_file

	preview.check_supported(doctype)
	frappe.has_permission(doctype, "read", throw=True)
	provide_binary_file(
		f"{frappe.scrub(doctype)}_tally",
		"xlsx",
		preview.get_workbook(doctype, _as_name_list(names)),
	)


@frappe.whitelist()
def tally_download_xml(doctype, names):
	from frappe.desk.utils import provide_binary_file

	preview.check_supported(doctype)
	frappe.has_permission(doctype, "read", throw=True)
	provide_binary_file(
		f"{frappe.scrub(doctype)}_tally",
		"xml",
		preview.get_xml_bytes(doctype, _as_name_list(names)),
	)
