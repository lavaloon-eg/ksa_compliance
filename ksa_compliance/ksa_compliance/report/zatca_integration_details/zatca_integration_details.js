// Copyright (c) 2024, LavaLoon and contributors
// For license information, please see license.txt

frappe.query_reports['Zatca Integration Details'] = {
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
			fieldname: 'branch_filter',
			label: __('Branch'),
			fieldtype: 'Link',
			options: 'Branch',
		},
		{
			fieldname: 'integration_status_filter',
			label: __('Integration Status'),
			fieldtype: 'Select',
			options:
				'All\nReady For Batch\nResend\nAccepted with warnings\nAccepted\nRejected\nClearance switched off\nNot Sended\nNo Sales Invoice',
			default: 'All',
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
		{
			fieldname: 'validated_filter',
			label: __('Date Validation'),
			fieldtype: 'Select',
			options: 'All\nValidated\nNot Validated',
			default: 'All',
			reqd: 1,
		},
	],

	onload: function (report) {
		const summary_elm = document.getElementById('message-summary');
		if (summary_elm) {
			return;
		}

		const page_container = report.$page && report.$page[0];
		if (!page_container) {
			return;
		}

		const filters_section = page_container.querySelector('.page-form');
		if (!filters_section) {
			return;
		}

		const message =
			'This report will display the ZATCA status for each transaction and provide detailed invoice amount information, to reconcile transactions between the system and Fatoorah platform.\n' +
			'It is not recommended to run or generate this report with the "From Date" and "To Date" filters set for a period exceeding 31 days.';

		const message_summary_elm = document.createElement('div');
		message_summary_elm.classList.add('my-3', 'mx-auto');
		message_summary_elm.id = 'message-summary';
		message_summary_elm.style.width = '95%';

		const message_title = document.createElement('h5');
		message_title.innerText = 'Summary';
		const message_content = document.createElement('span');
		message_content.innerText = message;

		message_summary_elm.append(
			document.createElement('hr'),
			message_title,
			message_content,
		);
		filters_section.appendChild(message_summary_elm);
	},

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!value || column.fieldname !== 'integration_status') {
			return value;
		}

		const status = String(value).toLowerCase();
		if (status === 'accepted') {
			return `<b style="color:green">${value}</b>`;
		}
		if (status === 'rejected') {
			return `<b style="color:red">${value}</b>`;
		}
		if (status === 'resend') {
			return `<b style="color:blue">${value}</b>`;
		}
		if (status === 'accepted with warnings') {
			return `<b style="color:orange">${value}</b>`;
		}
		return value;
	},
};
