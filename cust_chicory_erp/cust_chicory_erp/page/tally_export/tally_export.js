frappe.pages["tally-export"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Export to Tally"),
		single_column: true,
	});

	let current_names = [];
	let current_xml = "";
	let datatable = null;

	const $summary = $('<div class="report-summary mb-3"></div>').hide().appendTo(page.main);
	const $content = $('<div class="frappe-card p-3"></div>').appendTo(page.main);

	let refresh_timer = null;
	let request_seq = 0;
	const schedule_refresh = () => {
		clearTimeout(refresh_timer);
		refresh_timer = setTimeout(load_preview, 100);
	};

	const doctype_field = page.add_field({
		fieldname: "doctype",
		label: __("Document"),
		fieldtype: "Select",
		options: "Purchase Receipt\nSales Invoice\nPayment Entry",
		default: "Purchase Receipt",
		change: schedule_refresh,
	});
	const from_field = page.add_field({
		fieldname: "from_date",
		label: __("From"),
		fieldtype: "Date",
		default: frappe.datetime.month_start(),
		change: schedule_refresh,
	});
	const to_field = page.add_field({
		fieldname: "to_date",
		label: __("To"),
		fieldtype: "Date",
		default: frappe.datetime.get_today(),
		change: schedule_refresh,
	});

	function download(format) {
		if (!current_names.length) return;
		const endpoint =
			format === "xml"
				? "cust_chicory_erp.api.tally_download_xml"
				: "cust_chicory_erp.api.tally_download_excel";
		open_url_post(`/api/method/${endpoint}`, {
			doctype: doctype_field.get_value(),
			names: JSON.stringify(current_names),
		});
	}

	page.set_primary_action(__("Download Tally XML"), () => download("xml"));
	const $download_excel_btn = page.add_inner_button(__("Download Excel"), () => download("excel"));
	const $copy_btn = page.add_inner_button(__("Copy XML"), () => {
		if (!current_xml) return;
		frappe.utils.copy_to_clipboard(current_xml, __("Tally XML copied"));
	});
	page.add_inner_button(__("Refresh"), () => load_preview());

	function render_summary(rows, company) {
		$summary.empty();
		const total = rows.reduce((acc, r) => acc + flt(r.amount), 0);
		const currency = frappe.defaults.get_default("currency") || "INR";
		const items = [
			{ value: rows.length, label: __("Vouchers"), datatype: "Int", indicator: "Blue" },
			{
				value: total,
				label: __("Total Amount"),
				datatype: "Currency",
				currency,
				indicator: "Green",
			},
		];
		if (company) {
			items.push({ value: company, label: __("Tally Company"), datatype: "Data", indicator: "Blue" });
		}
		items.forEach((item) => {
			frappe.utils.build_summary_item(item).appendTo($summary);
		});
		$summary.show();
	}

	function set_export_actions_disabled(disabled) {
		page.btn_primary?.prop("disabled", disabled);
		$download_excel_btn.prop("disabled", disabled);
		$copy_btn.prop("disabled", disabled);
	}

	function render_empty(dt, from_date, to_date) {
		current_names = [];
		current_xml = "";
		set_export_actions_disabled(true);
		$summary.hide().empty();
		if (datatable) {
			datatable.destroy();
			datatable = null;
		}
		$content.empty().append(
			frappe.ui.empty_state({
				icon: "file",
				title: __("No submitted documents"),
				description: __("No submitted {0} records found for {1} to {2}.", [
					__(dt),
					frappe.datetime.str_to_user(from_date || "") || "—",
					frappe.datetime.str_to_user(to_date || "") || "—",
				]),
			}),
		);
	}

	function render_preview(data) {
		current_xml = data.xml || "";
		set_export_actions_disabled(!current_names.length);
		render_summary(data.rows || [], data.company);

		if (datatable) {
			datatable.destroy();
			datatable = null;
		}
		$content.empty();
		const $table = $('<div class="mb-3"></div>').appendTo($content);
		const columns = [
			{
				id: "date",
				name: __("Date"),
				width: 110,
				format: (val) => frappe.datetime.str_to_user(val),
			},
			{ id: "type", name: __("Voucher Type"), width: 120 },
			{ id: "number", name: __("No"), width: 140 },
			{ id: "party", name: __("Party"), width: 200 },
			{ id: "debit", name: __("Debit Ledger"), width: 180 },
			{ id: "credit", name: __("Credit Ledger"), width: 180 },
			{
				id: "amount",
				name: __("Amount"),
				align: "right",
				width: 130,
				format: (val) => format_currency(val, frappe.defaults.get_default("currency") || "INR"),
			},
			{ id: "narration", name: __("Narration"), width: 220 },
		];
		datatable = new frappe.DataTable(
			$table[0],
			{
				columns,
				data: data.rows || [],
				inlineFilters: true,
				cellHeight: 33,
				language: frappe.boot.lang,
				translations: frappe.utils.datatable?.get_translations?.() || {},
			},
		);

		const esc = frappe.utils.escape_html;
		$content.append(
			`<details class="mt-3">
				<summary class="text-muted" style="cursor:pointer">${__("Tally XML")}</summary>
				<pre class="p-3 mt-2 bg-light border rounded" style="max-height:320px;overflow:auto">${esc(current_xml)}</pre>
			</details>`,
		);
	}

	function load_preview() {
		clearTimeout(refresh_timer);
		const dt = doctype_field.get_value();
		const from_date = from_field.get_value();
		const to_date = to_field.get_value();
		if (!dt) return;

		const seq = ++request_seq;
		frappe.call({
			method: "cust_chicory_erp.api.tally_list_documents",
			args: { doctype: dt, from_date, to_date },
			callback: (r) => {
				if (seq !== request_seq) return;
				const names = r.message || [];
				if (!names.length) {
					render_empty(dt, from_date, to_date);
					return;
				}
				current_names = names;
				frappe.call({
					method: "cust_chicory_erp.api.tally_preview",
					args: { doctype: dt, names: JSON.stringify(names) },
					callback: (r2) => {
						if (seq !== request_seq || !r2.message) return;
						render_preview(r2.message);
					},
				});
			},
		});
	}

	wrapper._reload_tally_preview = schedule_refresh;
	schedule_refresh();
};

frappe.pages["tally-export"].on_page_show = function (wrapper) {
	wrapper._reload_tally_preview?.();
};
