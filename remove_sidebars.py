import os

files = ['templates/admin.html', 'templates/agrupadores.html', 'templates/pj_form.html']

for filepath in files:
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()
    
    # The old sidebar starts with <aside class="sidebar"> and ends before <main class="main">
    # Let's check exactly what the main class is.
    # From the file view, we see: <main class="main">
    # Let's extract between <aside class="sidebar"> and <main class="main">
    start_str = '<aside class="sidebar">'
    
    # Find the end of aside
    start_idx = html.find(start_str)
    if start_idx != -1:
        # Find the closing </aside> tag after start_idx
        end_idx = html.find('</aside>', start_idx)
        if end_idx != -1:
            # We want to remove everything from start_idx up to end_idx + len('</aside>')
            html = html[:start_idx] + html[end_idx + len('</aside>'):]
    
    # Also check if they had <div class="sidebar">
    start_str2 = '<div class="sidebar">'
    start_idx2 = html.find(start_str2)
    if start_idx2 != -1:
        end_idx2 = html.find('</div>', start_idx2)
        # Actually it's dangerous to just replace the first </div>, we should find `<div class="main">` or `<main class="main">`
        main_idx = html.find('<main class="main">')
        if main_idx == -1:
            main_idx = html.find('<div class="main">')
        
        if main_idx != -1:
            html = html[:start_idx2] + html[main_idx:]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

print("Admin templates sidebars removed.")
