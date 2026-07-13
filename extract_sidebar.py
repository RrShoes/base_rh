import os

with open('templates/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if '<aside' in line:
        start_idx = i
    if '</aside>' in line:
        end_idx = i

if start_idx != -1 and end_idx != -1:
    sidebar_lines = lines[start_idx:end_idx+1]
    
    # Add User Profile to sidebar_lines
    ul_end_idx = -1
    for i, line in enumerate(sidebar_lines):
        if '</ul>' in line:
            ul_end_idx = i
            break
    
    if ul_end_idx != -1:
        user_block = """
            <!-- User Profile -->
            <div class="pt-6 border-t border-gray-100 mt-8">
                <div class="flex items-center gap-3 px-3 py-3 bg-gray-50 rounded-xl border border-gray-100">
                    <div class="w-10 h-10 rounded-full bg-brand-600 flex items-center justify-center text-white font-bold">
                        {% if current_user.is_authenticated %}
                            {{ current_user.username[0].upper() }}
                        {% else %}
                            <i class="fa-solid fa-user"></i>
                        {% endif %}
                    </div>
                    <div class="flex-1 min-w-0">
                        <p class="text-sm font-semibold text-gray-900 truncate">
                            {% if current_user.is_authenticated %}
                                {{ current_user.username }}
                            {% else %}
                                Visitante
                            {% endif %}
                        </p>
                        <p class="text-xs text-gray-500 truncate">
                            {% if current_user.is_authenticated %}
                                Administrador
                            {% else %}
                                Somente Leitura
                            {% endif %}
                        </p>
                    </div>
                    {% if current_user.is_authenticated %}
                    <a href="/logout" class="text-gray-400 hover:text-red-500 transition-colors p-2" title="Sair">
                        <i class="fa-solid fa-arrow-right-from-bracket"></i>
                    </a>
                    {% else %}
                    <a href="/login" class="text-gray-400 hover:text-brand-600 transition-colors p-2" title="Login">
                        <i class="fa-solid fa-arrow-right-to-bracket"></i>
                    </a>
                    {% endif %}
                </div>
            </div>
"""
        sidebar_lines.insert(ul_end_idx + 1, user_block)
    
    # Wrap filters in {% if request.path == '/' %}
    filters_start = -1
    for i, line in enumerate(sidebar_lines):
        if 'Mês / Ano' in line or 'Tipo de Contrato' in line or 'Agrupadores' in line:
            # wait, let's just find "<!-- Filters -->" or "Filtros"
            if '>Filtros<' in line.replace(' ', ''):
                # Backtrack to the start of the div
                for j in range(i, -1, -1):
                    if '<div class="space-y-6">' in sidebar_lines[j]:
                        filters_start = j
                        break
                break

    if filters_start != -1:
        sidebar_lines.insert(filters_start, '            {% if request.path == \'/\' %}\n')
        
        menu_start = -1
        for i in range(filters_start+1, len(sidebar_lines)):
            if 'Menu' in sidebar_lines[i] and 'fa-bars' in sidebar_lines[i-1]:
                # backtrack to <div class="pt-6 border-t
                for j in range(i, -1, -1):
                    if '<!-- Menu -->' in sidebar_lines[j]:
                        menu_start = j
                        break
                break
        
        if menu_start != -1:
            sidebar_lines.insert(menu_start, '            {% endif %}\n\n')

    with open('templates/sidebar.html', 'w', encoding='utf-8') as f:
        f.writelines(sidebar_lines)
    
    # Replace sidebar in index.html with include
    new_index_lines = lines[:start_idx] + ['    {% include "sidebar.html" %}\n'] + lines[end_idx+1:]
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.writelines(new_index_lines)

print("Sidebar extracted successfully.")
