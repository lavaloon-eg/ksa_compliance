frappe.ui.form.on("ZATCA Business Settings", {
  setup: function (frm) {
    add_other_ids_if_new(frm);
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

function add_other_ids_if_new(frm) {
  // TODO: update permissions for child doctype
  if (frm.is_new()) {
    var seller_id_list = [];
    seller_id_list.push(
      {
        type_name: "Commercial Registration Number",
        type_code: "CRN",
      },
      {
        type_name: "MOMRAH License",
        type_code: "MOM",
      },
      {
        type_name: "MHRSD License",
        type_code: "MLS",
      },
      {
        type_name: "700 Number",
        type_code: "700",
      },
      {
        type_name: "MISA License",
        type_code: "SAG",
      },
      {
        type_name: "Other OD",
        type_code: "OTH",
      }
    );
    frm.set_value("other_ids", seller_id_list);
  }
}
