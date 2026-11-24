import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

CUSTOM_FIELDS = {
	"Purchase Receipt": [
		{
			"fieldname": "weighbridge_section",
			"label": "Weighbridge & Inward Details",
			"fieldtype": "Section Break",
			"insert_after": "supplier_delivery_note",
		},
		{
			"fieldname": "weighbridge_slip_no",
			"label": "Weighbridge Slip No",
			"fieldtype": "Data",
			"insert_after": "weighbridge_section",
		},
		{
			"fieldname": "vehicle_no",
			"label": "Vehicle No",
			"fieldtype": "Data",
			"insert_after": "weighbridge_slip_no",
		},
		{
			"fieldname": "gross_weight",
			"label": "Gross Weight (Kg)",
			"fieldtype": "Float",
			"insert_after": "vehicle_no",
		},
		{
			"fieldname": "tare_weight",
			"label": "Tare Weight (Kg)",
			"fieldtype": "Float",
			"insert_after": "gross_weight",
		},
		{
			"fieldname": "net_weight",
			"label": "Net Weight (Kg)",
			"fieldtype": "Float",
			"read_only": 1,
			"insert_after": "tare_weight",
		},
		{
			"fieldname": "col_break_wb",
			"fieldtype": "Column Break",
			"insert_after": "net_weight",
		},
		{
			"fieldname": "dirt_moisture_deduction_pct",
			"label": "Dirt/Moisture Deduction %",
			"fieldtype": "Percent",
			"insert_after": "col_break_wb",
		},
		{
			"fieldname": "net_payable_weight",
			"label": "Net Payable Weight (Kg)",
			"fieldtype": "Float",
			"read_only": 1,
			"insert_after": "dirt_moisture_deduction_pct",
		},
		{
			"fieldname": "freight_paid_by",
			"label": "Freight Paid By",
			"fieldtype": "Select",
			"options": "Company (Landed Cost)\nFarmer (Deduction from Payout)",
			"default": "Company (Landed Cost)",
			"insert_after": "net_payable_weight",
		},
	],
	"Job Card": [
		{
			"fieldname": "chicory_process_section",
			"label": "Chicory Process & Loss Logging",
			"fieldtype": "Section Break",
			"insert_after": "transferred_qty",
		},
		{
			"fieldname": "stage_input_qty",
			"label": "Stage Input (Kg)",
			"fieldtype": "Float",
			"insert_after": "chicory_process_section",
		},
		{
			"fieldname": "stage_output_qty",
			"label": "Stage Output (Kg)",
			"fieldtype": "Float",
			"insert_after": "stage_input_qty",
		},
		{
			"fieldname": "stage_process_loss_qty",
			"label": "Measured Process Loss (Kg)",
			"fieldtype": "Float",
			"read_only": 1,
			"insert_after": "stage_output_qty",
		},
		{
			"fieldname": "col_break_jc",
			"fieldtype": "Column Break",
			"insert_after": "stage_process_loss_qty",
		},
		{
			"fieldname": "process_loss_reason",
			"label": "Process Loss Reason",
			"fieldtype": "Select",
			"options": "\nWash Dirt & Debris\nMoisture Evaporation (Drying)\nRoasting Process Loss\nGrinding Dust / Sieve Reject\nPackaging Damage",
			"insert_after": "col_break_jc",
		},
		{
			"fieldname": "moisture_pct",
			"label": "Moisture Content %",
			"fieldtype": "Percent",
			"insert_after": "process_loss_reason",
		},
		{
			"fieldname": "roast_temp_celsius",
			"label": "Roasting Temp (°C)",
			"fieldtype": "Float",
			"insert_after": "moisture_pct",
		},
		{
			"fieldname": "roast_time_mins",
			"label": "Roasting Time (Minutes)",
			"fieldtype": "Int",
			"insert_after": "roast_temp_celsius",
		},
	],
	"Batch": [
		{
			"fieldname": "quality_status",
			"label": "Quality Status",
			"fieldtype": "Select",
			"options": "Draft\nPending Inspection\nPassed\nOn Hold\nRejected",
			"default": "Draft",
			"insert_after": "disabled",
		},
		{
			"fieldname": "supplier_lot_no",
			"label": "Supplier Lot No",
			"fieldtype": "Data",
			"insert_after": "supplier",
		},
	],
}


def setup_custom_fields():
	create_custom_fields(CUSTOM_FIELDS, update=True)
