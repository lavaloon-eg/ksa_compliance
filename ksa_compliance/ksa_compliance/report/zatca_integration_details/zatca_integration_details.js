// Copyright (c) 2024, LavaLoon and contributors
// For license information, please see license.txt

frappe.query_reports["Zatca Integration Details"] = {
	"onload": function (report) {
    const summary_elm = document.getElementById('message-summary')
    if (!summary_elm) {
      const page_container = report.$page[0];
      const filters_section = page_container.querySelector(".page-form");
      const message = "This report will display the ZATCA status for each transaction and provide detailed invoice amount information, to reconcile transactions between the system and Fatoorah platform.\n" +
          "It is not recommended to run or generate this report with the “From Date” and “To Date” filters set for a period exceeding 31 days.";

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
    formatter:function (value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);
    if (column.fieldname == 'integration_status') {
       if (value.toLowerCase() =='accepted') {
            value = `<b style="color:green">${value}</b>`
       } else if (value.toLowerCase() == 'rejected') {
            value = `<b style="color:red">${value}</b>`
       } else if (value.toLowerCase() == 'resend') {
            value = `<b style="color:blue">${value}</b>`
       } else if (value.toLowerCase() == 'accepted with warnings') {
            value = `<b style="color:orange">${value}</b>`
       }
    }
    return value;
}
};
