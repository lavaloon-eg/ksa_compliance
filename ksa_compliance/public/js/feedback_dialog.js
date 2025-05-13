frappe.provide('ksa_compliance.feedback_dialog');

ksa_compliance.feedback_dialog = {
    show_feedback_dialog: async function (title, is_after_save = false, document_name = '') {
        const uploaded_files = [];
        const feedback_config = await this.get_feedback_configuration();
        const default_email_account = await this.get_default_email_account();

        if (!default_email_account) {
            this.show_email_account_error(feedback_config.LAVALOON_CONTACT_PAGE);
            return;
        }

        const dialog = this.create_feedback_dialog(title, feedback_config, uploaded_files, default_email_account, is_after_save, document_name);
        dialog.show();
    },

    should_skip_feedback_dialog: function (document_name) {
        try {
            const ignored_documents = localStorage.getItem('ignore_feedback_popup_setting_ids');
            if (!ignored_documents) return false;

            return ignored_documents.split(',').includes(document_name);
        } catch (error) {
            console.error('Error checking ignored documents:', error);
            return false;
        }
    },

    add_to_ignored_documents: function (document_name) {
        try {
            const ignored_documents = localStorage.getItem('ignore_feedback_popup_setting_ids');
            let ignored_documents_list = [];

            if (ignored_documents) {
                ignored_documents_list = ignored_documents.split(',');
            }

            if (!ignored_documents_list.includes(document_name)) {
                ignored_documents_list.push(document_name);
                localStorage.setItem('ignore_feedback_popup_setting_ids', ignored_documents_list.join(','));
                frappe.show_alert({
                    message: __('Feedback dialog will not be shown again for this document.'),
                    indicator: 'green'
                });
            }
        } catch (error) {
            console.error('Error adding document to ignored list:', error);
            frappe.show_alert({
                message: __('Failed to save preference. Please try again.'),
                indicator: 'red'
            });
        }
    },

    get_feedback_configuration: async function () {
        const response = await frappe.call({
            method: 'ksa_compliance.customer_feedback.get_feedback_settings',
            type: 'GET'
        });

        return response.message
    },

    get_default_email_account: async function () {
        const email_accounts = await frappe.db.get_list('Email Account', {
            fields: ['email_id'],
            filters: { default_outgoing: 1 },
            limit: 1
        });

        return email_accounts.length > 0 ? email_accounts[0].email_id : '';
    },

    show_email_account_error: function (contact_center_page) {
        frappe.msgprint(__("Please create a default outgoing email account"));
        frappe.msgprint(__("Our Contact Center is here to help you with any questions or issues you may have."));
        frappe.msgprint(__("<a href='{0}' target='_blank'>Contact Us</a>", [contact_center_page]));
    },

    create_feedback_dialog: function (title, config, uploaded_files, default_email_account, is_after_save, document_name) {
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
                    reqd: 1,
                    description: __("Maximum {0} characters", [config.MAX_DESCRIPTION_LENGTH])
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
                        ksa_compliance.feedback_dialog.create_file_uploader(config, uploaded_files);
                    }
                }
            ],
            size: 'large',
            primary_action_label: __('Submit'),
            async primary_action(values) {
                try {
                    if (!ksa_compliance.feedback_dialog.validate_feedback_submission(values, config)) {
                        return;
                    }

                    dialog.set_primary_action(__('Submitting...'), null);
                    await ksa_compliance.feedback_dialog.submit_feedback(values, uploaded_files, default_email_account, dialog);
                } catch (error) {
                    console.error('Error submitting feedback:', error);
                    frappe.show_alert({
                        message: __('Failed to submit feedback. Please try again.'),
                        indicator: 'red'
                    });
                    dialog.set_primary_action(__('Submit'), () => dialog.primary_action(values));
                }
            },
            secondary_action_label: is_after_save ? __("Don't Show Again") : __("Cancel"),
            secondary_action: () => {
                if (is_after_save) {
                    ksa_compliance.feedback_dialog.add_to_ignored_documents(document_name);
                }
                dialog.hide();
            }
        });

        return dialog;
    },

    validate_feedback_submission: function (values, config) {
        if (!values.subject) {
            frappe.throw(__("Please select a subject"));
            return false;
        }

        if (!values.description) {
            frappe.throw(__("Please provide a description"));
            return false;
        }

        if (values.description.length > config.MAX_DESCRIPTION_LENGTH) {
            frappe.throw(__("Description must be less than {0} characters", [config.MAX_DESCRIPTION_LENGTH]));
            return false;
        }

        return true;
    },

    create_file_uploader: function (config, uploaded_files) {
        new frappe.ui.FileUploader({
            allow_multiple: true,
            make_attachments_public: true,
            upload_notes: __("Upload up to {0} files (PDF, PNG, JPEG, DOCX), max {1}MB each",
                [config.MAX_NUMBER_OF_FILES, config.MAX_FILE_SIZE_MB]),
            restrictions: {
                allowed_file_types: config.ALLOWED_FILE_TYPES,
                max_file_size: config.MAX_FILE_SIZE_MB * 1024 * 1024,
                max_number_of_files: config.MAX_NUMBER_OF_FILES,
            },
            on_success(file) {
                uploaded_files.push(file.file_url);
                frappe.show_alert({
                    message: __("File uploaded: {0}", [file.file_name]),
                    indicator: 'green'
                });
            },
            on_error(error) {
                frappe.show_alert({
                    message: __("Failed to upload file: {0}", [error.message]),
                    indicator: 'red'
                });
            }
        });
    },

    submit_feedback: async function (values, uploaded_files, default_email_account, dialog) {
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
    }
}; 