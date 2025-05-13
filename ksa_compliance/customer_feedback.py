import json
from typing import cast
import frappe
from frappe import _
import os
from frappe.core.doctype.file.file import File


@frappe.whitelist(methods=["GET"])
def get_feedback_settings():
    """Get feedback settings from ZATCA Feedback Settings"""
    settings_dict = {
        "RECIPIENT_EMAILS": ["ksa_compliance@lavaloon.com"],
        "LAVALOON_CONTACT_PAGE": "https://lavaloon.com/contact-us",
        "MAX_FILE_SIZE_MB": 5,
        "MAX_NUMBER_OF_FILES": 3,
        "ALLOWED_FILE_TYPES": ['.pdf', '.png', '.jpeg', '.docx'],
        "MAX_DESCRIPTION_LENGTH": 500,
    }

    return settings_dict

@frappe.whitelist()
def send_feedback_email(sender_email, subject, description, attachments=None):
    """Send feedback email using the default email account"""
    try:
        config = get_feedback_settings()

        email_content = f"""
        <h3>Feedback Details</h3>
        <p>{description}</p>
        """

        if attachments:
            attachments = json.loads(attachments)
            email_content += "<h4>Attachments:</h4><ul>"
            for attachment in attachments:
                file_doc = cast(File, frappe.get_doc("File", {"file_url": attachment}))
                file_extension = os.path.splitext(file_doc.file_name)[1].lower()
                if file_extension not in config["ALLOWED_FILE_TYPES"]:
                    frappe.throw(_("Invalid file type: {0}").format(file_extension))
                if file_doc.file_size > config["MAX_FILE_SIZE_MB"] * 1024 * 1024:
                    frappe.throw(_("File size exceeds the maximum limit of {0}MB: {1}").format(
                        config["MAX_FILE_SIZE_MB"], file_doc.file_name))
                email_content += f"<li><a href='{attachment}'>{attachment}</a></li>"
            email_content += "</ul>"

        frappe.sendmail(
            recipients=config["RECIPIENT_EMAILS"],
            sender=sender_email,
            subject=f"Feedback: {subject}",
            message=email_content,
            now=True,
            with_container=True
        )

        frappe.response["message"] = _("Feedback email sent successfully")
        frappe.response["http_status_code"] = 200
        frappe.response["success"] = True
        return

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Feedback Email Error")
        frappe.response["message"] = str(e)
        frappe.response["http_status_code"] = 500
        frappe.response["success"] = False
        return

