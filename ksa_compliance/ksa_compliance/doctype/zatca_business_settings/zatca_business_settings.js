frappe.ui.form.on("ZATCA Business Settings", {
    setup: function (frm) {
        frm.set_df_property('other_ids', 'cannot_delete_rows', 1);
        frm.set_df_property('other_ids', 'cannot_add_rows', 1);
    },
    refresh: function (frm) {
        add_other_ids_if_new(frm);
        filter_company_address(frm);
        frm.add_custom_button(__("Submit Feedback"), () => {
            show_feedback_dialog(__("Submit Feedback"));
        });
    },
    after_insert: function (frm) {
        show_feedback_dialog(__("How was your experience configuring these settings?"));
    },
    company: function (frm) {
        filter_company_address(frm);
    },
    setup_zatca_cli: async function (frm) {
        let response = await frappe.call({
            method: "ksa_compliance.zatca_cli.setup",
            args: {
                override_cli_download_url: frm.doc.override_cli_download_url || '',
                override_jre_download_url: frm.doc.override_jre_download_url || '',
            },
        })
        if (response.message) {
            frm.set_value('zatca_cli_path', response.message.cli_path);
            frm.set_value('java_home', response.message.jre_path);
            frm.save();
        }
    },
    check_zatca_cli: function (frm) {
        frappe.call({
            freeze: true,
            freeze_message: __('Please wait...'),
            method: "ksa_compliance.zatca_cli.check_setup",
            args: {
                zatca_cli_path: frm.doc.zatca_cli_path || '',
                java_home: frm.doc.java_home || '',
            }
        })
    },
    block_invoice_on_invalid_xml: async function (frm) {
        if (frm.doc.block_invoice_on_invalid_xml) {
            try {
                let result = await frappe.call({
                    freeze: true,
                    freeze_message: __('Please wait. Checking ZATCA CLI version...'),
                    method: "ksa_compliance.zatca_cli.check_validation_details_support",
                    args: {
                        zatca_cli_path: frm.doc.zatca_cli_path || '',
                        java_home: frm.doc.java_home || '',
                    }
                });

                if (!result.message.is_supported) {
                    frappe.throw(result.message.error);
                }
            } catch (e) {
                frm.set_value('block_invoice_on_invalid_xml', 0);
                throw e;
            }
        }
    },
    create_csr: function (frm) {
        frappe.prompt(__('OTP'), async ({ value }) => {
            await frappe.call({
                freeze: true,
                freeze_message: __('Please wait...'),
                method: "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.onboard",
                args: {
                    business_settings_id: frm.doc.name,
                    otp: value
                },
            });
            frm.reload_doc();
        });
    },
    perform_compliance_checks: function (frm) {
        if (!frm.doc.compliance_request_id) {
            frappe.throw(__('Please Onboard first to generate a compliance request ID'))
            return;
        }


        let simplified = frm.doc.type_of_business_transactions === 'Let the system decide (both)' ||
            frm.doc.type_of_business_transactions === 'Simplified Tax Invoices';
        let standard = frm.doc.type_of_business_transactions === 'Let the system decide (both)' ||
            frm.doc.type_of_business_transactions === 'Standard Tax Invoices';
        let customer_fields = [];
        if (simplified)
            customer_fields.push({
                label: 'Simplified Tax Customer',
                fieldname: 'simplified_customer_id',
                fieldtype: 'Link',
                options: 'Customer',
                reqd: 1,
                get_query: function () {
                    return {
                        query: "ksa_compliance.compliance_checks.customer_query",
                        filters: { "standard": false },
                    }
                }
            });

        if (standard) {
            customer_fields.push({
                label: 'Standard Tax Customer',
                fieldname: 'standard_customer_id',
                fieldtype: 'Link',
                options: 'Customer',
                reqd: 1,
                get_query: function () {
                    return {
                        query: "ksa_compliance.compliance_checks.customer_query",
                        filters: { "standard": true },
                    }
                }
            });
        }

        let fields = customer_fields.concat([
            {
                label: 'Item',
                fieldname: 'item_id',
                fieldtype: 'Link',
                options: 'Item',
                reqd: 1,
            },
            {
                label: 'Tax Category',
                fieldname: 'tax_category_id',
                fieldtype: 'Link',
                options: 'Tax Category',
                reqd: 1,
            },
        ])

        frappe.prompt(fields, values => {
            frappe.call({
                freeze: true,
                freeze_message: 'Please wait...',
                method: "ksa_compliance.compliance_checks.perform_compliance_checks",
                args: {
                    business_settings_id: frm.doc.name,
                    simplified_customer_id: values.simplified_customer_id || '',
                    standard_customer_id: values.standard_customer_id || '',
                    item_id: values.item_id,
                    tax_category_id: values.tax_category_id,
                },
            });
        });
    },
    get_production_csid: function (frm) {
        if (!frm.doc.compliance_request_id) {
            frappe.throw(__('Please Onboard first to generate a compliance request ID'))
            return;
        }

        frappe.prompt(__('OTP'), ({ value }) => {
            frappe.call({
                freeze: true,
                freeze_message: 'Please wait...',
                method: "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.get_production_csid",
                args: {
                    business_settings_id: frm.doc.name,
                    otp: value
                },
            });
        });
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
    if (frm.doc.other_ids.length === 0) {
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
                type_name: "Other ID",
                type_code: "OTH",
            }
        );
        frm.set_value("other_ids", seller_id_list);
    }
}

