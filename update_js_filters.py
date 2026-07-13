import os

main_js_path = r'static\js\main.js'

with open(main_js_path, 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Update populateMonthFilter to handle both Year and Month filters
old_populate_year = """const populateMonthFilter = () => {
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

new_populate_both = """const populateMonthFilter = () => {
    const yearFilter = document.getElementById('yearFilter');
    const monthFilter = document.getElementById('monthFilter');
    if (!yearFilter || !monthFilter) return;
    
    yearFilter.innerHTML = '';
    const uniqueYears = [...new Set(dashboardData.meses.map(m => m.split('-')[0]))].sort().reverse();
    uniqueYears.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = year;
        yearFilter.appendChild(option);
    });
    
    const monthNames = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
    
    const updateMonthOptions = () => {
        const selectedYear = yearFilter.value;
        const availableMonths = dashboardData.meses.filter(m => m.startsWith(selectedYear)).sort().reverse();
        
        monthFilter.innerHTML = '';
        availableMonths.forEach(mes => {
            const [year, month] = mes.split('-');
            const text = `${monthNames[parseInt(month) - 1]}`;
            const option = document.createElement('option');
            option.value = mes;
            option.textContent = text;
            monthFilter.appendChild(option);
        });
    };
    
    yearFilter.addEventListener('change', () => {
        updateMonthOptions();
        updateDashboard();
    });
    
    monthFilter.addEventListener('change', () => {
        updateDashboard();
    });
    
    const contractFilter = document.getElementById('contractFilter');
    if(contractFilter) {
        contractFilter.addEventListener('change', () => {
            updateDashboard();
        });
    }

    updateMonthOptions();
    populateAgrupadorFilters();
};"""

if old_populate_year in js:
    js = js.replace(old_populate_year, new_populate_both)
else:
    print("Warning: old populate year not found.")

# 2. Update updateDashboard selectedMonths logic
# Currently:
#    const yearFilter = document.getElementById('yearFilter');
#    let selectedMonths = [];
#    if (yearFilter && yearFilter.value) {
#        const year = yearFilter.value;
#        selectedMonths = dashboardData.meses.filter(m => m.startsWith(year));
#    }
# We need to change this to:
# selectedMonths (for charts) = all months in year
# selectedTableMonth (for table/kpis) = monthFilter.value
# We will define selectedMonths array for charts. But the table needs an array of months too, because `listaAgrupadaBase` uses `selectedMonths.includes(item.mes_str)`.
# So we can rename the table filter list to `selectedTableMonths` = [monthFilter.value].

old_selected_months = """    const yearFilter = document.getElementById('yearFilter');
    let selectedMonths = [];
    if (yearFilter && yearFilter.value) {
        const year = yearFilter.value;
        selectedMonths = dashboardData.meses.filter(m => m.startsWith(year));
    }"""

new_selected_months = """    const yearFilter = document.getElementById('yearFilter');
    const monthFilter = document.getElementById('monthFilter');
    
    let selectedMonths = [];
    if (yearFilter && yearFilter.value) {
        const year = yearFilter.value;
        selectedMonths = dashboardData.meses.filter(m => m.startsWith(year));
    }
    
    let selectedTableMonths = [];
    if (monthFilter && monthFilter.value) {
        selectedTableMonths = [monthFilter.value];
    } else {
        selectedTableMonths = selectedMonths;
    }"""

if old_selected_months in js:
    js = js.replace(old_selected_months, new_selected_months)
else:
    print("Warning: old selected months block not found.")

# Now we must replace all occurrences of `selectedMonths.includes(item.mes_str)` with `selectedTableMonths.includes(item.mes_str)`
# for the table generation block.
# Actually, the block that filters data for KPIs and Table is this:
# dashboardData.centros.forEach(item => { ... if (selectedMonths.includes(item.mes_str)) { ... }
# Let's just find that block and replace `selectedMonths.includes` with `selectedTableMonths.includes`.

js = js.replace("if (selectedMonths.includes(item.mes_str)) {", "if (selectedTableMonths.includes(item.mes_str)) {")

with open(main_js_path, 'w', encoding='utf-8') as f:
    f.write(js)

print("Updated main.js for month/year split logic.")
