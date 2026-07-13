// Global variables for charts
let costChartInstance = null;
let peopleChartInstance = null;
let histCostChartInstance = null;
let histPeopleChartInstance = null;
let histTurnoverChartInstance = null;
let modalCostChartInstance = null;
let modalPeopleChartInstance = null;
let modalTurnoverChartInstance = null;
let modalSituacaoChartInstance = null;
let dashboardData = null;

// Register datalabels globally
if (typeof ChartDataLabels !== 'undefined') {
    Chart.register(ChartDataLabels);
}

// Format currency
const formatCurrency = (value) => {
    if (value === -1) return 'Confidencial';
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value);
};

// Format number
const formatNumber = (value) => {
    return new Intl.NumberFormat('pt-BR').format(value);
};

// Calculates Turnover %
function calcularTurnover(admissoes, desligamentos, totalInicial, totalFinal) {
    if (totalInicial === 0 && totalFinal === 0) {
        return { geral: 0, saida: 0, mediaFuncionarios: 0 };
    }
    const mediaFuncionarios = (totalInicial + totalFinal) / 2;
    const fluxoTotal = (admissoes + desligamentos) / 2;
    const turnoverGeral = (fluxoTotal / mediaFuncionarios) * 100;
    const turnoverSaida = (desligamentos / mediaFuncionarios) * 100;
    return {
        geral: Number(turnoverGeral.toFixed(2)),
        saida: Number(turnoverSaida.toFixed(2)),
        mediaFuncionarios: mediaFuncionarios
    };
}

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', () => {
    fetchData();
});

// Fetch data from API
const fetchData = async () => {
    try {
        const response = await fetch('/api/dados');
        const result = await response.json();
        
        if (result.success) {
            dashboardData = result.data;
            
            populateMonthFilter();
            
            // Select the most recent year by default (handled by option being first)
            if (dashboardData.meses && dashboardData.meses.length > 0) {
                updateDashboard();
            }
            
            // Hide loader and show dashboard
            document.getElementById('loader').classList.add('hidden');
            document.getElementById('dashboardContent').classList.remove('hidden');
        } else {
            console.error('Error fetching data:', result.error);
            alert('Erro ao carregar dados: ' + result.error);
        }
    } catch (error) {
        console.error('Fetch error:', error);
        alert('Erro ao comunicar com o servidor.');
    }
};

// Populate Month Filter Dropdown
const populateMonthFilter = () => {
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
        const availableMonths = dashboardData.meses.filter(m => m.startsWith(selectedYear)).sort();
        
        monthFilter.innerHTML = '';
        availableMonths.forEach(mes => {
            const [year, month] = mes.split('-');
            const text = `${monthNames[parseInt(month) - 1]}`;
            const option = document.createElement('option');
            option.value = mes;
            option.textContent = text;
            monthFilter.appendChild(option);
        });
        
        if (availableMonths.length > 0) {
            monthFilter.value = availableMonths[availableMonths.length - 1];
        }
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
            if (window.currentAgrupador && !document.getElementById('detalheContent').classList.contains('hidden')) {
                openDetalhe360(window.currentAgrupador);
            }
        });
    }
    
    const activePessoasFilter = document.getElementById('activePessoasFilter');
    if(activePessoasFilter) {
        activePessoasFilter.addEventListener('change', () => {
            if (window.currentAgrupador && !document.getElementById('detalheContent').classList.contains('hidden')) {
                openDetalhe360(window.currentAgrupador);
            }
        });
    }
    
    const valorTypeFilter = document.getElementById('valorTypeFilter');
    if(valorTypeFilter) {
        valorTypeFilter.addEventListener('change', () => {
            if (window.currentAgrupador && !document.getElementById('detalheContent').classList.contains('hidden')) {
                openDetalhe360(window.currentAgrupador);
            }
        });
    }

    updateMonthOptions();
    populateAgrupadorFilters();
};

function populateAgrupadorFilters() {
    const ag1Set = new Set(), ag2Set = new Set(), ag3Set = new Set();
    
    // Extract unique values from all months
    dashboardData.meses.forEach(m => {
        if (!dashboardData.dados[m]) return;
        dashboardData.dados[m].centros.forEach(item => {
            if (item.agrupador1) ag1Set.add(item.agrupador1);
            if (item.agrupador2) ag2Set.add(item.agrupador2);
            if (item.agrupador3) ag3Set.add(item.agrupador3);
        });
    });

    const populateSelect = (id, set) => {
        const sel = document.getElementById(id);
        if (!sel) return;
        const cur = sel.value;
        while (sel.options.length > 1) sel.remove(1);
        Array.from(set).sort().forEach(val => {
            const opt = document.createElement('option');
            opt.value = val;
            opt.textContent = val;
            if (val === cur) opt.selected = true;
            sel.appendChild(opt);
        });
    };

    populateSelect('agrupador1Filter', ag1Set);
    populateSelect('agrupador2Filter', ag2Set);
    populateSelect('agrupador3Filter', ag3Set);
};

window.applyFilters = () => {
    updateDashboard();
};

