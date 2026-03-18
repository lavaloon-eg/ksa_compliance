import frappe


def execute():
    block_name = 'KSA Compliance Premium Announcement'
    html_content = """<div id="premium-announcement" style="
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: rgb(255 247 211);
    color: #3b3b3b;
    padding: 10px 16px;
    border-radius: 10px;
    border: 1px solid #e2d9b3;
    text-align: left;
    margin: 0;
">

    <div style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
    ">

        <div style="display:flex; align-items:center; gap:10px; flex:1;">

            <span style="font-size:12px;">🚀</span>

            <div style="font-size:12px; line-height:1.6;">
                <strong>{{ _("Unlock the Full Power of KSA Compliance!") }}</strong>:
                <span style="color:#6b7280;">
                    {{ _("Upgrade to our") }}
                    <span style="color:#ED1C24; font-weight:600;">
                        <span></span>{{ _("Premium version") }} <span></span>
                    </span>
                    {{ _("for advanced features; priority support and a seamless compliance experience.") }}
                </span>
            </div>

        </div>

        <div style="display:flex; align-items:center; gap:8px;">

            <a href="https://lavaloon.com/contact-us"
               target="_blank"
               style="
                    background:#ffffff;
                    border:1px solid #d7d7d9;
                    color:#3b3b3b;
                    text-decoration:none;
                    padding:2px 6px;
                    font-size:12px;
                    border-radius:6px;
                    font-weight:500;
                    white-space:nowrap;
               ">
               {{ _("Learn More") }}
            </a>

            <span style="
                cursor:pointer;
                font-size:18px;
                color:#6b7280;
                padding-left:4px;
            "
            onclick="this.closest('#premium-announcement').style.display='none'">
                ×
            </span>

        </div>

    </div>

</div>"""

    js_content = """
    // reference: https://discuss.frappe.io/t/how-does-translation-work-in-html-blocks/135109
    let elements = root_element.querySelectorAll('*:not(script):not(style)');
    elements.forEach(function(element) {
        if (element.childNodes.length) {
            element.childNodes.forEach(function(child) {
                if (child.nodeType === 3) {
                    let textContent = child.textContent.trim();
                    let regex = /\{\{\s*_\("(.+?)"\)\s*\}\}/g;
                    let matches = regex.exec(textContent);
                    if (matches && matches[1]) {
                        let translatableText = matches[1];
                        let translatedText = __(translatableText);
                        child.textContent = textContent.replace(matches[0], translatedText);
                    }
                }
            });
        }
    });
    
    const container = root_element.querySelector('#premium-announcement');

    if (container) {
        const is_rtl = frappe.utils.is_rtl
            ? frappe.utils.is_rtl()
            : document.documentElement.dir === "rtl";
    
        if (is_rtl) {
            container.setAttribute("dir", "rtl");
            container.style.textAlign = "right";
            container.style.borderLeft = "none";
        }
    }
    """

    if frappe.db.exists('Custom HTML Block', block_name):
        custom_block_doc = frappe.get_doc('Custom HTML Block', block_name)
        custom_block_doc.html = html_content
        custom_block_doc.script = js_content
        custom_block_doc.save()
        print(f'Custom HTML Block {block_name} updated successfully.')
    else:
        custom_block_doc = frappe.new_doc('Custom HTML Block')
        custom_block_doc.name = block_name
        custom_block_doc.html = html_content
        custom_block_doc.script = js_content
        custom_block_doc.insert()
        print(f'Custom HTML Block {block_name} created successfully.')
