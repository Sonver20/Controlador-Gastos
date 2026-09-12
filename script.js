/**
 * script.js - Frontend logic for Controlador de Gastos
 * Handles UI interactions, DOM updates, and pywebview.api calls.
 */

// ==========================================================================
// STATE
// ==========================================================================
let currentTreeMonth = null;
let currentTreeCategory = null;
let currentTreeSubcategory = null;          // null = sem filtro, "" = balde "sem subcategoria", "X" = subcategoria especifica
let currentTreeHasSubcategoryLevel = false; // true se a grade de subcategorias foi exibida para a categoria atual
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
    if (viewId === 'view-register') {
        loadCategoryList();
        loadSubcategoryList();
        if (document.getElementById('reg-products-list').children.length === 0) {
            addProductRow();
        }
    }
    if (viewId === 'view-calendar') renderSalaryCalendar();
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

async function loadSubcategoryList() {
    try {
        const res = await pywebview.api.get_all_subcategories();
        if (res.success) {
            const datalist = document.getElementById('subcategory-list');
            datalist.innerHTML = '';
            res.data.forEach(sub => {
                const opt = document.createElement('option');
                opt.value = sub;
                datalist.appendChild(opt);
            });
        }
    } catch (e) {
        console.error('Failed to load subcategories:', e);
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

// ==========================================================================
// NOVA DESPESA - lista de produtos (unifica o antigo "Cadastro em Massa":
// uma categoria/subcategoria compartilhada + N produtos com nome, preco
// unitario e quantidade controlada por um stepper +/-)
// ==========================================================================

let productRowCounter = 0;

function addProductRow() {
    const list = document.getElementById('reg-products-list');
    const rowId = `prow-${++productRowCounter}`;
    const row = document.createElement('div');
    row.className = 'product-row flex flex-col sm:flex-row gap-3 items-stretch sm:items-center bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 border border-slate-200 dark:border-slate-700';
    row.dataset.rowId = rowId;
    row.innerHTML = `
        <input type="text" class="product-name flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 outline-none transition text-sm"
            placeholder="Nome do produto" oninput="updateProductsGrandTotal()">
        <input type="number" class="product-price w-full sm:w-28 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 outline-none transition text-sm"
            placeholder="Preço" step="0.01" min="0" oninput="updateProductsGrandTotal()">
        <div class="flex items-center gap-2 justify-center">
            <button type="button" onclick="stepProductQty('${rowId}', -1)"
                class="w-8 h-8 shrink-0 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition font-bold">-</button>
            <input type="number" class="product-qty w-16 text-center px-2 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 outline-none transition text-sm"
                value="1" step="0.001" min="0.001" oninput="updateProductsGrandTotal()">
            <button type="button" onclick="stepProductQty('${rowId}', 1)"
                class="w-8 h-8 shrink-0 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition font-bold">+</button>
        </div>
        <span class="product-subtotal text-sm font-semibold text-slate-600 dark:text-slate-300 w-24 text-right shrink-0">R$ 0,00</span>
        <button type="button" onclick="removeProductRow('${rowId}')"
            class="text-red-500 hover:text-red-700 dark:hover:text-red-400 p-1 shrink-0" title="Remover produto">
            <i class="ph ph-trash text-lg"></i>
        </button>
    `;
    list.appendChild(row);
    row.querySelector('.product-name').focus();
    updateProductsGrandTotal();
}

function removeProductRow(rowId) {
    const list = document.getElementById('reg-products-list');
    const row = list.querySelector(`[data-row-id="${rowId}"]`);
    if (row) row.remove();
    // Sempre deixa pelo menos uma linha disponivel
    if (list.children.length === 0) addProductRow();
    updateProductsGrandTotal();
}

function stepProductQty(rowId, delta) {
    const row = document.getElementById('reg-products-list').querySelector(`[data-row-id="${rowId}"]`);
    if (!row) return;
    const qtyInput = row.querySelector('.product-qty');
    let qty = parseFloat(qtyInput.value) || 0;
    qty = Math.max(0.001, qty + delta);
    // Arredonda para evitar sobra de ponto flutuante (ex: 1.9999999999)
    qtyInput.value = Math.round(qty * 1000) / 1000;
    updateProductsGrandTotal();
}

function updateProductsGrandTotal() {
    const rows = document.querySelectorAll('#reg-products-list .product-row');
    let grandTotal = 0;
    rows.forEach(row => {
        const price = parseFloat(row.querySelector('.product-price').value) || 0;
        const qty = parseFloat(row.querySelector('.product-qty').value) || 0;
        const subtotal = price * qty;
        row.querySelector('.product-subtotal').textContent = formatCurrency(subtotal);
        grandTotal += subtotal;
    });
    document.getElementById('reg-grand-total').textContent = formatCurrency(grandTotal);
}

async function submitProductsExpense() {
    const category = document.getElementById('reg-category').value.trim();
    const subcategory = document.getElementById('reg-subcategory').value.trim();

    if (!category) {
        showToast('Informe a categoria.', 'warning');
        return;
    }

    const rows = document.querySelectorAll('#reg-products-list .product-row');
    const products = [];
    let hasInvalidRow = false;

    rows.forEach(row => {
        const name = row.querySelector('.product-name').value.trim();
        const priceStr = row.querySelector('.product-price').value.trim();
        const qtyStr = row.querySelector('.product-qty').value.trim();

        // Linha totalmente vazia (usuário clicou em "+" e não usou) -- ignora
        if (!name && !priceStr) return;

        const price = parseFloat(priceStr);
        const qty = parseFloat(qtyStr);
        if (!name || !priceStr || isNaN(price) || price <= 0 || !qtyStr || isNaN(qty) || qty <= 0) {
            hasInvalidRow = true;
            return;
        }
        products.push({ description: name, unit_price: priceStr, quantity: qtyStr });
    });

    if (hasInvalidRow) {
        showToast('Verifique os produtos: nome, preço e quantidade são obrigatórios.', 'warning');
        return;
    }
    if (products.length === 0) {
        showToast('Adicione ao menos um produto.', 'warning');
        return;
    }

    try {
        const res = await pywebview.api.add_expenses_structured(category, subcategory || null, products);
        if (res.success) {
            showToast(res.message, 'success');
            clearRegisterForm();
            loadCategoryList();
            loadSubcategoryList();
            loadBalance();  // atualiza saldo no header
        } else {
            showToast(res.message, 'error');
        }
    } catch (e) {
        showToast('Erro de comunicação com o backend.', 'error');
        console.error(e);
    }
}

function clearRegisterForm() {
    document.getElementById('reg-category').value = '';
    document.getElementById('reg-subcategory').value = '';
    document.getElementById('reg-products-list').innerHTML = '';
    addProductRow();
}

// ==========================================================================
// EXPENSES TREE (Drill-down)
// ==========================================================================

function ensureTreeViewActive() {
    // Mostra a seção view-tree e destaca o botão correspondente no
    // sidebar, SEM disparar showMonthsList() (diferente de switchView).
    // Usado pelas funções internas de navegação da árvore, que já cuidam
    // de mostrar o conteudo certo (meses/categorias/subcategorias/despesas)
    // por conta propria.
    document.querySelectorAll('.view-section').forEach(el => el.classList.add('hidden'));
    document.getElementById('view-tree').classList.remove('hidden');

    document.querySelectorAll('.nav-btn').forEach(b => {
        b.classList.remove('bg-primary-50', 'text-primary-700', 'dark:bg-primary-900/30', 'dark:text-primary-300', 'font-medium');
        b.classList.add('text-slate-600', 'dark:text-slate-300');
    });
    const treeBtn = document.querySelector('[data-target="view-tree"]');
    if (treeBtn) {
        treeBtn.classList.remove('text-slate-600', 'dark:text-slate-300');
        treeBtn.classList.add('bg-primary-50', 'text-primary-700', 'dark:bg-primary-900/30', 'dark:text-primary-300', 'font-medium');
    }
}

async function showMonthsList() {
    currentTreeMonth = null;
    currentTreeCategory = null;
    currentTreeSubcategory = null;
    currentTreeHasSubcategoryLevel = false;
    updateBreadcrumb();

    document.getElementById('tree-months').classList.remove('hidden');
    document.getElementById('tree-categories').classList.add('hidden');
    document.getElementById('tree-subcategories').classList.add('hidden');
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
    currentTreeSubcategory = null;
    currentTreeHasSubcategoryLevel = false;
    updateBreadcrumb();

    // Garante que a seção view-tree esteja visível (ex.: quando chamado
    // a partir do Dashboard). NAO usa switchView('view-tree') aqui: essa
    // função dispara showMonthsList() como efeito colateral sempre que o
    // alvo e 'view-tree', o que resetava currentTreeMonth de volta para
    // null logo após termos acabado de defini-lo acima -- e era por isso
    // que os botoes "Voltar" da arvore paravam de funcionar depois de
    // navegar para uma categoria.
    ensureTreeViewActive();

    document.getElementById('tree-months').classList.add('hidden');
    document.getElementById('tree-categories').classList.remove('hidden');
    document.getElementById('tree-subcategories').classList.add('hidden');
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
            card.onclick = () => viewCategorySubcategories(month, row.category);
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

async function viewCategorySubcategories(month, category) {
    currentTreeCategory = category;
    currentTreeSubcategory = null;

    try {
        const res = await pywebview.api.get_subcategories_by_month_and_category(month, category);
        const buckets = (res.success && res.data) ? res.data : [];

        // Se a categoria não usa subcategorias (só o balde "sem subcategoria",
        // ou nenhum dado), pula direto para a lista de despesas -- ninguem
        // precisa de um clique extra pra categorias que não usam o recurso.
        const onlyEmptyBucket = buckets.length === 0 || (buckets.length === 1 && buckets[0].subcategory === '');
        if (onlyEmptyBucket) {
            currentTreeHasSubcategoryLevel = false;
            viewCategoryExpenses(month, category, null);
            return;
        }

        currentTreeHasSubcategoryLevel = true;
        updateBreadcrumb();

        document.getElementById('tree-months').classList.add('hidden');
        document.getElementById('tree-categories').classList.add('hidden');
        document.getElementById('tree-subcategories').classList.remove('hidden');
        document.getElementById('tree-expenses').classList.add('hidden');

        document.getElementById('tree-subcat-title').textContent = `${formatMonth(month)} > ${category}`;
        const grid = document.getElementById('tree-subcategories-grid');
        grid.innerHTML = '';

        buckets.forEach(row => {
            const isEmpty = row.subcategory === '';
            const label = isEmpty ? 'Sem subcategoria' : row.subcategory;
            const card = document.createElement('div');
            card.className = 'bg-card-light dark:bg-card-dark rounded-2xl p-5 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md hover:border-primary-300 dark:hover:border-primary-700 cursor-pointer transition-all';
            card.onclick = () => viewCategoryExpenses(month, category, row.subcategory);
            card.innerHTML = `
                <div class="flex items-center justify-between mb-3">
                    <span class="text-lg font-bold ${isEmpty ? 'text-slate-400 dark:text-slate-500 italic' : ''}">${escapeHtml(label)}</span>
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
        console.error(e);
        // Em caso de erro, cai para a listagem direta de despesas
        currentTreeHasSubcategoryLevel = false;
        viewCategoryExpenses(month, category, null);
    }
}

function showSubcategoriesForCategory() {
    if (currentTreeMonth && currentTreeCategory) {
        viewCategorySubcategories(currentTreeMonth, currentTreeCategory);
    }
}

function goBackFromExpenses() {
    if (currentTreeHasSubcategoryLevel) {
        showSubcategoriesForCategory();
    } else {
        showCategoriesForMonth();
    }
}

async function viewCategoryExpenses(month, category, subcategory = null) {
    currentTreeCategory = category;
    currentTreeSubcategory = subcategory;
    updateBreadcrumb();

    document.getElementById('tree-months').classList.add('hidden');
    document.getElementById('tree-categories').classList.add('hidden');
    document.getElementById('tree-subcategories').classList.add('hidden');
    document.getElementById('tree-expenses').classList.remove('hidden');

    let title = `${formatMonth(month)} > ${category}`;
    if (subcategory) title += ` > ${subcategory}`;
    else if (subcategory === '') title += ` > Sem subcategoria`;
    document.getElementById('tree-exp-title').textContent = title;

    const tbody = document.getElementById('tree-expenses-body');
    tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400"><i class="ph ph-spinner animate-spin text-2xl"></i></td></tr>';

    try {
        const res = await pywebview.api.get_expenses_by_month_and_category(month, category, subcategory);
        tbody.innerHTML = '';

        if (!res.success || !res.data.length) {
            tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400">Nenhuma despesa encontrada.</td></tr>`;
            return;
        }

        res.data.forEach(exp => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-800/50 transition';

            // Se a despesa foi lancada por quantidade x preco unitario
            // (quantidade != 1), mostramos essa composição abaixo da descrição.
            let descHtml = escapeHtml(exp.description);
            const qty = Number(exp.quantity);
            if (!isNaN(qty) && qty !== 1) {
                descHtml += `<br><span class="text-xs text-slate-400">${formatQuantity(qty)} &times; ${formatCurrency(exp.unit_price)}</span>`;
            }
            if (exp.subcategory) {
                descHtml += ` <span class="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded-full ml-1">${escapeHtml(exp.subcategory)}</span>`;
            }

            tr.innerHTML = `
                <td class="px-6 py-4 text-sm text-slate-500 dark:text-slate-400">${formatDateTime(exp.created_at)}</td>
                <td class="px-6 py-4 font-medium">${descHtml}</td>
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
        if (currentTreeHasSubcategoryLevel) {
            html += ` <span class="text-slate-300">/</span> <button onclick="showSubcategoriesForCategory()" class="hover:text-primary-600 dark:hover:text-primary-400 transition">${escapeHtml(currentTreeCategory)}</button>`;
        } else {
            html += ` <span class="text-slate-300">/</span> <span class="text-slate-700 dark:text-slate-200 font-medium">${escapeHtml(currentTreeCategory)}</span>`;
        }
    }
    if (currentTreeHasSubcategoryLevel && currentTreeSubcategory !== null) {
        const label = currentTreeSubcategory === '' ? 'Sem subcategoria' : currentTreeSubcategory;
        html += ` <span class="text-slate-300">/</span> <span class="text-slate-700 dark:text-slate-200 font-medium">${escapeHtml(label)}</span>`;
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
            showToast('Despesa não encontrada.', 'error');
            return;
        }

        loadSubcategoryList();

        document.getElementById('edit-id').value = res.data.id;
        document.getElementById('edit-category').value = res.data.category;
        document.getElementById('edit-subcategory').value = res.data.subcategory || '';
        document.getElementById('edit-description').value = res.data.description;
        document.getElementById('edit-date').value = res.data.created_at.split(' ')[0];
        document.getElementById('edit-unit-price').value = res.data.unit_price;
        document.getElementById('edit-quantity').value = res.data.quantity;
        updateEditTotal();

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

function stepEditQty(delta) {
    const qtyInput = document.getElementById('edit-quantity');
    let qty = parseFloat(qtyInput.value) || 0;
    qty = Math.max(0.001, qty + delta);
    qtyInput.value = Math.round(qty * 1000) / 1000;
    updateEditTotal();
}

function updateEditTotal() {
    const price = parseFloat(document.getElementById('edit-unit-price').value) || 0;
    const qty = parseFloat(document.getElementById('edit-quantity').value) || 0;
    document.getElementById('edit-total-display').textContent = formatCurrency(price * qty);
}

async function submitEdit() {
    const id = parseInt(document.getElementById('edit-id').value);
    const category = document.getElementById('edit-category').value.trim();
    const subcategory = document.getElementById('edit-subcategory').value.trim();
    const description = document.getElementById('edit-description').value.trim();
    const dateVal = document.getElementById('edit-date').value;
    const unitPriceStr = document.getElementById('edit-unit-price').value.trim();
    const quantityStr = document.getElementById('edit-quantity').value.trim();

    const price = parseFloat(unitPriceStr);
    const qty = parseFloat(quantityStr);
    if (!category || !description || !dateVal || !unitPriceStr || isNaN(price) || price <= 0 || !quantityStr || isNaN(qty) || qty <= 0) {
        showToast('Preencha todos os campos corretamente.', 'warning');
        return;
    }

    try {
        const res = await pywebview.api.update_expense(
            id, category, description, null, subcategory || null, quantityStr, unitPriceStr, dateVal
        );
        if (res.success) {
            showToast(res.message, 'success');
            closeEditModal();
            // Refresh current view (preservando o filtro de subcategoria, se houver)
            if (currentTreeMonth && currentTreeCategory) {
                viewCategoryExpenses(currentTreeMonth, currentTreeCategory, currentTreeSubcategory);
            } else if (currentTreeMonth) {
                viewMonthCategories(currentTreeMonth);
            }
            loadDashboard();
            loadBalance();  // saldo pode ter mudado (bug corrigido: editar valor agora ajusta o saldo)
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
            // Refresh current view (preservando o filtro de subcategoria, se houver)
            if (currentTreeMonth && currentTreeCategory) {
                viewCategoryExpenses(currentTreeMonth, currentTreeCategory, currentTreeSubcategory);
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

function computeNextSalaryDate(anchorStr) {
    if (!anchorStr) return null;
    let d = new Date(anchorStr + 'T00:00:00');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    while (d < today) {
        d.setDate(d.getDate() + 30);
    }
    return d;
}

async function loadBalanceModalValues() {
    try {
        const balRes = await pywebview.api.get_balance();
        const salRes = await pywebview.api.get_salary();
        const vacRes = await pywebview.api.get_vacation_month();
        if (balRes.success) {
            document.getElementById('balance-input').value = Number(balRes.balance) !== 0 ? balRes.balance : '';
        }
        if (salRes.success) {
            document.getElementById('salary-input').value = Number(salRes.salary) !== 0 ? salRes.salary : '';
            const salaryDisplay = document.getElementById('salary-display');
            if (salaryDisplay) {
                salaryDisplay.textContent = salRes.salary > 0 
                    ? `Salário atual: ${formatCurrency(salRes.salary)}` 
                    : 'Nenhum salario configurado';
            }
            const nextDate = computeNextSalaryDate(salRes.last_salary_date);
            document.getElementById('next-salary-date-input').value = nextDate ? nextDate.toISOString().slice(0, 10) : '';
        }
        if (vacRes.success) {
            document.getElementById('vacation-month-input').value = vacRes.month;
        }
    } catch (e) {
        console.error('Erro ao carregar valores do modal:', e);
    }
}

async function submitBalance() {
    const balanceVal = document.getElementById('balance-input').value.trim();
    const salaryVal = document.getElementById('salary-input').value.trim();
    const vacationVal = document.getElementById('vacation-month-input').value;
    const nextDateVal = document.getElementById('next-salary-date-input').value;
    
    // String crua vai para o Python (Decimal); parseFloat aqui é só validação.
    const balanceStr = balanceVal === '' ? '0' : balanceVal;
    const salaryStr = salaryVal === '' ? '0' : salaryVal;
    const vacationMonth = vacationVal === '' ? 7 : parseInt(vacationVal);
    
    if (isNaN(parseFloat(balanceStr)) || isNaN(parseFloat(salaryStr)) || isNaN(vacationMonth)) {
        showToast('Informe valores válidos.', 'warning');
        return;
    }
    
    try {
        // Salva saldo
        const balRes = await pywebview.api.set_balance(balanceStr);
        // Salva salario
        const salRes = await pywebview.api.set_salary(salaryStr);
        // Salva mes de ferias
        const vacRes = await pywebview.api.set_vacation_month(vacationMonth);
        // Salva proxima data de recebimento (se preenchida) -- ancora usada
        // pelo auto-credito de 30 em 30 dias e pelo calendario de salarios
        let dateRes = { success: true };
        if (nextDateVal) {
            dateRes = await pywebview.api.set_next_salary_date(nextDateVal);
        }
        
        if (balRes.success && salRes.success && vacRes.success && dateRes.success) {
            showToast('Saldo, salário e mês de férias atualizados!', 'success');
            document.getElementById('header-balance').textContent = formatCurrency(balRes.balance);
            closeBalanceModal();
        } else {
            showToast(balRes.message || salRes.message || vacRes.message || dateRes.message, 'error');
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

function formatQuantity(value) {
    const n = Number(value) || 0;
    // Mostra ate 3 casas decimais, mas sem zeros a mais (2 -> "2", 0.750 -> "0,75")
    return new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 3 }).format(n);
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
        closeFeriasModal();
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
                console.error('pywebview.api não ficou disponível a tempo.');
                showToast('Erro de inicialização do app.', 'error');
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
        checkAutoSalary();  // verifica credito automatico de salario
        loadAppVersion();
    });
});

async function loadAppVersion() {
    try {
        const res = await pywebview.api.get_app_version();
        const footer = document.getElementById('app-version-footer');
        if (res.success && footer) {
            footer.innerHTML = `Controlador de Gastos v${res.version}<br>PyWebView Desktop`;
        }
    } catch (e) {
        console.error('Erro ao carregar versao:', e);
    }
}

// ==========================================================================
// AUTO SALARIO (a cada 30 dias)
// ==========================================================================

async function checkAutoSalary() {
    try {
        const res = await pywebview.api.check_auto_salary();
        if (res.success && res.should_credit) {
            showToast(res.message, 'success');
            loadBalance();
        }
    } catch (e) {
        console.error('Auto-salary check error:', e);
    }
}

// ==========================================================================
// CALENDARIO DE SALARIOS & FERIAS
// ==========================================================================

async function renderSalaryCalendar() {
    const container = document.getElementById('salary-calendar-grid');
    if (!container) return;
    container.innerHTML = '<div class="col-span-full text-center py-12 text-slate-400"><i class="ph ph-spinner animate-spin text-3xl"></i></div>';

    try {
        const calRes = await pywebview.api.get_salary_calendar();
        container.innerHTML = '';

        if (!calRes.success) {
            container.innerHTML = `<div class="col-span-full text-center py-12 text-red-400">Erro ao carregar calendario.</div>`;
            return;
        }

        if (!calRes.has_reference_date) {
            container.innerHTML = `
                <div class="col-span-full text-center py-16 text-slate-400 space-y-3">
                    <i class="ph ph-calendar-x text-4xl block mx-auto"></i>
                    <p>Configure a proxima data de recebimento do salario para ver o calendario.</p>
                    <button onclick="openBalanceModal()" class="text-primary-600 hover:underline text-sm font-medium">Configurar agora</button>
                </div>`;
            return;
        }

        calRes.data.forEach((entry, idx) => {
            const d = new Date(entry.date + 'T00:00:00');
            const dd = String(d.getDate()).padStart(2, '0');
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const yy = String(d.getFullYear()).slice(-2);
            const dateLabel = `${dd}/${mm}/${yy}`;

            // O primeiro item da lista e sempre o proximo recebimento (a
            // lista já vem ordenada a partir de hoje, 30 em 30 dias).
            const isNext = idx === 0;

            const card = document.createElement('div');
            let extraClass = isNext
                ? 'border-primary-400 dark:border-primary-600 ring-2 ring-primary-200 dark:ring-primary-800'
                : 'border-slate-200 dark:border-slate-700';
            if (entry.is_vacation) extraClass += ' bg-amber-50 dark:bg-amber-900/20';
            if (entry.is_vacation) extraClass += ' cursor-pointer hover:shadow-md hover:border-amber-400 dark:hover:border-amber-600 transition-all';

            card.className = `rounded-2xl p-4 border ${extraClass} bg-card-light dark:bg-card-dark shadow-sm flex flex-col gap-2`;

            const valorDisplay = (entry.amount !== null && entry.amount !== undefined)
                ? formatCurrency(entry.amount)
                : '---';

            card.innerHTML = `
                <div class="flex items-center justify-between">
                    <span class="font-bold ${entry.is_vacation ? 'text-amber-700 dark:text-amber-400' : ''}">${dateLabel}</span>
                    <div class="flex gap-1.5">
                        ${entry.is_vacation ? '<span class="text-xs bg-amber-200 dark:bg-amber-800 text-amber-800 dark:text-amber-200 px-2 py-0.5 rounded-full font-medium">Férias</span>' : ''}
                        ${isNext ? '<span class="text-xs bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 px-2 py-0.5 rounded-full font-medium">Próximo</span>' : ''}
                    </div>
                </div>
                <div class="mt-1">
                    <p class="text-lg font-semibold ${entry.is_vacation ? 'text-amber-700 dark:text-amber-400' : 'text-primary-600 dark:text-primary-400'}">${valorDisplay}</p>
                    <p class="text-xs text-slate-400">${entry.is_vacation ? 'Clique para detalhes' : entry.label}</p>
                </div>
            `;

            if (entry.is_vacation) {
                card.addEventListener('click', () => openFeriasModal());
            }

            container.appendChild(card);
        });
    } catch (e) {
        container.innerHTML = `<div class="col-span-full text-center py-12 text-red-400">Erro ao carregar calendario.</div>`;
        console.error(e);
    }
}

async function openFeriasModal() {
    const modal = document.getElementById('ferias-modal');
    const resultDiv = document.getElementById('ferias-result');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    resultDiv.innerHTML = '';

    // Pega o salario configurado como default
    try {
        const res = await pywebview.api.get_salary();
        const input = document.getElementById('ferias-salario-input');
        if (res.success && res.salary > 0) {
            input.value = res.salary;
            calcularFerias();
        } else {
            input.value = '';
        }
        input.focus();
    } catch (e) {
        console.error(e);
    }
}

function closeFeriasModal() {
    const modal = document.getElementById('ferias-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

async function calcularFerias() {
    const input = document.getElementById('ferias-salario-input');
    const salarioStr = input.value.trim();
    const salario = parseFloat(salarioStr);
    const resultDiv = document.getElementById('ferias-result');

    if (!salarioStr || isNaN(salario) || salario <= 0) {
        resultDiv.innerHTML = `<p class="text-amber-600 dark:text-amber-400 text-sm">Informe um salario valido.</p>`;
        return;
    }

    try {
        const res = await pywebview.api.calcular_ferias(salarioStr);
        if (res.success) {
            resultDiv.innerHTML = `
                <div class="space-y-2 text-sm">
                    <div class="flex justify-between"><span class="text-slate-500 dark:text-slate-400">Salário bruto:</span><span class="font-medium">${formatCurrency(res.salario_bruto)}</span></div>
                    <div class="flex justify-between"><span class="text-slate-500 dark:text-slate-400">1/3 constitucional:</span><span class="font-medium">${formatCurrency(res.terco_constitucional)}</span></div>
                    <div class="flex justify-between border-t border-slate-200 dark:border-slate-700 pt-1"><span class="text-slate-500 dark:text-slate-400">Total bruto:</span><span class="font-semibold">${formatCurrency(res.total_bruto)}</span></div>
                    <div class="flex justify-between text-red-600 dark:text-red-400"><span>INSS:</span><span>-${formatCurrency(res.inss)}</span></div>
                    <div class="flex justify-between"><span class="text-slate-500 dark:text-slate-400">Base IRRF:</span><span>${formatCurrency(res.base_irrf)}</span></div>
                    <div class="flex justify-between text-red-600 dark:text-red-400"><span>IRRF calculado:</span><span>-${formatCurrency(res.irrf_calculado)}</span></div>
                    <div class="flex justify-between text-emerald-600 dark:text-emerald-400"><span>Desconto adicional:</span><span>+${formatCurrency(res.desconto_adicional)}</span></div>
                    <div class="flex justify-between border-t border-slate-200 dark:border-slate-700 pt-1"><span class="text-slate-500 dark:text-slate-400">IRRF final:</span><span class="font-medium">-${formatCurrency(res.irrf_final)}</span></div>
                    <div class="flex justify-between text-lg font-bold text-primary-600 dark:text-primary-400 pt-1"><span>LIQUIDO:</span><span>${formatCurrency(res.salario_liquido)}</span></div>
                </div>
            `;
        } else {
            resultDiv.innerHTML = `<p class="text-red-600 dark:text-red-400 text-sm">${res.message}</p>`;
        }
    } catch (e) {
        resultDiv.innerHTML = `<p class="text-red-600 dark:text-red-400 text-sm">Erro ao calcular.</p>`;
    }
}