async function show_feedback_dialog(title) {
    const uploaded_files = [];

    const settings = await frappe.call({
        method: 'ksa_compliance.customer_feedback.get_feedback_settings',
        type: 'GET'
    });

    const CONFIG = {
        CONTACT_CENTER_PAGE: settings.message.CONTACT_CENTER_PAGE,
        MAX_DESCRIPTION_LENGTH: settings.message.MAX_DESCRIPTION_LENGTH,
        MAX_FILES: settings.message.MAX_FILES,
        MAX_FILE_SIZE_MB: settings.message.MAX_FILE_SIZE_MB,
        ALLOWED_FILE_TYPES: settings.message.ALLOWED_FILE_TYPES
    };

    const email_accounts = await frappe.db.get_list('Email Account', {
        fields: ['email_id'],
        filters: { default_outgoing: 1 },
        limit: 1
    });

    const default_email_account = email_accounts.length > 0 ? email_accounts[0].email_id : '';

    if (!default_email_account) {
        frappe.msgprint(__("Please create a default outgoing email account"));
        frappe.msgprint(__("Our Contact Center is here to help you with any questions or issues you may have. <a href='{0}' target='_blank'>Contact Us</a>", [CONFIG.CONTACT_CENTER_PAGE]));
        return;
    }

    const dialog = new frappe.ui.Dialog({
        title: title,
        fields: [
            {
                label: __("Subject"),
                fieldname: "subject",
                fieldtype: "Select",
                reqd: 1,
                options: [
                    __("Bug Report"),
                    __("Feature Request"),
                    __("General Feedback"),
                    __("Compliance Issue"),
                    __("Other")
                ]
            },
            {
                label: __("Description"),
                fieldname: "description",
                fieldtype: "Text",
                reqd: 1
            },
            {
                fieldtype: "HTML",
                fieldname: "upload_area",
                label: __("Attachments")
            },
            {
                fieldtype: "Button",
                fieldname: "upload_button",
                label: __("Upload Files"),
                click() {
                    new frappe.ui.FileUploader({
                        allow_multiple: true,
                        make_attachments_public: true,
                        upload_notes: __("Upload up to {0} files (PDF, PNG, JPEG, DOCX), max {1}MB each",
                            [CONFIG.MAX_FILES, CONFIG.MAX_FILE_SIZE_MB]),
                        restrictions: {
                            allowed_file_types: CONFIG.ALLOWED_FILE_TYPES,
                            max_file_size: CONFIG.MAX_FILE_SIZE_MB * 1024 * 1024,
                            max_number_of_files: CONFIG.MAX_FILES,
                        },
                        on_success(file) {
                            uploaded_files.push(file.file_url);
                            frappe.show_alert({
                                message: __("File uploaded: {0}", [file.file_name]),
                                indicator: 'green'
                            });
                        }
                    });
                }
            }
        ],
        size: 'large',
        primary_action_label: __('Submit'),
        async primary_action(values) {
            if (values.description.length > CONFIG.MAX_DESCRIPTION_LENGTH) {
                frappe.throw(__("Description must be less than {0} characters", [CONFIG.MAX_DESCRIPTION_LENGTH]));
                return;
            }

            dialog.set_primary_action(__('Submitting...'), null);
            values.attachments = uploaded_files;

            try {
                const response = await frappe.call({
                    method: 'ksa_compliance.customer_feedback.send_feedback_email',
                    args: {
                        sender_email: default_email_account,
                        subject: values.subject,
                        description: values.description,
                        attachments: values.attachments
                    }
                });

                if (response.success) {
                    frappe.show_alert({
                        message: response.message,
                        indicator: 'green'
                    });
                    dialog.hide();
                } else {
                    throw new Error(response.message);
                }
            } catch (error) {
                frappe.show_alert({
                    message: __("An error occurred while submitting your feedback: {0}", [error.message]),
                    indicator: 'red'
                });
                console.error(error);
            } finally {
                dialog.set_primary_action(__('Submit'), () => dialog.primary_action(values));
            }
        },
        secondary_action_label: __("Cancel"),
        secondary_action() {
            dialog.hide();
        }
    });

    dialog.show();
}
