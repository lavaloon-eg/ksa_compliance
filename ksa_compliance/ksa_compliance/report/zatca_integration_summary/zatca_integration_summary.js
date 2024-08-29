// Copyright (c) 2024, LavaLoon and contributors
// For license information, please see license.txt

frappe.query_reports["Zatca Integration Summary"] = {
	"onload": function (report) {
		const summary_elm = document.getElementById('message-summary')
		if (!summary_elm) {
			const page_container = report.$page[0];
			const filters_section = page_container.querySelector(".page-form");
			const message = "A quick overview of ZATCA integration status totals and financial information is needed to monitor and reconcile transactions, ensuring all invoices are tracked and accounted for.";

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
	},
};
