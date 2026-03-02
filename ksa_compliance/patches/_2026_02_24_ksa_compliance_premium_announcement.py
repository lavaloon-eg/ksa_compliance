import frappe


def execute():
    block_name = 'KSA Compliance Premium Announcement'
    html_content = """<div id="premium-announcement" style="
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #FFFFFF;
    color: #000000;
    padding: 4px 16px;
    border-radius: 16px;
    border-left: 4px solid #ED1C24;
    text-align: left;
    box-shadow: 0 12px 25px rgba(0,0,0,0.25);
    margin: 0 0;
">

    <!-- Header -->
    <div style="
        display: flex;
        justify-content: space-between;
        align-items: center;
        cursor: pointer;
    "
    onclick="
        const body = this.parentElement.querySelector('.premium-body');
        const icon = this.querySelector('.toggle-icon');
        if (body.style.display === 'none') {
            body.style.display = 'block';
            icon.innerHTML = '−';
        } else {
            body.style.display = 'none';
            icon.innerHTML = '+';
        }
    ">
        <div style="font-size: 14px; font-weight: 700;">
            🚀 {{ _("Unlock the Full Power of KSA Compliance!") }}
        </div>

        <div class="toggle-icon" style="
            font-size: 22px;
            font-weight: bold;
            color: #ED1C24;
            padding-left: 10px;
        ">
            −
        </div>
    </div>

    <!-- Collapsible Body -->
    <div class="premium-body" style="margin-top:18px;">

        <div style="
            font-size: 14px;
            line-height: 1.7;
            color: #8a929c;
            margin-bottom: 22px;
        ">
            {{ _("Upgrade to our") }}
            <span style="color:#ED1C24; font-weight:600;">
                <span>&nbsp;</span>{{ _("Premium version") }}<span>&nbsp;</span>
            </span>
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
                padding: 8px 18px;
                font-size: 12px;
                font-weight: 600;
                border-radius: 16px;
                margin-bottom: 6px;
                box-shadow: 0 6px 15px rgba(34,197,94,0.4);
           ">
            {{ _("Learn More & Contact Us") }} &nbsp;📞
        </a>

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
            container.style.borderRight = "4px solid #ED1C24";
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
