import os

files = ['templates/admin.html', 'templates/agrupadores.html', 'templates/pj_form.html']

for filepath in files:
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # 1. Add Tailwind CSS if not present
    if 'cdn.tailwindcss.com' not in html:
        html = html.replace('</title>', '</title>\n    <script src="https://cdn.tailwindcss.com"></script>')
    
    # 2. Remove the old sidebar block
    # The old sidebar starts with <div class="sidebar"> and ends before <div class="main">
    # Let's extract it.
    start_str = '<div class="sidebar">'
    end_str = '<div class="main">'
    
    start_idx = html.find(start_str)
    end_idx = html.find(end_str)
    
    if start_idx != -1 and end_idx != -1:
        # We need to make sure we don't accidentally remove things we shouldn't.
        # So we just replace the substring from start_idx to end_idx with empty.
        html = html[:start_idx] + html[end_idx:]
    
    # 3. Add the include for sidebar.html at the end of the body
    # We want it AFTER <div class="main">...</div>, so before </body>
    if '{% include "sidebar.html" %}' not in html:
        html = html.replace('</body>', '    {% include "sidebar.html" %}\n</body>')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

print("Admin templates updated.")