// Update entire dashboard based on selected month and grouping
const updateDashboard = () => {
    const yearFilter = document.getElementById('yearFilter');
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
    }
    
    const contractType = document.getElementById('contractFilter') ? document.getElementById('contractFilter').value : 'todos';
    
    if (selectedTableMonths.length === 0) return;
    
    // Sort months chronologically
    selectedTableMonths.sort();
    
    const filterAg1 = document.getElementById('agrupador1Filter') ? document.getElementById('agrupador1Filter').value : '';
    const filterAg2 = document.getElementById('agrupador2Filter') ? document.getElementById('agrupador2Filter').value : '';
    const filterAg3 = document.getElementById('agrupador3Filter') ? document.getElementById('agrupador3Filter').value : '';
    
    let totalPessoas = 0;
    let custoTotal = 0;
    let listaAgrupadaBase = [];
    
    // Helper function to check if item passes the groupings filter
    const passesFilter = (item) => {
        if (filterAg1 && item.agrupador1 !== filterAg1) return false;
        if (filterAg2 && item.agrupador2 !== filterAg2) return false;
        if (filterAg3 && item.agrupador3 !== filterAg3) return false;
        return true;
    };
    
    if (selectedTableMonths.length === 1) {
        const dataMes = dashboardData.dados[selectedTableMonths[0]];
        if (!dataMes) return;
        
        // Dynamic aggregation even for 1 month because there are multiple groupings now
        const mapCentros = {};
        dataMes.centros.forEach(item => {
            if (!passesFilter(item)) return;
            const keyAgrupador = item.agrupador3 || 'Sem Classificação';
            if (!mapCentros[keyAgrupador]) {
                mapCentros[keyAgrupador] = { ...item, agrupador: keyAgrupador, custo_total: 0, custo_clt: 0, custo_pj: 0, sit_1: 0, sit_2: 0, sit_3: 0, qtd_clt: 0, qtd_pj: 0, total_pessoas: 0 };
            }
            if (item.custo_total !== -1) mapCentros[keyAgrupador].custo_total += item.custo_total;
            if (item.custo_clt !== -1) mapCentros[keyAgrupador].custo_clt += item.custo_clt;
            if (item.custo_pj !== -1) mapCentros[keyAgrupador].custo_pj += item.custo_pj;
            
            mapCentros[keyAgrupador].qtd_clt += item.qtd_clt;
            mapCentros[keyAgrupador].qtd_pj += item.qtd_pj;
            mapCentros[keyAgrupador].total_pessoas += item.total_pessoas;
            mapCentros[keyAgrupador].sit_1 += item.sit_1;
            mapCentros[keyAgrupador].sit_2 += item.sit_2;
            mapCentros[keyAgrupador].sit_3 += item.sit_3;
        });
        
        listaAgrupadaBase = Object.values(mapCentros).sort((a, b) => b.custo_total - a.custo_total);
    } else {
        // Dynamic aggregation for multiple months
        const mapCentros = {};
        
        selectedTableMonths.forEach(m => {
            if (!dashboardData.dados[m]) return;
            dashboardData.dados[m].centros.forEach(item => {
                if (!passesFilter(item)) return;
                
                const keyAgrupador = item.agrupador3 || 'Sem Classificação';
                if (!mapCentros[keyAgrupador]) {
                    mapCentros[keyAgrupador] = { ...item, agrupador: keyAgrupador, custo_total: 0, custo_clt: 0, custo_pj: 0, sit_1: 0, sit_2: 0, sit_3: 0, qtd_clt: 0, qtd_pj: 0, total_pessoas: 0 };
                }
                if (item.custo_total !== -1) mapCentros[keyAgrupador].custo_total += item.custo_total;
                if (item.custo_clt !== -1) mapCentros[keyAgrupador].custo_clt += item.custo_clt;
                if (item.custo_pj !== -1) mapCentros[keyAgrupador].custo_pj += item.custo_pj;
                
                // For people metrics across months we sum the individual chunks, but max across the chunks?
                // Wait: the data has chunks per (mes, CC, ag1, ag2, ag3). 
                // To get average or max people over period, we can accumulate and average, or just max.
                // Let's take the max per chunk across the months to preserve the behavior:
                // Actually since it's the same CC, we need to track by month and then average. For now we use the logic:
                mapCentros[keyAgrupador].qtd_clt = Math.max(mapCentros[keyAgrupador].qtd_clt, item.qtd_clt);
                mapCentros[keyAgrupador].qtd_pj = Math.max(mapCentros[keyAgrupador].qtd_pj, item.qtd_pj);
                mapCentros[keyAgrupador].total_pessoas = Math.max(mapCentros[keyAgrupador].total_pessoas, item.total_pessoas);
                
                mapCentros[keyAgrupador].sit_1 = Math.max(mapCentros[keyAgrupador].sit_1, item.sit_1);
                mapCentros[keyAgrupador].sit_2 += item.sit_2;
                mapCentros[keyAgrupador].sit_3 += item.sit_3;
            });
        });
        
        listaAgrupadaBase = Object.values(mapCentros).sort((a, b) => b.custo_total - a.custo_total);
    }
    
    if (contractType === 'clt') {
        totalPessoas = listaAgrupadaBase.reduce((sum, item) => sum + item.qtd_clt, 0);
        custoTotal = (!dashboardData.show_salaries && totalPessoas > 0 && totalPessoas < 10) ? -1 : listaAgrupadaBase.reduce((sum, item) => sum + (item.custo_clt !== -1 ? item.custo_clt : 0), 0);
    } else if (contractType === 'pj') {
        totalPessoas = listaAgrupadaBase.reduce((sum, item) => sum + item.qtd_pj, 0);
        custoTotal = (!dashboardData.show_salaries && totalPessoas > 0 && totalPessoas < 10) ? -1 : listaAgrupadaBase.reduce((sum, item) => sum + (item.custo_pj !== -1 ? item.custo_pj : 0), 0);
    } else {
        totalPessoas = listaAgrupadaBase.reduce((sum, item) => sum + item.total_pessoas, 0);
        custoTotal = (!dashboardData.show_salaries && totalPessoas > 0 && totalPessoas < 10) ? -1 : listaAgrupadaBase.reduce((sum, item) => sum + (item.custo_total !== -1 ? item.custo_total : 0), 0);
    }
    
    const listaAgrupada = listaAgrupadaBase.map(item => {
        let tp = item.total_pessoas;
        let ct = item.custo_total;
        if (contractType === 'clt') {
            tp = item.qtd_clt;
            ct = item.custo_clt;
        } else if (contractType === 'pj') {
            tp = item.qtd_pj;
            ct = item.custo_pj;
        }
        
        let has_confidential = !dashboardData.show_salaries && ((tp > 0 && tp < 10) || ct === 0);
        
        return {
            ...item,
            total_pessoas: tp,
            custo_total: has_confidential ? -1 : ct,
            has_confidential: has_confidential
        };
    }).sort((a, b) => b.custo_total - a.custo_total).filter(item => item.total_pessoas > 0 || item.custo_total > 0);
    
    // Calculate KPI values
    let kpiLastPeople = 0, kpiAvgPeople = 0;
    let kpiLastCost = 0, kpiAvgCost = 0;
    let kpiLastTurnover = 0, kpiAvgTurnover = 0;
    
    const hasAgrupadorFilter = filterAg1 || filterAg2 || filterAg3;
    let localHistorico = dashboardData.historico;

    // Dynamically build historico if agrupador filter is active
    if (hasAgrupadorFilter && dashboardData.historico) {
        localHistorico = {
            meses: dashboardData.historico.meses,
            total_pessoas: [], custo_total: [], total_clt: [], total_pj: [], custo_clt: [], custo_pj: [],
            entradas: [], saidas: [], entradas_clt: [], saidas_clt: [], entradas_pj: [], saidas_pj: [],
            inss: [], rescisao: [], inss_clt: [], rescisao_clt: [], inss_pj: [], rescisao_pj: []
        };
        dashboardData.historico.meses.forEach((m, idx) => {
            let p = 0, c = 0, pclt = 0, ppj = 0, cclt = 0, cpj = 0, inss = 0, res = 0, ent = 0, sai = 0;
            let validCentros = [];
            
            if (dashboardData.dados[m] && dashboardData.dados[m].centros) {
                const filtered = dashboardData.dados[m].centros.filter(passesFilter);
                validCentros = filtered.map(item => item.agrupador);
                filtered.forEach(item => {
                    p += item.total_pessoas;
                    if (item.custo_total !== -1) c += item.custo_total;
                    pclt += item.qtd_clt; ppj += item.qtd_pj;
                    if (item.custo_clt !== -1) cclt += item.custo_clt;
                    if (item.custo_pj !== -1) cpj += item.custo_pj;
                    inss += item.sit_2; res += item.sit_3;
                });
                if (!dashboardData.show_salaries && ((p > 0 && p < 10) || c === 0)) {
                    c = -1; cclt = -1; cpj = -1;
                }
            }
            if (dashboardData.historico_detalhado && dashboardData.historico_detalhado.centros) {
                validCentros.forEach(cc => {
                    if (dashboardData.historico_detalhado.centros[cc]) {
                        ent += dashboardData.historico_detalhado.centros[cc].entradas[idx] || 0;
                        sai += dashboardData.historico_detalhado.centros[cc].saidas[idx] || 0;
                    }
                });
            }
            localHistorico.total_pessoas.push(p); localHistorico.custo_total.push(c);
            localHistorico.total_clt.push(pclt); localHistorico.total_pj.push(ppj);
            localHistorico.custo_clt.push(cclt); localHistorico.custo_pj.push(cpj);
            localHistorico.inss.push(inss); localHistorico.rescisao.push(res);
            localHistorico.entradas.push(ent); localHistorico.saidas.push(sai);
            
            // Fallbacks for split arrays when filtered
            localHistorico.inss_clt.push(inss); localHistorico.rescisao_clt.push(res);
            localHistorico.inss_pj.push(inss); localHistorico.rescisao_pj.push(res);
            localHistorico.entradas_clt.push(ent); localHistorico.saidas_clt.push(sai);
            localHistorico.entradas_pj.push(ent); localHistorico.saidas_pj.push(sai);
        });
    }

    if (selectedMonths.length > 0 && localHistorico) {
        let sumPeople = 0, sumCost = 0, sumTurnover = 0;
        let turnoverMonthsCount = 0;
        
        // Target month for the main KPI number (usually the selected month in the table)
        const targetMonth = selectedTableMonths[selectedTableMonths.length - 1];
        
        selectedMonths.forEach(m => {
            const idx = localHistorico.meses.indexOf(m);
            if (idx !== -1) {
                let p = 0, c = 0, t = 0;
                let adm = 0, des = 0, tf = 0, ti = 0;
                
                if (contractType === 'clt') {
                    p = localHistorico.total_clt[idx];
                    c = localHistorico.custo_clt[idx];
                    adm = localHistorico.entradas_clt[idx];
                    des = localHistorico.saidas_clt[idx];
                } else if (contractType === 'pj') {
                    p = localHistorico.total_pj[idx];
                    c = localHistorico.custo_pj[idx];
                    adm = localHistorico.entradas_pj[idx];
                    des = localHistorico.saidas_pj[idx];
                } else {
                    p = localHistorico.total_pessoas[idx];
                    c = localHistorico.custo_total[idx];
                    adm = localHistorico.entradas[idx];
                    des = localHistorico.saidas[idx];
                }
                
                tf = p;
                ti = tf - adm + des;
                if (idx === 0) ti = tf; // Approximation for first month
                
                t = calcularTurnover(adm, des, ti, tf).geral;
                
                if (c === -1) {
                    sumCost = -1; // If any month is confidential, the average is confidential
                } else if (sumCost !== -1) {
                    sumCost += c;
                }
                
                if (m !== selectedMonths[0]) {
                    sumTurnover += t;
                    turnoverMonthsCount++;
                } else if (selectedMonths.length === 1) {
                    sumTurnover += t;
                    turnoverMonthsCount = 1;
                }
                
                // Set the big KPI number based on the selected month for the table
                if (m === targetMonth) {
                    kpiLastPeople = p;
                    kpiLastCost = c;
                    kpiLastTurnover = t;
                }
            }
        });
        
        kpiAvgPeople = sumPeople / selectedMonths.length;
        kpiAvgCost = sumCost === -1 ? -1 : sumCost / selectedMonths.length;
        kpiAvgTurnover = turnoverMonthsCount > 0 ? (sumTurnover / turnoverMonthsCount) : 0;
    }

    // Update KPIs HTML
    document.getElementById('kpiTotalPessoas').textContent = formatNumber(totalPessoas);
    const subPessoas = document.getElementById('kpiTotalPessoasSub');
    if (subPessoas) subPessoas.textContent = `Média do período: ${formatNumber(Math.round(kpiAvgPeople))}`;
    
    document.getElementById('kpiCustoTotal').textContent = formatCurrency(custoTotal);
    const subCusto = document.getElementById('kpiCustoTotalSub');
    if (subCusto) subCusto.textContent = `Média do período: ${formatCurrency(kpiAvgCost)}`;
    
    const turnoverEl = document.getElementById('kpiTurnover');
    turnoverEl.innerHTML = `<span class="text-gray-900">${kpiLastTurnover.toFixed(2).replace('.', ',')}%</span>`;
    const subTurnover = document.getElementById('kpiTurnoverSub');
    if (subTurnover) subTurnover.textContent = `Média do período: ${kpiAvgTurnover.toFixed(2).replace('.', ',')}%`;
    
    // Update Table
    updateTable(listaAgrupada, totalPessoas, custoTotal);
    
    // Filter and Update Historical Charts
    if (localHistorico) {
        const filteredHistorico = {
            meses: [], custo_total: [], custo_clt: [], custo_pj: [],
            total_pessoas: [], total_clt: [], total_pj: [],
            entradas: [], saidas: [], inss: [], rescisao: []
        };
        localHistorico.meses.forEach((mes, idx) => {
            if (selectedMonths.includes(mes)) {
                filteredHistorico.meses.push(mes);
                filteredHistorico.custo_total.push(localHistorico.custo_total[idx]);
                filteredHistorico.custo_clt.push(localHistorico.custo_clt[idx]);
                filteredHistorico.custo_pj.push(localHistorico.custo_pj[idx]);
                filteredHistorico.total_pessoas.push(localHistorico.total_pessoas[idx]);
                filteredHistorico.total_clt.push(localHistorico.total_clt[idx]);
                filteredHistorico.total_pj.push(localHistorico.total_pj[idx]);
                
                // Zero adm/des for the first selected month so it acts as baseline
                if (filteredHistorico.meses.length === 1) {
                    filteredHistorico.entradas.push(0);
                    filteredHistorico.saidas.push(0);
                } else {
                    if (contractType === 'clt') {
                        filteredHistorico.entradas.push(localHistorico.entradas_clt[idx]);
                        filteredHistorico.saidas.push(localHistorico.saidas_clt[idx]);
                    } else if (contractType === 'pj') {
                        filteredHistorico.entradas.push(localHistorico.entradas_pj[idx]);
                        filteredHistorico.saidas.push(localHistorico.saidas_pj[idx]);
                    } else {
                        filteredHistorico.entradas.push(localHistorico.entradas[idx]);
                        filteredHistorico.saidas.push(localHistorico.saidas[idx]);
                    }
                }
                
                if (contractType === 'clt') {
                    filteredHistorico.inss.push(localHistorico.inss_clt[idx]);
                    filteredHistorico.rescisao.push(localHistorico.rescisao_clt[idx]);
                } else if (contractType === 'pj') {
                    filteredHistorico.inss.push(localHistorico.inss_pj[idx]);
                    filteredHistorico.rescisao.push(localHistorico.rescisao_pj[idx]);
                } else {
                    filteredHistorico.inss.push(localHistorico.inss[idx]);
                    filteredHistorico.rescisao.push(localHistorico.rescisao[idx]);
                }
            }
        });
        initHistoricalCharts(filteredHistorico, contractType, localHistorico);
    }
};


