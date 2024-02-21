frappe.ui.form.on("Customer", {
  setup: function(frm){
    frm.set_df_property('custom_additional_ids', 'cannot_delete_rows', 1);
    frm.set_df_property('custom_additional_ids', 'cannot_add_rows', 1);
  },
  refresh: function (frm) {
    add_other_ids_if_new(frm);
  },
});

function add_other_ids_if_new(frm) {
  // TODO: update permissions for child doctype
  if (frm.is_new()) {
    var buyer_id_list = [];
    buyer_id_list.push(
      {
        type_name: "Tax Identification Number",
        type_code: "TIN",
      },
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
        type_name: "National ID",
        type_code: "NAT",
      },
      {
        type_name: "GCC ID",
        type_code: "GCC",
      },
      {
        type_name: "Iqama",
        type_code: "IQA",
      },
      {
        type_name: "Passport ID",
        type_code: "PAS",
      },
      {
        type_name: "Other OD",
        type_code: "OTH",
      }
    );
    frm.set_value("custom_additional_ids", buyer_id_list);
  }
}
