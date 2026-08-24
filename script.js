/**
 * script.js - Frontend logic for Controlador de Gastos
 * Handles UI interactions, DOM updates, and pywebview.api calls.
 */

// ==========================================================================
// STATE
// ==========================================================================
let currentTreeMonth = null;
let currentTreeCategory = null;
let lastParsedData = [];

// ==========================================================================
// NAVIGATION
// ==========================================================================

document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const target = btn.dataset.target;
        switchView(target);

        // Update active state
        document.querySelectorAll('.nav-btn').forEach(b => {
            b.classList.remove('bg-primary-50', 'text-primary-700', 'dark:bg-primary-900/30', 'dark:text-primary-300', 'font-medium');
            b.classList.add('text-slate-600', 'dark:text-slate-300');
        });
        btn.classList.remove('text-slate-600', 'dark:text-slate-300');
        btn.classList.add('bg-primary-50', 'text-primary-700', 'dark:bg-primary-900/30', 'dark:text-primary-300', 'font-medium');
    });
});

function switchView(viewId) {
    document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
    document.getElementById(viewId).classList.remove('hidden');

    // Load data when entering specific views
    if (viewId === 'view-dashboard') loadDashboard();
    if (viewId === 'view-tree') showMonthsList();
    if (viewId === 'view-register') loadCategoryList();
}

// ==========================================================================
// THEME (persisted via Python API — survives app restarts)
// ==========================================================================

const themeBtn = document.getElementById('btn-theme');
const themeIcon = document.getElementById('icon-theme');

async function initTheme() {
    try {
        const res = await pywebview.api.get_theme();
        const savedTheme = res.success ? res.theme : 'light';
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        const isDark = savedTheme === 'dark' || (!savedTheme && prefersDark);

        if (isDark) {
            document.documentElement.classList.add('dark');
            themeIcon.classList.replace('ph-moon', 'ph-sun');
        } else {
            document.documentElement.classList.remove('dark');
            themeIcon.classList.replace('ph-sun', 'ph-moon');
        }
    } catch (e) {
        console.error('Failed to load theme:', e);
    }
}

themeBtn.addEventListener('click', async () => {
    const isDark = document.documentElement.classList.toggle('dark');
    themeIcon.classList.toggle('ph-moon');
    themeIcon.classList.toggle('ph-sun');

    try {
        await pywebview.api.set_theme(isDark ? 'dark' : 'light');
    } catch (e) {
        console.error('Failed to save theme:', e);
    }
});

// ==========================================================================
// TOAST NOTIFICATIONS
// ==========================================================================

