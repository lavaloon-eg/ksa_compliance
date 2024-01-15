import subprocess
import frappe
from frappe.utils import execute_in_shell


@frappe.whitelist()
def get_pwd():
    try:
        err, out = execute_in_shell("pwd")
        err, out2 = execute_in_shell("fatoora -help")
        command = 'fatoora -help'
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        # Print the output
        print("Command Output:", result)
        return str(out), str(out2), str(err), str(result)

    except Exception as e:
        frappe.throw("error occured in get pwd" + str(e))