// Update Table
const updateTable = (listaAgrupada, totalPessoas, totalCusto) => {
    const tbody = document.getElementById('dataTableBody');
    tbody.innerHTML = '';
    
    const thAgrupador = document.getElementById('thAgrupador');
    if (thAgrupador) {
        thAgrupador.textContent = 'Centro de Custo';
    }
    
    // Calculate Totals for the new summary row
    let sumClt = 0, sumPj = 0, sumReg = 0;
    listaAgrupada.forEach(item => {
        sumClt += item.qtd_clt || 0;
        sumPj += item.qtd_pj || 0;
        sumReg += item.sit_1 || 0;
    });

    // Create Totals Row
    const trTotal = document.createElement('tr');
    trTotal.className = 'bg-gray-100 font-bold border-b-2 border-gray-300 cursor-pointer hover:bg-gray-200 transition-colors';
    trTotal.onclick = () => openDetalhe360('TOTAL GERAL');
    trTotal.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">TOTAL GERAL</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-center">${formatNumber(totalPessoas)}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-center">${formatNumber(sumClt)}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-center">${formatNumber(sumPj)}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-center">100,00%</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">${formatCurrency(totalCusto)}</td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">${totalCusto === -1 ? '***' : '100,00%'}</td>
    `;
    tbody.appendChild(trTotal);

    listaAgrupada.forEach(item => {
        const tr = document.createElement('tr');
        tr.className = 'hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-0 cursor-pointer';
        tr.onclick = () => openDetalhe360(item.agrupador);
        
        // Calculate percentages
        const pctPessoas = totalPessoas > 0 ? (item.total_pessoas / totalPessoas) * 100 : 0;
        const pctCusto = (totalCusto > 0 && item.custo_total !== -1) ? (item.custo_total / totalCusto) * 100 : 0;
        
        // Format percentages (e.g., 15,34%)
        const formattedPctPessoas = pctPessoas.toFixed(2).replace('.', ',') + '%';
        const formattedPctCusto = item.custo_total === -1 ? '***' : pctCusto.toFixed(2).replace('.', ',') + '%';

        tr.innerHTML = `
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${item.agrupador}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900 text-center">${formatNumber(item.total_pessoas)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">${formatNumber(item.qtd_clt)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">${formatNumber(item.qtd_pj)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">${formattedPctPessoas}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right font-medium">${formatCurrency(item.custo_total)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">${formattedPctCusto}</td>
        `;
        
        tbody.appendChild(tr);
    });
};

// Initialize Historical Charts
const initHistoricalCharts = (historico, contractType = 'todos', fullLocalHistorico = null) => {
    if (!historico) return;

    if (histCostChartInstance) histCostChartInstance.destroy();
    if (histPeopleChartInstance) histPeopleChartInstance.destroy();
    if (histTurnoverChartInstance) histTurnoverChartInstance.destroy();


    const monthNames = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
    const labels = historico.meses.map(mes => {
        const [year, month] = mes.split('-');
        return `${monthNames[parseInt(month) - 1]} ${year}`;
    });

    let dataCost = [];
    let dataPeople = [];
    
    if (contractType === 'clt') {
        dataCost = historico.custo_clt.map(v => v === -1 ? null : v);
        dataPeople = historico.total_clt;
    } else if (contractType === 'pj') {
        dataCost = historico.custo_pj.map(v => v === -1 ? null : v);
        dataPeople = historico.total_pj;
    } else {
        dataCost = historico.custo_total.map(v => v === -1 ? null : v);
        dataPeople = historico.total_pessoas;
    }

    // Goal Logic (June 2026) using fullLocalHistorico (which respects agrupadores)
    const refData = fullLocalHistorico || dashboardData.historico;
    const globalGoalIndex = refData.meses.indexOf('2026-06');
    let goalCost = null;
    let goalPeople = null;
    
    if (globalGoalIndex !== -1) {
        if (contractType === 'clt') {
            goalCost = refData.custo_clt[globalGoalIndex];
            goalPeople = refData.total_clt[globalGoalIndex];
        } else if (contractType === 'pj') {
            goalCost = refData.custo_pj[globalGoalIndex];
            goalPeople = refData.total_pj[globalGoalIndex];
        } else {
            goalCost = refData.custo_total[globalGoalIndex];
            goalPeople = refData.total_pessoas[globalGoalIndex];
        }
    }
    
    const bgColorsCost = dataCost.map((val) => {
        if (goalCost !== null && val > goalCost) return 'rgba(239, 68, 68, 0.8)'; // Red
        return 'rgba(16, 185, 129, 0.8)'; // Green
    });
    
    const bgColorsPeople = dataPeople.map((val) => {
        if (goalPeople !== null && val > goalPeople) return 'rgba(239, 68, 68, 0.8)'; // Red
        return 'rgba(16, 185, 129, 0.8)'; // Green
    });

    const dlConfig = {
        anchor: 'end',
        align: 'top',
        font: { weight: 'bold', size: 10 },
        color: '#4B5563'
    };

    // 1. Cost Chart
    const ctxCost = document.getElementById('histCostChart').getContext('2d');
    
    const costDatasets = [{
        type: 'bar',
        label: 'Custo Total (R$)',
        data: dataCost,
        backgroundColor: bgColorsCost,
        borderRadius: 4,
    }];
    
    let costPlugins = { 
        legend: { display: false },
        datalabels: {
            ...dlConfig,
            formatter: function(value) { return (value/1000).toFixed(0) + 'k'; }
        }
    };
    
    if (goalCost !== null) {
        costPlugins.annotation = {
            annotations: {
                goalLine: {
                    type: 'line',
                    yMin: goalCost,
                    yMax: goalCost,
                    borderColor: 'rgba(75, 85, 99, 0.8)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    label: {
                        content: 'Meta:\n' + (goalCost/1000).toFixed(0) + 'k',
                        display: true,
                        position: 'end',
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        color: '#4B5563',
                        font: { size: 10, weight: 'bold' },
                        padding: 4,
                        xAdjust: 30,
                        yAdjust: 0
                    }
                }
            }
        };
    }
    
    histCostChartInstance = new Chart(ctxCost, {
        data: {
            labels: labels,
            datasets: costDatasets
        },
        options: {
            clip: false,
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { top: 20, right: 80 } },
            plugins: costPlugins,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { callback: function(value) { return 'R$ ' + (value/1000) + 'k'; } }
                }
            }
        }
    });

    // 2. People Chart
    const ctxPeople = document.getElementById('histPeopleChart').getContext('2d');
    
    const peopleDatasets = [{
        type: 'bar',
        label: 'Quantidade de Funcionários',
        data: dataPeople,
        backgroundColor: bgColorsPeople,
        borderRadius: 4,
    }];
    
    let peoplePlugins = { 
        legend: { display: false },
        datalabels: dlConfig
    };
    
    if (goalPeople !== null) {
        peoplePlugins.annotation = {
            annotations: {
                goalLine: {
                    type: 'line',
                    yMin: goalPeople,
                    yMax: goalPeople,
                    borderColor: 'rgba(75, 85, 99, 0.8)',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    label: {
                        content: 'Meta:\n' + formatNumber(goalPeople),
                        display: true,
                        position: 'end',
                        backgroundColor: 'rgba(255, 255, 255, 0.9)',
                        color: '#4B5563',
                        font: { size: 10, weight: 'bold' },
                        padding: 4,
                        xAdjust: 30,
                        yAdjust: 0
                    }
                }
            }
        };
    }

    histPeopleChartInstance = new Chart(ctxPeople, {
        data: {
            labels: labels,
            datasets: peopleDatasets
        },
        options: {
            clip: false,
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { top: 20, right: 80 } },
            plugins: peoplePlugins,
            scales: { y: { beginAtZero: true } }
        }
    });

    // Calculate Global Turnover Percentages
    const globalTurnoverGeralList = historico.meses.map((mes, i) => {
        const adm = historico.entradas[i];
        const des = historico.saidas[i];
        const tf = historico.total_pessoas[i];
        const ti = i === 0 ? (tf - adm + des) : historico.total_pessoas[i - 1];
        return calcularTurnover(adm, des, ti, tf).geral;
    });

    // 3. Turnover Chart (Entradas vs Saídas)
    const ctxTurnover = document.getElementById('histTurnoverChart').getContext('2d');
    histTurnoverChartInstance = new Chart(ctxTurnover, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    type: 'line',
                    label: '% Turnover Geral',
                    data: globalTurnoverGeralList,
                    borderColor: 'rgba(99, 102, 241, 0.8)', // Indigo
                    backgroundColor: 'rgba(99, 102, 241, 0.8)',
                    borderWidth: 2,
                    yAxisID: 'y1',
                    datalabels: {
                        color: 'rgba(99, 102, 241, 1)',
                        align: 'top',
                        formatter: function(value) { return value + '%'; }
                    }
                },
                {
                    type: 'bar',
                    label: 'Entradas',
                    data: historico.entradas,
                    backgroundColor: 'rgba(16, 185, 129, 0.8)',
                    borderRadius: 4,
                    yAxisID: 'y',
                },
                {
                    type: 'bar',
                    label: 'Saídas',
                    data: historico.saidas,
                    backgroundColor: 'rgba(239, 68, 68, 0.8)',
                    borderRadius: 4,
                    yAxisID: 'y',
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: { padding: { top: 25 } },
            plugins: {
                legend: { position: 'bottom' },
                datalabels: { ...dlConfig, formatter: function(value, context) {
                    if (context.dataset.type === 'line') return value + '%';
                    return value;
                }}
            },
            scales: { 
                y: { beginAtZero: true, position: 'left' },
                y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, ticks: { callback: function(value) { return value + '%'; } } }
            }
        }
    });


};

// SPA Navigation Listeners
document.getElementById('btnVoltar').addEventListener('click', closeDetalhe360);

function closeDetalhe360() {
    document.getElementById('detalheContent').classList.add('hidden');
    document.getElementById('detalheContent').classList.remove('flex');
    
    document.getElementById('dashboardContent').classList.remove('hidden');
    document.getElementById('dashboardContent').classList.add('flex');
}

function openDetalhe360(agrupador) {
    if (!dashboardData || !dashboardData.historico_detalhado) return;
    
    // Now grouped by Agrupador 3
    const hist = dashboardData.historico_detalhado['agrupadores3'] ? dashboardData.historico_detalhado['agrupadores3'][agrupador] : null;
    if (!hist) return;
    
    window.currentAgrupador = agrupador;
    document.getElementById('detalheTitle').textContent = `Análise Detalhada: ${agrupador}`;
    
    // SPA Transition
    document.getElementById('dashboardContent').classList.add('hidden');
    document.getElementById('dashboardContent').classList.remove('flex');
    
    document.getElementById('detalheContent').classList.remove('hidden');
    document.getElementById('detalheContent').classList.add('flex');
    
    const monthNames = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"];
    const labels = hist.meses.map(mes => {
        const [year, month] = mes.split('-');
        return `${monthNames[parseInt(month) - 1]} ${year}`;
    });

    const dlConfig = {
        anchor: 'end', align: 'top', font: { weight: 'bold', size: 10 }, color: '#4B5563'
    };

    const cFilter = document.getElementById('contractFilter');
    const contractType = cFilter ? cFilter.value : '';
    
    let chartCusto = hist.custo_total.map(v => v === -1 ? null : v);
    let chartPessoas = hist.total_pessoas;
    
    if (contractType === 'clt') {
        chartCusto = hist.custo_clt.map(v => v === -1 ? null : v);
        chartPessoas = hist.total_clt;
    } else if (contractType === 'pj') {
        chartCusto = hist.custo_pj.map(v => v === -1 ? null : v);
        chartPessoas = hist.total_pj;
    }
    
    const chartPctCusto = hist.pct_custo.map(v => v === -1 ? null : v);

    // 1. Custo e Participação (Modal)
    if (modalCostChartInstance) modalCostChartInstance.destroy();
    modalCostChartInstance = new Chart(document.getElementById('modalCostChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    type: 'line',
                    label: '% do Total Empresa',
                    data: chartPctCusto,
                    borderColor: 'rgba(239, 68, 68, 0.8)',
                    backgroundColor: 'rgba(239, 68, 68, 0.8)',
                    borderWidth: 2,
                    yAxisID: 'y1',
                    datalabels: { display: false }
                },
                {
                    type: 'bar',
                    label: 'Custo (R$)',
                    data: chartCusto,
                    backgroundColor: 'rgba(16, 185, 129, 0.8)',
                    borderRadius: 4,
                    yAxisID: 'y',
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false, layout: { padding: { top: 25 } },
            plugins: { 
                legend: { position: 'bottom' },
                datalabels: { ...dlConfig, formatter: function(value, context) {
                    if (context.dataset.type === 'line') return '';
                    return (value/1000).toFixed(0) + 'k'; 
                }}
            },
            scales: {
                y: { beginAtZero: true, type: 'linear', position: 'left', ticks: { callback: function(value) { return 'R$ ' + (value/1000) + 'k'; } } },
                y1: { beginAtZero: true, type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { callback: function(value) { return value.toFixed(1) + '%'; } } }
            }
        }
    });

    // 2. Pessoas e Participação (Modal)
    if (modalPeopleChartInstance) modalPeopleChartInstance.destroy();
    modalPeopleChartInstance = new Chart(document.getElementById('modalPeopleChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    type: 'line',
                    label: '% do Total Empresa',
                    data: hist.pct_pessoas,
                    borderColor: 'rgba(245, 158, 11, 0.8)',
                    backgroundColor: 'rgba(245, 158, 11, 0.8)',
                    borderWidth: 2,
                    yAxisID: 'y1',
                    datalabels: { display: false }
                },
                {
                    type: 'bar',
                    label: 'Quantidade',
                    data: chartPessoas,
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderRadius: 4,
                    yAxisID: 'y',
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false, layout: { padding: { top: 25 } },
            plugins: { 
                legend: { position: 'bottom' },
                datalabels: { ...dlConfig, formatter: function(value, context) {
                    if (context.dataset.type === 'line') return '';
                    return value;
                }}
            },
            scales: {
                y: { beginAtZero: true, type: 'linear', position: 'left' },
                y1: { beginAtZero: true, type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { callback: function(value) { return value.toFixed(1) + '%'; } } }
            }
        }
    });

    // Calculate detailed Turnover Percentages
    const detalheTurnoverGeralList = hist.meses.map((mes, i) => {
        const adm = hist.entradas[i];
        const des = hist.saidas[i];
        const tf = hist.total_pessoas[i];
        const ti = i === 0 ? (tf - adm + des) : hist.total_pessoas[i - 1];
        return calcularTurnover(adm, des, ti, tf).geral;
    });

    // 3. Turnover Setorial (Modal)
    if (modalTurnoverChartInstance) modalTurnoverChartInstance.destroy();
    modalTurnoverChartInstance = new Chart(document.getElementById('modalTurnoverChart').getContext('2d'), {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    type: 'line',
                    label: '% Turnover Geral',
                    data: detalheTurnoverGeralList,
                    borderColor: 'rgba(99, 102, 241, 0.8)', // Indigo
                    backgroundColor: 'rgba(99, 102, 241, 0.8)',
                    borderWidth: 2,
                    yAxisID: 'y1',
                    datalabels: {
                        color: 'rgba(99, 102, 241, 1)',
                        align: 'top',
                        formatter: function(value) { return value + '%'; }
                    }
                },
                {
                    type: 'bar',
                    label: 'Entradas',
                    data: hist.entradas,
                    backgroundColor: 'rgba(16, 185, 129, 0.8)',
                    borderRadius: 4,
                    yAxisID: 'y',
                },
                {
                    type: 'bar',
                    label: 'Saídas',
                    data: hist.saidas,
                    backgroundColor: 'rgba(239, 68, 68, 0.8)',
                    borderRadius: 4,
                    yAxisID: 'y',
                }
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false, layout: { padding: { top: 25 } },
            plugins: { 
                legend: { position: 'bottom' }, 
                datalabels: { ...dlConfig, formatter: function(value, context) {
                    if (context.dataset.type === 'line') return value + '%';
                    return value;
                }} 
            },
            scales: { 
                y: { beginAtZero: true, position: 'left' },
                y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, ticks: { callback: function(value) { return value + '%'; } } }
            }
        }
    });

    // Build Historical Table
    const yearFilter = document.getElementById('yearFilter');
    const selectedYear = yearFilter ? yearFilter.value : '';
    const currentMonth = document.getElementById('monthFilter') ? document.getElementById('monthFilter').value : '';
    const activeFilterEl = document.getElementById('activePessoasFilter');
    const activeFilter = activeFilterEl ? activeFilterEl.value : 'all';
    const valorTypeFilterEl = document.getElementById('valorTypeFilter');
    const valorType = valorTypeFilterEl ? valorTypeFilterEl.value : 'custo';
    
    let pessoasArray = hist.pessoas_hist || [];
    if (contractType === 'clt' || contractType === 'pj') {
        pessoasArray = pessoasArray.filter(p => p.tipo_contrato === contractType);
    }
    
    if (activeFilter === 'active' || activeFilter === 'ativos') {
        pessoasArray = pessoasArray.filter(p => {
            const vals = valorType === 'remuneracao' ? p.remuneracoes : p.salarios;
            return vals[currentMonth] && vals[currentMonth] > 0;
        });
    }
    
    // Sort by name
    pessoasArray.sort((a, b) => a.nome.localeCompare(b.nome));
    
    const yearMonths = hist.meses.filter(m => m.startsWith(selectedYear)).sort();
    
    let theadHTML = `<tr>
        <th class="px-2 py-2 text-left text-xs font-semibold uppercase tracking-wider sticky top-0 left-0 bg-gray-900 z-30 min-w-[150px] max-w-[200px]">Nome / Identificador</th>
        <th class="px-2 py-2 text-center text-[10px] font-semibold uppercase tracking-wider sticky top-0 bg-gray-900 z-20">Tipo</th>`;
        
    yearMonths.forEach(m => {
        const [y, mm] = m.split('-');
        const isCurrent = (m === currentMonth);
        const colClass = isCurrent ? 'bg-indigo-700 font-bold' : 'bg-gray-900';
        theadHTML += `<th class="px-2 py-2 text-right text-[10px] font-semibold uppercase tracking-wider sticky top-0 z-20 ${colClass}">${monthNames[parseInt(mm)-1].substring(0,3)}</th>`;
    });
    
    theadHTML += `
        <th class="px-2 py-2 text-right text-[10px] font-semibold uppercase tracking-wider sticky top-0 z-20 bg-gray-800 leading-tight">Var.<br>Mês Ant.</th>
        <th class="px-2 py-2 text-right text-[10px] font-semibold uppercase tracking-wider sticky top-0 z-20 bg-gray-800 leading-tight">Var.<br>Ano</th>
    </tr>`;
    
    document.getElementById('histPessoasThead').innerHTML = theadHTML;
    
    const formatBRL = (val) => {
        if (val === -1) return 'Confidencial';
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(val);
    };
    
    let tbodyHTML = '';
    const monthTotals = {};
    yearMonths.forEach(m => monthTotals[m] = 0);
    
    pessoasArray.forEach(p => {
        let rowHTML = `<tr>
            <td class="px-2 py-2 text-xs font-medium text-gray-900 sticky left-0 bg-white z-10 border-r border-gray-100 min-w-[150px] max-w-[200px] whitespace-normal leading-tight">
                ${p.nome}<br><span class="text-[10px] text-gray-500 font-normal">${p.matricula}</span>
            </td>
            <td class="px-2 py-2 whitespace-nowrap text-[10px] text-center text-gray-500">${p.tipo_contrato.toUpperCase()}</td>`;
            
        let firstMonthVal = null;
        let prevMonthVal = null;
        let currentMonthVal = null;
        
        yearMonths.forEach(m => {
            const valsDict = valorType === 'remuneracao' ? (p.remuneracoes || p.salarios) : p.salarios;
            const val = valsDict[m] || 0;
            monthTotals[m] += val;
            
            if (val > 0 && firstMonthVal === null) firstMonthVal = val;
            if (m === currentMonth) currentMonthVal = val;
            if (m < currentMonth) prevMonthVal = val; // Assuming yearMonths is sorted, this gets the last one before current
            
            const isCurrent = (m === currentMonth);
            const bgClass = isCurrent ? 'bg-indigo-50 font-semibold text-indigo-900' : 'text-gray-700';
            
            if (dashboardData.show_salaries === false) {
                rowHTML += `<td class="px-2 py-2 whitespace-nowrap text-xs text-right ${bgClass}">******</td>`;
            } else {
                rowHTML += `<td class="px-2 py-2 whitespace-nowrap text-xs text-right ${bgClass}">${val > 0 ? formatBRL(val) : '-'}</td>`;
            }
        });
        
        // Variações (only if current month has value or if we want to show drop to 0)
        // If current month has 0, and prev has value, it's a drop to 0.
        prevMonthVal = prevMonthVal || 0;
        firstMonthVal = firstMonthVal || 0;
        currentMonthVal = currentMonthVal || 0;
        
        const varPrev = currentMonthVal - prevMonthVal;
        const varAno = currentMonthVal - firstMonthVal;
        
        const varColor = (val) => {
            if (val > 1) return 'text-red-600 font-medium';
            if (val < -1) return 'text-emerald-600 font-medium';
            return 'text-gray-400';
        };
        const varSign = (val) => val > 0 ? '+' : '';
        
        if (dashboardData.show_salaries === false) {
            rowHTML += `
                <td class="px-2 py-2 whitespace-nowrap text-xs text-right text-gray-400">***</td>
                <td class="px-2 py-2 whitespace-nowrap text-xs text-right text-gray-400">***</td>
            </tr>`;
        } else {
            rowHTML += `
                <td class="px-2 py-2 whitespace-nowrap text-xs text-right ${varColor(varPrev)}">${varPrev !== 0 ? varSign(varPrev) + formatBRL(varPrev) : '-'}</td>
                <td class="px-2 py-2 whitespace-nowrap text-xs text-right ${varColor(varAno)}">${varAno !== 0 ? varSign(varAno) + formatBRL(varAno) : '-'}</td>
            </tr>`;
        }
        
        tbodyHTML += rowHTML;
    });
    
    if (pessoasArray.length === 0) {
        tbodyHTML = `<tr><td colspan="${yearMonths.length + 4}" class="px-4 py-8 text-center text-gray-500">Nenhum dado encontrado para os filtros atuais.</td></tr>`;
    }
    
    let totalRowHTML = `<tr class="bg-gray-100">
        <td class="px-2 py-2 text-xs font-bold text-gray-900 sticky left-0 bg-gray-100 z-10 border-r border-gray-200 border-b border-gray-300 min-w-[150px] max-w-[200px] whitespace-normal">TOTAL</td>
        <td class="px-2 py-2 whitespace-nowrap text-[10px] font-bold text-center text-gray-900 border-b border-gray-300">-</td>`;
        
    let prevTotal = null;
    let firstTotalVal = null;
    let prevTotalVal = null;
    let currentTotalVal = null;
    
    yearMonths.forEach(m => {
        const val = monthTotals[m];
        const isCurrent = (m === currentMonth);
        
        if (val > 0 && firstTotalVal === null) firstTotalVal = val;
        if (isCurrent) currentTotalVal = val;
        if (m < currentMonth) prevTotalVal = val;
        
        let colorClass = isCurrent ? 'bg-indigo-100 text-indigo-900' : 'text-gray-900';
        if (prevTotal !== null && val > prevTotal + 1) { // +1 to avoid floating point issues
            colorClass += ' text-red-600';
        } else if (prevTotal !== null && val < prevTotal - 1) {
            colorClass += ' text-emerald-600';
        }
        
        totalRowHTML += `<td class="px-2 py-2 whitespace-nowrap text-xs text-right font-bold border-b border-gray-300 ${colorClass}">${formatBRL(val)}</td>`;
        prevTotal = val;
    });
    
    prevTotalVal = prevTotalVal || 0;
    firstTotalVal = firstTotalVal || 0;
    currentTotalVal = currentTotalVal || 0;
    
    const varTotalPrev = currentTotalVal - prevTotalVal;
    const varTotalAno = currentTotalVal - firstTotalVal;
    
    const varTotalColor = (val) => {
        if (val > 1) return 'text-red-600 font-bold';
        if (val < -1) return 'text-emerald-600 font-bold';
        return 'text-gray-600 font-bold';
    };
    const varTotalSign = (val) => val > 0 ? '+' : '';
    
    totalRowHTML += `
        <td class="px-2 py-1 whitespace-nowrap text-[11px] text-right border-b border-gray-300 ${varTotalColor(varTotalPrev)}">${varTotalPrev !== 0 ? varTotalSign(varTotalPrev) + formatBRL(varTotalPrev) : '-'}</td>
        <td class="px-2 py-1 whitespace-nowrap text-[11px] text-right border-b border-gray-300 ${varTotalColor(varTotalAno)}">${varTotalAno !== 0 ? varTotalSign(varTotalAno) + formatBRL(varTotalAno) : '-'}</td>
    </tr>`;
    
    if (pessoasArray.length > 0) {
        document.getElementById('histPessoasBody').innerHTML = totalRowHTML + tbodyHTML;
        document.getElementById('histPessoasTfoot').innerHTML = '';
    } else {
        document.getElementById('histPessoasTfoot').innerHTML = '';
        document.getElementById('histPessoasBody').innerHTML = tbodyHTML;
    }
}
