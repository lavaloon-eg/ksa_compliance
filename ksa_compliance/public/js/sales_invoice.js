frappe.ui.form.on("Sales Invoice Item", {
  on_update: function (frm, cdt, cdn) {
    console.log(frm.doc.net_rate, frm.doc.net_amount);
    frappe.model.set_value(cdt, cdn, "custom_tax_total", frm.doc.net_rate);
  },
  items_add: function (frm, cdt, cdn) {
    console.log(frm.doc.net_rate, frm.doc.net_amount);
    frappe.model.set_value(cdt, cdn, "custom_tax_total", frm.doc.net_rate);
  },
  onload: function (frm, cdt, cdn) {
    console.log(frm.doc.net_rate, frm.doc.net_amount);
    frappe.model.set_value(cdt, cdn, "custom_tax_total", frm.doc.net_rate);
  },
});
