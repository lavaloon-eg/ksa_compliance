import frappe
import pyqrcode


@frappe.whitelist()
def gen_qrcode(text):
    data = pyqrcode.create(text)

    return f'data:image/png;base64,{data.png_as_base64_str(scale=5)}'
