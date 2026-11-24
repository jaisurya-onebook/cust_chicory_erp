frappe.query_reports["Chicory Stage Yield and Loss"] = {
	filters: [
		{
			fieldname: "work_order",
			label: __("Work Order"),
			fieldtype: "Link",
			options: "Work Order",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
		},
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "loss_pct" && data && data.loss_pct > 15) {
			value = `<span style="font-weight: bold; color: #dc2626;">${value}</span>`;
		} else if (column.fieldname === "loss_pct" && data && data.loss_pct > 5) {
			value = `<span style="font-weight: bold; color: #d97706;">${value}</span>`;
		}
		return value;
	},
};
