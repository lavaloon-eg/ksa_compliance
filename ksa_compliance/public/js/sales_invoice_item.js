frappe.ui.form.on("Sales Invoice Item", {
  rate: async function (frm, cdt, cdn) {
    var item = locals[cdt][cdn];
    var tax_rate = frm.doc.taxes[0].rate;
    if (item.rate && tax_rate) {
      item.custom_tax_total = (tax_rate / 100) * item.rate;
      item.custom_total_after_tax = item.rate + item.custom_tax_total;
    }
  },
});
