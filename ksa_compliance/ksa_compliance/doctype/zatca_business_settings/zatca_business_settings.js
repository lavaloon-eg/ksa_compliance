frappe.ui.form.on("ZATCA Business Settings", {
  setup: function (frm) {
    filter_company_address(frm);
  },
  company: function (frm) {
    filter_company_address(frm);
  },
});

function filter_company_address(frm) {
  frappe.call({
    method:
      "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.fetch_company_addresses",
    args: {
      company_name: frm.doc.company,
    },
    callback: function (r) {
      if (r.message) {
        frm.set_query("company_address", function () {
          return {
            filters: {
              name: ["in", r.message],
            },
          };
        });
      }
    },
  });
}
