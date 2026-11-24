from xml.etree import ElementTree

from frappe.utils import flt, getdate


def build_envelope(company, vouchers):
	"""Tally import envelope (file import). Debit amounts are negative with ISDEEMEDPOSITIVE Yes."""
	envelope = ElementTree.Element("ENVELOPE")
	header = ElementTree.SubElement(envelope, "HEADER")
	ElementTree.SubElement(header, "TALLYREQUEST").text = "Import Data"
	import_data = ElementTree.SubElement(ElementTree.SubElement(envelope, "BODY"), "IMPORTDATA")
	description = ElementTree.SubElement(import_data, "REQUESTDESC")
	ElementTree.SubElement(description, "REPORTNAME").text = "Vouchers"
	variables = ElementTree.SubElement(description, "STATICVARIABLES")
	ElementTree.SubElement(variables, "SVCURRENTCOMPANY").text = company
	data = ElementTree.SubElement(import_data, "REQUESTDATA")
	for voucher in vouchers:
		_add_voucher(ElementTree.SubElement(data, "TALLYMESSAGE"), voucher)
	ElementTree.indent(envelope)
	return ElementTree.tostring(envelope, encoding="unicode")


def _add_voucher(message, voucher):
	node = ElementTree.SubElement(message, "VOUCHER", VCHTYPE=voucher["type"], ACTION="Create")
	ElementTree.SubElement(node, "DATE").text = getdate(voucher["date"]).strftime("%Y%m%d")
	ElementTree.SubElement(node, "VOUCHERTYPENAME").text = voucher["type"]
	ElementTree.SubElement(node, "VOUCHERNUMBER").text = str(voucher["number"])
	ElementTree.SubElement(node, "PARTYLEDGERNAME").text = str(voucher["party"])
	ElementTree.SubElement(node, "NARRATION").text = voucher.get("narration") or ""
	for entry in voucher["entries"]:
		line = ElementTree.SubElement(node, "ALLLEDGERENTRIES.LIST")
		ElementTree.SubElement(line, "LEDGERNAME").text = str(entry["ledger"])
		ElementTree.SubElement(line, "ISDEEMEDPOSITIVE").text = "Yes" if entry["is_debit"] else "No"
		amount = flt(entry["amount"], 2)
		ElementTree.SubElement(line, "AMOUNT").text = f"{-amount if entry['is_debit'] else amount:.2f}"
