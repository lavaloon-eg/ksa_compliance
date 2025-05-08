import json

import frappe
from frappe import _
import os


CONFIG = {
    "RECIPIENT_EMAIL": ["Khloud.aboelhasan@lavaloon.com", "Amr.Ashraf@lavaloon.com"], # FIXME: This should be a setting
    "MAX_FILE_SIZE_MB": 5,
    "ALLOWED_FILE_TYPES": ['.pdf', '.png', '.jpeg', '.docx'],
    "MAX_FILES": 3,
    "MAX_DESCRIPTION_LENGTH": 500,
    "CONTACT_CENTER_PAGE": "https://lavaloon.com/contact-us"
}

@frappe.whitelist()
def send_feedback_email(sender_email, subject, description, attachments=None):
    """Send feedback email using the default email account"""
    try:
        email_content = f"""
        <h3>Feedback Details</h3>
        <p><strong>Subject:</strong> {subject}</p>
        <p><strong>Description:</strong></p>
        <p>{description}</p>
        """

        if attachments:
            attachments = json.loads(attachments)
            email_content += "<h4>Attachments:</h4><ul>"
            for attachment in attachments:
                file_doc = frappe.get_doc("File", {"file_url": attachment})
                file_extension = os.path.splitext(file_doc.file_name)[1].lower()
                if file_extension not in CONFIG["ALLOWED_FILE_TYPES"]:
                    frappe.throw(_("Invalid file type: {0}").format(file_extension))
                if file_doc.file_size > CONFIG["MAX_FILE_SIZE_MB"] * 1024 * 1024:
                    frappe.throw(_("File size exceeds the maximum limit of {0}MB: {1}").format(
                        CONFIG["MAX_FILE_SIZE_MB"], file_doc.file_name))
                email_content += f"<li><a href='{attachment}'>{attachment}</a></li>"
            email_content += "</ul>"

        frappe.sendmail(
            recipients=CONFIG["RECIPIENT_EMAIL"],
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