function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');

    const colors = {
        success: 'bg-emerald-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        warning: 'bg-amber-500'
    };

    const icons = {
        success: 'ph-check-circle',
        error: 'ph-x-circle',
        info: 'ph-info',
        warning: 'ph-warning'
    };

    toast.className = `${colors[type]} text-white px-5 py-3 rounded-xl shadow-lg flex items-center gap-3 transform translate-x-full transition-transform duration-300 pointer-events-auto min-w-[280px]`;
    toast.innerHTML = `<i class="ph ${icons[type]} text-xl"></i><span class="font-medium">${message}</span>`;

    container.appendChild(toast);

    // Animate in
    requestAnimationFrame(() => toast.classList.remove('translate-x-full'));

    // Remove after 3s
    setTimeout(() => {
        toast.classList.add('translate-x-full', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ==========================================================================
// CATEGORY DATALIST
// ==========================================================================

async function loadCategoryList() {
    try {
        const res = await pywebview.api.get_all_categories();
        if (res.success) {
            const datalist = document.getElementById('category-list');
            datalist.innerHTML = '';
            res.data.forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat;
                datalist.appendChild(opt);
            });
        }
    } catch (e) {
        console.error('Failed to load categories:', e);
    }
}

// ==========================================================================
// DASHBOARD
// ==========================================================================

async function loadDashboard() {
    try {
        const res = await pywebview.api.get_months_summary();
        const tbody = document.getElementById('dash-months-body');
        tbody.innerHTML = '';

        if (!res.success || !res.data.length) {
            tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400">Nenhuma despesa registrada ainda.</td></tr>`;
            document.getElementById('dash-current-month').textContent = 'R$ 0,00';
            document.getElementById('dash-top-category').textContent = '-';
            document.getElementById('dash-total-count').textContent = '0';
            return;
        }

        let totalCount = 0;
        let currentMonthTotal = 0;

        const now = new Date();
        const currentMonthStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;

        res.data.forEach(row => {
            totalCount += row.count;
            if (row.month === currentMonthStr) {
                currentMonthTotal = row.total;
            }

            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-800/50 transition';
            tr.innerHTML = `
                <td class="px-6 py-4 font-medium">${formatMonth(row.month)}</td>
                <td class="px-6 py-4 text-slate-500 dark:text-slate-400">${row.count} despesa(s)</td>
                <td class="px-6 py-4 text-right font-semibold text-primary-600 dark:text-primary-400">${formatCurrency(row.total)}</td>
                <td class="px-6 py-4 text-right">
                    <button onclick="viewMonthCategories('${row.month}')" class="text-sm text-primary-600 hover:underline">Ver detalhes &rarr;</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        document.getElementById('dash-current-month').textContent = formatCurrency(currentMonthTotal);
        document.getElementById('dash-total-count').textContent = totalCount.toString();

        // Find top category for current month
        if (currentMonthTotal > 0) {
            const catRes = await pywebview.api.get_categories_by_month(currentMonthStr);
            if (catRes.success && catRes.data.length) {
                document.getElementById('dash-top-category').textContent = 
                    `${catRes.data[0].category} (${formatCurrency(catRes.data[0].total)})`;
            } else {
                document.getElementById('dash-top-category').textContent = '-';
            }
        } else {
            document.getElementById('dash-top-category').textContent = '-';
        }
    } catch (e) {
        console.error('Dashboard load error:', e);
        showToast('Erro ao carregar dashboard', 'error');
    }
}

// ==========================================================================
// SINGLE REGISTRATION
// ==========================================================================

async function submitSingleExpense() {
    const category = document.getElementById('reg-category').value.trim();
    const description = document.getElementById('reg-description').value.trim();
    const amount = parseFloat(document.getElementById('reg-amount').value);

    if (!category || !description || isNaN(amount) || amount <= 0) {
        showToast('Preencha todos os campos corretamente.', 'warning');
        return;
    }

    try {
        const res = await pywebview.api.add_expense(category, description, amount);
        if (res.success) {
            showToast(res.message, 'success');
            clearRegisterForm();
            loadCategoryList();
            loadBalance();  // atualiza saldo no header
        } else {
            showToast(res.message, 'error');
        }
    } catch (e) {
        showToast('Erro de comunicacao com o backend.', 'error');
        console.error(e);
    }
}

function clearRegisterForm() {
    document.getElementById('reg-category').value = '';
    document.getElementById('reg-description').value = '';
    document.getElementById('reg-amount').value = '';
}

// ==========================================================================
// BULK REGISTRATION
// ==========================================================================

async function submitBulkExpenses() {
    const category = document.getElementById('bulk-category').value.trim();
    const lines = document.getElementById('bulk-lines').value;

    if (!category) {
        showToast('Informe a categoria.', 'warning');
        return;
    }
    if (!lines.trim()) {
        showToast('Cole pelo menos uma linha de despesa.', 'warning');
        return;
    }

    try {
        const res = await pywebview.api.add_expenses_bulk(category, lines);
        const resultDiv = document.getElementById('bulk-result');
        resultDiv.classList.remove('hidden');

        if (res.success) {
            let html = `<div class="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl p-4 text-sm">`;
            html += `<p class="font-semibold text-emerald-800 dark:text-emerald-300"><i class="ph ph-check-circle mr-1"></i> ${res.message}</p>`;

            if (res.errors && res.errors.length) {
                html += `<div class="mt-3 space-y-1">`;
                html += `<p class="font-medium text-amber-700 dark:text-amber-400">Erros encontrados:</p>`;
                res.errors.forEach(err => {
                    html += `<p class="text-xs text-red-600 dark:text-red-400">${err}</p>`;
                });
                html += `</div>`;
            }
            html += `</div>`;
            resultDiv.innerHTML = html;
            showToast(res.message, 'success');
            loadCategoryList();
            loadBalance();  // atualiza saldo no header
        } else {
            resultDiv.innerHTML = `<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 text-sm text-red-700 dark:text-red-300">${res.message}</div>`;
            showToast(res.message, 'error');
        }
    } catch (e) {
        showToast('Erro de comunicacao com o backend.', 'error');
        console.error(e);
    }
}

// ==========================================================================
// EXPENSES TREE (Drill-down)
// ==========================================================================

async function showMonthsList() {
    currentTreeMonth = null;
    currentTreeCategory = null;
    updateBreadcrumb();

    document.getElementById('tree-months').classList.remove('hidden');
    document.getElementById('tree-categories').classList.add('hidden');
    document.getElementById('tree-expenses').classList.add('hidden');

    const grid = document.getElementById('tree-months');
    grid.innerHTML = '<div class="col-span-full text-center py-12 text-slate-400"><i class="ph ph-spinner animate-spin text-3xl"></i></div>';

    try {
        const res = await pywebview.api.get_months_summary();
        grid.innerHTML = '';

        if (!res.success || !res.data.length) {
            grid.innerHTML = `<div class="col-span-full text-center py-12 text-slate-400">Nenhuma despesa registrada.</div>`;
            return;
        }

        res.data.forEach(row => {
            const card = document.createElement('div');
            card.className = 'bg-card-light dark:bg-card-dark rounded-2xl p-5 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md hover:border-primary-300 dark:hover:border-primary-700 cursor-pointer transition-all';
            card.onclick = () => viewMonthCategories(row.month);
            card.innerHTML = `
                <div class="flex items-center justify-between mb-3">
                    <span class="text-lg font-bold">${formatMonth(row.month)}</span>
                    <i class="ph ph-caret-right text-slate-400"></i>
                </div>
                <div class="flex items-center justify-between text-sm">
                    <span class="text-slate-500 dark:text-slate-400">${row.count} despesa(s)</span>
                    <span class="font-semibold text-primary-600 dark:text-primary-400">${formatCurrency(row.total)}</span>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        grid.innerHTML = `<div class="col-span-full text-center py-12 text-red-400">Erro ao carregar meses.</div>`;
        console.error(e);
    }
}

async function viewMonthCategories(month) {
    currentTreeMonth = month;
    currentTreeCategory = null;
    updateBreadcrumb();

    // BUG FIX: Navegar para a view da arvore antes de carregar os dados
    switchView('view-tree');
    // Atualiza o botao ativo no sidebar
    document.querySelectorAll('.nav-btn').forEach(b => {
        b.classList.remove('bg-primary-50', 'text-primary-700', 'dark:bg-primary-900/30', 'dark:text-primary-300', 'font-medium');
        b.classList.add('text-slate-600', 'dark:text-slate-300');
    });
    const treeBtn = document.querySelector('[data-target="view-tree"]');
    if (treeBtn) {
        treeBtn.classList.remove('text-slate-600', 'dark:text-slate-300');
        treeBtn.classList.add('bg-primary-50', 'text-primary-700', 'dark:bg-primary-900/30', 'dark:text-primary-300', 'font-medium');
    }

    document.getElementById('tree-months').classList.add('hidden');
    document.getElementById('tree-categories').classList.remove('hidden');
    document.getElementById('tree-expenses').classList.add('hidden');

    document.getElementById('tree-cat-title').textContent = formatMonth(month);
    const grid = document.getElementById('tree-categories-grid');
    grid.innerHTML = '<div class="col-span-full text-center py-12 text-slate-400"><i class="ph ph-spinner animate-spin text-3xl"></i></div>';

    try {
        const res = await pywebview.api.get_categories_by_month(month);
        grid.innerHTML = '';

        if (!res.success || !res.data.length) {
            grid.innerHTML = `<div class="col-span-full text-center py-12 text-slate-400">Nenhuma categoria encontrada.</div>`;
            return;
        }

        res.data.forEach(row => {
            const card = document.createElement('div');
            card.className = 'bg-card-light dark:bg-card-dark rounded-2xl p-5 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md hover:border-primary-300 dark:hover:border-primary-700 cursor-pointer transition-all';
            card.onclick = () => viewCategoryExpenses(month, row.category);
            card.innerHTML = `
                <div class="flex items-center justify-between mb-3">
                    <span class="text-lg font-bold">${row.category}</span>
                    <i class="ph ph-caret-right text-slate-400"></i>
                </div>
                <div class="flex items-center justify-between text-sm">
                    <span class="text-slate-500 dark:text-slate-400">${row.count} item(ns)</span>
                    <span class="font-semibold text-primary-600 dark:text-primary-400">${formatCurrency(row.total)}</span>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (e) {
        grid.innerHTML = `<div class="col-span-full text-center py-12 text-red-400">Erro ao carregar categorias.</div>`;
        console.error(e);
    }
}

function showCategoriesForMonth() {
    if (currentTreeMonth) {
        viewMonthCategories(currentTreeMonth);
    }
}

async function viewCategoryExpenses(month, category) {
    currentTreeCategory = category;
    updateBreadcrumb();

    document.getElementById('tree-months').classList.add('hidden');
    document.getElementById('tree-categories').classList.add('hidden');
    document.getElementById('tree-expenses').classList.remove('hidden');

    document.getElementById('tree-exp-title').textContent = `${formatMonth(month)} > ${category}`;
    const tbody = document.getElementById('tree-expenses-body');
    tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400"><i class="ph ph-spinner animate-spin text-2xl"></i></td></tr>';

    try {
        const res = await pywebview.api.get_expenses_by_month_and_category(month, category);
        tbody.innerHTML = '';

        if (!res.success || !res.data.length) {
            tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400">Nenhuma despesa encontrada.</td></tr>`;
            return;
        }

        res.data.forEach(exp => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-800/50 transition';
            tr.innerHTML = `
                <td class="px-6 py-4 text-sm text-slate-500 dark:text-slate-400">${formatDateTime(exp.created_at)}</td>
                <td class="px-6 py-4 font-medium">${escapeHtml(exp.description)}</td>
                <td class="px-6 py-4 text-right font-semibold">${formatCurrency(exp.amount)}</td>
                <td class="px-6 py-4 text-center">
                    <div class="flex items-center justify-center gap-2">
                        <button onclick="openEditModal(${exp.id})" class="p-2 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 transition" title="Editar">
                            <i class="ph ph-pencil-simple text-lg"></i>
                        </button>
                        <button onclick="openDeleteModal(${exp.id})" class="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition" title="Excluir">
                            <i class="ph ph-trash text-lg"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-red-400">Erro ao carregar despesas.</td></tr>`;
        console.error(e);
    }
}

function updateBreadcrumb() {
    const bc = document.getElementById('tree-breadcrumb');
    let html = `<button onclick="showMonthsList()" class="hover:text-primary-600 dark:hover:text-primary-400 transition font-medium">Meses</button>`;

    if (currentTreeMonth) {
        html += ` <span class="text-slate-300">/</span> <button onclick="showCategoriesForMonth()" class="hover:text-primary-600 dark:hover:text-primary-400 transition">${formatMonth(currentTreeMonth)}</button>`;
    }
    if (currentTreeCategory) {
        html += ` <span class="text-slate-300">/</span> <span class="text-slate-700 dark:text-slate-200 font-medium">${escapeHtml(currentTreeCategory)}</span>`;
    }

    bc.innerHTML = html;
}

// ==========================================================================
// EDIT MODAL
// ==========================================================================

async function openEditModal(id) {
    try {
        const res = await pywebview.api.get_expense(id);
        if (!res.success || !res.data) {
            showToast('Despesa nao encontrada.', 'error');
            return;
        }

        document.getElementById('edit-id').value = res.data.id;
        document.getElementById('edit-category').value = res.data.category;
        document.getElementById('edit-description').value = res.data.description;
        document.getElementById('edit-amount').value = res.data.amount;

        document.getElementById('edit-modal').classList.remove('hidden');
        document.getElementById('edit-modal').classList.add('flex');
    } catch (e) {
        showToast('Erro ao carregar despesa.', 'error');
        console.error(e);
    }
}

function closeEditModal() {
    document.getElementById('edit-modal').classList.add('hidden');
    document.getElementById('edit-modal').classList.remove('flex');
}

async function submitEdit() {
    const id = parseInt(document.getElementById('edit-id').value);
    const category = document.getElementById('edit-category').value.trim();
    const description = document.getElementById('edit-description').value.trim();
    const amount = parseFloat(document.getElementById('edit-amount').value);

    if (!category || !description || isNaN(amount) || amount <= 0) {
        showToast('Preencha todos os campos corretamente.', 'warning');
        return;
    }

    try {
        const res = await pywebview.api.update_expense(id, category, description, amount);
        if (res.success) {
            showToast(res.message, 'success');
            closeEditModal();
            // Refresh current view
            if (currentTreeMonth && currentTreeCategory) {
                viewCategoryExpenses(currentTreeMonth, currentTreeCategory);
            } else if (currentTreeMonth) {
                viewMonthCategories(currentTreeMonth);
            }
            loadDashboard();
        } else {
            showToast(res.message, 'error');
        }
    } catch (e) {
        showToast('Erro ao atualizar.', 'error');
        console.error(e);
    }
}

// ==========================================================================
// DELETE MODAL
// ==========================================================================

function openDeleteModal(id) {
    document.getElementById('delete-id').value = id;
    document.getElementById('delete-modal').classList.remove('hidden');
    document.getElementById('delete-modal').classList.add('flex');
}

function closeDeleteModal() {
    document.getElementById('delete-modal').classList.add('hidden');
    document.getElementById('delete-modal').classList.remove('flex');
}

async function confirmDelete() {
    const id = parseInt(document.getElementById('delete-id').value);

    try {
        const res = await pywebview.api.delete_expense(id);
        if (res.success) {
            showToast(res.message, 'success');
            closeDeleteModal();
            // Refresh current view
            if (currentTreeMonth && currentTreeCategory) {
                viewCategoryExpenses(currentTreeMonth, currentTreeCategory);
            } else if (currentTreeMonth) {
                viewMonthCategories(currentTreeMonth);
            } else {
                showMonthsList();
            }
            loadDashboard();
        } else {
            showToast(res.message, 'error');
        }
    } catch (e) {
        showToast('Erro ao excluir.', 'error');
        console.error(e);
    }
}

// ==========================================================================
// RAW TEXT PARSER
// ==========================================================================

async function parseRawText() {
    const rawText = document.getElementById('raw-text').value.trim();

    if (!rawText) {
        showToast('Cole algum texto para analisar.', 'warning');
        return;
    }

    try {
        const res = await pywebview.api.parse_raw_text(rawText);
        const previewDiv = document.getElementById('raw-preview');
        const errorsDiv = document.getElementById('raw-errors');
        const listDiv = document.getElementById('raw-preview-list');

        previewDiv.classList.remove('hidden');
        listDiv.innerHTML = '';
        lastParsedData = res.parsed || [];

        if (res.parsed && res.parsed.length) {
            res.parsed.forEach((item, idx) => {
                const row = document.createElement('div');
                row.className = 'flex items-center justify-between p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700';
                row.innerHTML = `
                    <div class="flex-1 min-w-0">
                        <p class="font-medium truncate">${escapeHtml(item.description)}</p>
                        <p class="text-xs text-slate-400 truncate">${escapeHtml(item.raw)}</p>
                    </div>
                    <span class="font-semibold text-primary-600 dark:text-primary-400 ml-4">${formatCurrency(item.amount)}</span>
                `;
                listDiv.appendChild(row);
            });
        } else {
            listDiv.innerHTML = `<p class="text-slate-400 text-center py-4">Nenhum item encontrado.</p>`;
        }

        if (res.errors && res.errors.length) {
            errorsDiv.classList.remove('hidden');
            errorsDiv.innerHTML = `<p class="font-medium mb-1">Erros:</p>` + 
                res.errors.map(e => `<p class="text-xs">${escapeHtml(e)}</p>`).join('');
        } else {
            errorsDiv.classList.add('hidden');
        }

        showToast(res.message, res.parsed.length ? 'success' : 'warning');
    } catch (e) {
        showToast('Erro ao analisar texto.', 'error');
        console.error(e);
    }
}

async function saveParsedExpenses() {
    const category = document.getElementById('raw-category').value.trim();

    if (!category) {
        showToast('Informe uma categoria.', 'warning');
        return;
    }
    if (!lastParsedData.length) {
        showToast('Nenhum item para salvar.', 'warning');
        return;
    }

    try {
        const res = await pywebview.api.save_parsed_expenses(category, lastParsedData);
        if (res.success) {
            showToast(res.message, 'success');
            document.getElementById('raw-text').value = '';
            document.getElementById('raw-preview').classList.add('hidden');
            document.getElementById('raw-errors').classList.add('hidden');
            lastParsedData = [];
            loadCategoryList();
            loadBalance();  // atualiza saldo no header
        } else {
            showToast(res.message, 'error');
        }
    } catch (e) {
        showToast('Erro ao salvar.', 'error');
        console.error(e);
    }
}

// ==========================================================================
// BALANCE / SALDO & SALARIO
// ==========================================================================

async function loadBalance() {
    try {
        const res = await pywebview.api.get_balance();
        if (res.success) {
            document.getElementById('header-balance').textContent = formatCurrency(res.balance);
        }
    } catch (e) {
        console.error('Erro ao carregar saldo:', e);
    }
}

async function openBalanceModal() {
    document.getElementById('balance-modal').classList.remove('hidden');
    document.getElementById('balance-modal').classList.add('flex');
    // Carrega valores salvos ao abrir
    await loadBalanceModalValues();
    document.getElementById('balance-input').focus();
}

function closeBalanceModal() {
    document.getElementById('balance-modal').classList.add('hidden');
    document.getElementById('balance-modal').classList.remove('flex');
}

async function loadBalanceModalValues() {
    try {
        const balRes = await pywebview.api.get_balance();
        const salRes = await pywebview.api.get_salary();
        if (balRes.success) {
            document.getElementById('balance-input').value = balRes.balance !== 0 ? balRes.balance : '';
        }
        if (salRes.success) {
            document.getElementById('salary-input').value = salRes.salary !== 0 ? salRes.salary : '';
            // Mostra o salario salvo em texto para confirmacao
            const salaryDisplay = document.getElementById('salary-display');
            if (salaryDisplay) {
                salaryDisplay.textContent = salRes.salary > 0 
                    ? `Salario atual: ${formatCurrency(salRes.salary)}` 
                    : 'Nenhum salario configurado';
            }
        }
    } catch (e) {
        console.error('Erro ao carregar valores do modal:', e);
    }
}

async function submitBalance() {
    const balanceVal = document.getElementById('balance-input').value;
    const salaryVal = document.getElementById('salary-input').value;
    
    const balance = balanceVal === '' ? 0 : parseFloat(balanceVal);
    const salary = salaryVal === '' ? 0 : parseFloat(salaryVal);
    
    if (isNaN(balance) || isNaN(salary)) {
        showToast('Informe valores validos.', 'warning');
        return;
    }
    
    try {
        // Salva saldo
        const balRes = await pywebview.api.set_balance(balance);
        // Salva salario
        const salRes = await pywebview.api.set_salary(salary);
        
        if (balRes.success && salRes.success) {
            showToast('Saldo e salario atualizados!', 'success');
            document.getElementById('header-balance').textContent = formatCurrency(balRes.balance);
            closeBalanceModal();
        } else {
            showToast(balRes.message || salRes.message, 'error');
        }
    } catch (e) {
        showToast('Erro ao salvar.', 'error');
        console.error(e);
    }
}

// ==========================================================================
// UTILITIES
// ==========================================================================

function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value || 0);
}

function formatMonth(yyyymm) {
    const [year, month] = yyyymm.split('-');
    const date = new Date(year, month - 1, 1);
    return date.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
}

function formatDateTime(isoString) {
    if (!isoString) return '-';
    const date = new Date(isoString.replace(' ', 'T'));
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = String(date.getFullYear()).slice(-2);
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${day}/${month}/${year} ${hours}:${minutes}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==========================================================================
// KEYBOARD SHORTCUTS
// ==========================================================================

document.addEventListener('keydown', (e) => {
    // Escape closes modals
    if (e.key === 'Escape') {
        closeEditModal();
        closeDeleteModal();
        closeBalanceModal();
    }
});

// ==========================================================================
// INIT
// ==========================================================================

function waitForPyWebViewAPI(callback, maxRetries = 50) {
    let retries = 0;
    const interval = setInterval(() => {
        if (typeof pywebview !== 'undefined' && pywebview.api) {
            clearInterval(interval);
            callback();
        } else {
            retries++;
            if (retries >= maxRetries) {
                clearInterval(interval);
                console.error('pywebview.api nao ficou disponivel a tempo.');
                showToast('Erro de inicializacao do app.', 'error');
            }
        }
    }, 100); // checa a cada 100ms, timeout de 5s
}

document.addEventListener('DOMContentLoaded', () => {
    // Aguarda pywebview.api estar pronto antes de chamar QUALQUER metodo do backend
    waitForPyWebViewAPI(() => {
        initTheme();
        loadBalance();      // carrega saldo no header
        loadDashboard();
        loadCategoryList();
    });
});
