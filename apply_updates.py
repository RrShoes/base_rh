import os

main_js_path = r'static\js\main.js'

with open(main_js_path, 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Replace populateMonthFilter with populateYearFilter
old_populate_month = """const populateMonthFilter = () => {
    const monthFilterBtn = document.getElementById('monthFilterBtn');
    const monthFilterMenu = document.getElementById('monthFilterMenu');
    
    // Toggle menu
    monthFilterBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        monthFilterMenu.classList.toggle('hidden');
    });
    
    // Close when clicking outside
    document.addEventListener('click', (e) => {
        if (!monthFilterMenu.contains(e.target) && e.target !== monthFilterBtn) {
            monthFilterMenu.classList.add('hidden');
        }
    });
    
    monthFilterMenu.innerHTML = '';
    const monthNames = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
    
    dashboardData.meses.forEach(mes => {
        const [year, month] = mes.split('-');
        const text = `${monthNames[parseInt(month) - 1]} ${year}`;
        
        const label = document.createElement('label');
        label.className = 'flex items-center px-4 py-2 hover:bg-gray-100 cursor-pointer text-sm text-gray-700 w-full';
        label.innerHTML = `<input type="checkbox" value="${mes}" class="mr-3 month-checkbox form-checkbox h-4 w-4 text-brand-600 rounded transition duration-150 ease-in-out cursor-pointer"> <span>${text}</span>`;
        
        monthFilterMenu.appendChild(label);
    });
    
    // Listen for changes
    const checkboxes = document.querySelectorAll('.month-checkbox');
    checkboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            updateMonthFilterBtnText();
            updateDashboard();
        });
    });
    
    window.updateMonthFilterBtnText = () => {
        const selectedOptions = Array.from(document.querySelectorAll('.month-checkbox:checked'));
        if (selectedOptions.length === 0) {
            monthFilterBtn.textContent = 'Selecione os meses...';
        } else if (selectedOptions.length === 1) {
            monthFilterBtn.textContent = selectedOptions[0].nextElementSibling.textContent;
        } else {
            monthFilterBtn.textContent = `${selectedOptions.length} meses selecionados`;
        }
    };
    
    const contractFilter = document.getElementById('contractFilter');
    if(contractFilter) {
        contractFilter.addEventListener('change', () => {
            updateDashboard();
        });
    }

    populateAgrupadorFilters();
};"""

new_populate_year = """const populateMonthFilter = () => {
    // Retaining function name to avoid breaking calls, but it actually populates Year filter
    const yearFilter = document.getElementById('yearFilter');
    if (!yearFilter) return;
    
    yearFilter.innerHTML = '';
    
    // Extract unique years
    const uniqueYears = [...new Set(dashboardData.meses.map(m => m.split('-')[0]))].sort().reverse();
    
    uniqueYears.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearFilter.appendChild(option);
    });
    
    yearFilter.addEventListener('change', () => {
        updateDashboard();
    });
    
    const contractFilter = document.getElementById('contractFilter');
    if(contractFilter) {
        contractFilter.addEventListener('change', () => {
            updateDashboard();
        });
    }

    populateAgrupadorFilters();
};"""

if old_populate_month in js:
    js = js.replace(old_populate_month, new_populate_year)
else:
    print("WARNING: Could not find old populateMonthFilter to replace")

# 2. Update init to not use checkboxes
old_init = """            // Select the most recent month by default
            if (dashboardData.meses && dashboardData.meses.length > 0) {
                const latestMonth = dashboardData.meses[dashboardData.meses.length - 1];
                const cb = document.querySelector(`.month-checkbox[value="${latestMonth}"]`);
                if (cb) cb.checked = true;
                if (typeof updateMonthFilterBtnText === 'function') updateMonthFilterBtnText();
                updateDashboard();
            }"""
new_init = """            // Select the most recent year by default (handled by option being first)
            if (dashboardData.meses && dashboardData.meses.length > 0) {
                updateDashboard();
            }"""
if old_init in js:
    js = js.replace(old_init, new_init)

# 3. Fix updateDashboard selectedMonths logic
old_selected_months = """    const selectedMonthCheckboxes = document.querySelectorAll('.month-checkbox:checked');
    const selectedMonths = Array.from(selectedMonthCheckboxes).map(cb => cb.value);"""
new_selected_months = """    const yearFilter = document.getElementById('yearFilter');
    let selectedMonths = [];
    if (yearFilter && yearFilter.value) {
        const year = yearFilter.value;
        selectedMonths = dashboardData.meses.filter(m => m.startsWith(year));
    }"""
if old_selected_months in js:
    js = js.replace(old_selected_months, new_selected_months)

# 4. Remove unwanted charts logic
# Remove global vars
js = js.replace("let histSituacaoChartInstance = null;\n", "")
# Remove canvas destruction
js = js.replace("""    if (histSituacaoChartInstance) histSituacaoChartInstance.destroy();
    if (costChartInstance) costChartInstance.destroy();
    if (peopleChartInstance) peopleChartInstance.destroy();\n""", "")

# Remove render of histSituacao
hist_sit_logic_start = js.find("    // 4. Histórico INSS e Rescisão")
hist_sit_logic_end = js.find("    // ----- RENDER MONTHLY TOP 5 CHARTS -----")
if hist_sit_logic_start != -1 and hist_sit_logic_end != -1:
    js = js[:hist_sit_logic_start] + js[hist_sit_logic_end:]

# Remove render of Monthly Top 5 charts
monthly_charts_start = js.find("    // ----- RENDER MONTHLY TOP 5 CHARTS -----")
monthly_charts_end = js.find("    // ----- RENDER DETAILS MODAL CHARTS -----")
if monthly_charts_start != -1 and monthly_charts_end != -1:
    js = js[:monthly_charts_start] + js[monthly_charts_end:]

with open(main_js_path, 'w', encoding='utf-8') as f:
    f.write(js)

print("Updated main.js")

# Now update data_processor.py
dp_path = 'data_processor.py'
with open(dp_path, 'r', encoding='utf-8') as f:
    dp = f.read()

# 1. Update is_clt to is_clt_ativo for aggregation
old_is_clt = """        df_clean['is_clt'] = (df_clean['tipo_contrato'] == 'CLT').astype(int)
        df_clean['is_pj'] = (df_clean['tipo_contrato'] == 'PJ').astype(int)
        
        # Auxiliar columns for aggregation
        df_clean['custo_clt'] = df_clean.apply(lambda row: row['custo_total'] if row['is_clt'] else 0, axis=1)
        df_clean['custo_pj'] = df_clean.apply(lambda row: row['custo_total'] if row['is_pj'] else 0, axis=1)"""

new_is_clt = """        df_clean['is_clt'] = (df_clean['tipo_contrato'] == 'CLT').astype(int)
        df_clean['is_clt_ativo'] = ((df_clean['tipo_contrato'] == 'CLT') & (df_clean['situacao'] == 1)).astype(int)
        df_clean['is_pj'] = (df_clean['tipo_contrato'] == 'PJ').astype(int)
        
        # Auxiliar columns for aggregation
        df_clean['custo_clt'] = df_clean.apply(lambda row: row['custo_total'] if row['is_clt_ativo'] else 0, axis=1)
        df_clean['custo_pj'] = df_clean.apply(lambda row: row['custo_total'] if row['is_pj'] else 0, axis=1)
        # Fix custo_total to only include active clt and pj
        df_clean['custo_total'] = df_clean['custo_clt'] + df_clean['custo_pj']"""

if old_is_clt in dp:
    dp = dp.replace(old_is_clt, new_is_clt)
else:
    print("WARNING: Could not find old_is_clt block")

# 2. Update qtd_clt aggregation in groupby
old_groupby = """        agrupado_centro = df_clean.groupby(['mes_str', 'centro_custo', 'agrupador1', 'agrupador2', 'agrupador3']).agg(
            qtd_pessoas=('matricula', 'count'),
            qtd_clt=('is_clt', 'sum'),"""
new_groupby = """        agrupado_centro = df_clean.groupby(['mes_str', 'centro_custo', 'agrupador1', 'agrupador2', 'agrupador3']).agg(
            qtd_pessoas=('matricula', 'count'),
            qtd_clt=('is_clt_ativo', 'sum'),"""
if old_groupby in dp:
    dp = dp.replace(old_groupby, new_groupby)
else:
    print("WARNING: Could not find old groupby block")

# 3. Update total_pessoas in the json result
old_centros = """                    'qtd_clt': int(row['qtd_clt']),
                    'qtd_pj': int(row['qtd_pj']),
                    'total_pessoas': int(row['qtd_pessoas']),"""
new_centros = """                    'qtd_clt': int(row['qtd_clt']),
                    'qtd_pj': int(row['qtd_pj']),
                    'total_pessoas': int(row['qtd_clt']) + int(row['qtd_pj']),"""
if old_centros in dp:
    dp = dp.replace(old_centros, new_centros)
else:
    print("WARNING: Could not find old centros block")

with open(dp_path, 'w', encoding='utf-8') as f:
    f.write(dp)

print("Updated data_processor.py")
