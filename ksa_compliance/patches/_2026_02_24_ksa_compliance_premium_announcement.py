import frappe


def execute():
    block_name = "KSA Compliance Premium Announcement"
    html_content = """<div style="
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #FFFFF;
                    color: #000000;
                    padding: 28px;
                    border-radius: 16px;
                    text-align: center;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.25);
                    max-width: 520px;
                    margin: 0 auto;
                ">

                <div style="font-size: 26px; font-weight: 700; margin-bottom: 16px;">
                    🚀 {{ _("Unlock the Full Power of KSA Compliance!") }} 🚀
                </div>
            
                <div style="
                                    font-size: 16px;
                                    line-height: 1.7;
                                    color: #8a929c;
                                    margin-bottom: 22px;
                                ">
                    {{ _("Upgrade to our") }} <span
                        style="color:#ED1C24; font-weight:600;"><span>&nbsp</span> {{ _("Premium version") }}<span>&nbsp</span></span>
                    {{ _("for advanced features; priority support and a seamless compliance experience.") }}
                    <br><br>
                    {{ _("Take your business to the next level!") }} ✨
                </div>
            
                <a href="https://lavaloon.com/contact-us"
                   target="_blank"
                   style="
                                        display: inline-block;
                                        background: linear-gradient(135deg, #22c55e, #16a34a);
                                        color: #ffffff;
                                        text-decoration: none;
                                        padding: 14px 28px;
                                        font-size: 16px;
                                        font-weight: 600;
                                        border-radius: 50px;
                                        box-shadow: 0 6px 15px rgba(34,197,94,0.4);
                                        transition: all 0.2s ease-in-out;
                                   ">
                    {{ _("Learn More & Contact Us") }} &nbsp 📞
                </a>
            
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
