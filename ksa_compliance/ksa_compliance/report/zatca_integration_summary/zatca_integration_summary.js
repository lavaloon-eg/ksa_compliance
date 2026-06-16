// Copyright (c) 2024, LavaLoon and contributors
// For license information, please see license.txt

frappe.query_reports['Zatca Integration Summary'] = {
	filters: [
		{
			fieldname: 'from_date_filter',
			label: __('From Date'),
			fieldtype: 'Date',
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: 'to_date_filter',
			label: __('To Date'),
			fieldtype: 'Date',
			default: frappe.datetime.now_date(),
			reqd: 1,
		},
		{
			fieldname: 'company_filter',
			label: __('Company'),
			fieldtype: 'Link',
			options: 'Company',
			default: frappe.defaults.get_user_default('Company'),
			reqd: 1,
		},
		{
			fieldname: 'invoice_doctype',
			label: __('Document Type'),
			fieldtype: 'Select',
			options: 'All\nSales Invoice\nPOS Invoice\nPayment Entry',
			default: 'All',
			reqd: 1,
		},
	],

	onload: function (report) {
		const summary_elm = document.getElementById('message-summary');
		const page_container = report.$page && report.$page[0];
		if (!page_container) {
			return;
		}

		const filters_section = page_container.querySelector('.page-form');
		if (!filters_section) {
			return;
		}

		if (!summary_elm) {
			const message =
				'A quick overview of ZATCA integration status totals and financial information is needed to monitor and reconcile transactions, ensuring all invoices are tracked and accounted for.';

			const message_summary_elm = document.createElement('div');
			message_summary_elm.classList.add('my-3', 'mx-auto');
			message_summary_elm.id = 'message-summary';
			message_summary_elm.style.width = '95%';

			const message_title = document.createElement('h5');
			message_title.innerText = 'Summary';
			const message_content = document.createElement('span');
			message_content.innerText = message;

			message_summary_elm.append(document.createElement('hr'), message_title, message_content);
			filters_section.appendChild(message_summary_elm);
		}

		report.page.add_inner_button(__('Integration Details'), function () {
			const v = report.get_values() || {};
			frappe.set_route('query-report', 'Zatca Integration Details', {
				from_date_filter: v.from_date_filter,
				to_date_filter: v.to_date_filter,
				company_filter: v.company_filter,
				invoice_doctype: v.invoice_doctype || 'All',
			});
		});
	},
};
