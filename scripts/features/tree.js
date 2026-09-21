/**
 * scripts/features/tree.js - Árvore de Gastos (drill-down).
 * Navegação hierárquica: Meses -> Categorias -> Subcategorias -> Despesas.
 */
window.CG = window.CG || {};

CG.tree = (function () {
    const { formatCurrency, formatQuantity, formatMonth, formatDateTime, escapeHtml } = CG.utils;

    // ------------------------------------------------------------------
    // helpers de visibilidade / navegação
    // ------------------------------------------------------------------

    /**
     * Mostra a seção view-tree e destaca o botão do sidebar, SEM disparar
     * showMonthsList() (diferente de switchView). Usado pelas funções
     * internas de navegação da árvore, que já cuidam de mostrar o conteúdo
     * certo por conta própria.
     */
    function ensureTreeViewActive() {
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

    function showLevel(level) {
        document.getElementById('tree-months').classList.toggle('hidden', level !== 'months');
        document.getElementById('tree-categories').classList.toggle('hidden', level !== 'categories');
        document.getElementById('tree-subcategories').classList.toggle('hidden', level !== 'subcategories');
        document.getElementById('tree-expenses').classList.toggle('hidden', level !== 'expenses');
    }

    // ------------------------------------------------------------------
    // Nível 1: Meses
    // ------------------------------------------------------------------
    async function showMonthsList() {
        CG.state.currentTreeMonth = null;
        CG.state.currentTreeCategory = null;
        CG.state.currentTreeSubcategory = null;
        CG.state.currentTreeHasSubcategoryLevel = false;
        updateBreadcrumb();
        showLevel('months');

        const grid = document.getElementById('tree-months');
        grid.innerHTML = '<div class="col-span-full text-center py-12 text-slate-400"><i class="ph ph-spinner animate-spin text-3xl"></i></div>';

        try {
            const res = await CG.api.call('get_months_summary');
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
        }
    }

    // ------------------------------------------------------------------
    // Nível 2: Categorias do mês
    // ------------------------------------------------------------------
    async function viewMonthCategories(month) {
        CG.state.currentTreeMonth = month;
        CG.state.currentTreeCategory = null;
        CG.state.currentTreeSubcategory = null;
        CG.state.currentTreeHasSubcategoryLevel = false;
        updateBreadcrumb();

        // Garante que a seção view-tree esteja visível (ex.: vindo do
        // Dashboard). NÃO usa switchView('view-tree'): essa função dispara
        // showMonthsList() como efeito colateral e resetaria o estado.
        ensureTreeViewActive();
        showLevel('categories');

        document.getElementById('tree-cat-title').textContent = formatMonth(month);
        const grid = document.getElementById('tree-categories-grid');
        grid.innerHTML = '<div class="col-span-full text-center py-12 text-slate-400"><i class="ph ph-spinner animate-spin text-3xl"></i></div>';

        try {
            const res = await CG.api.call('get_categories_by_month', month);
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
                        <span class="text-lg font-bold">${escapeHtml(row.category)}</span>
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
        }
    }

    function showCategoriesForMonth() {
        if (CG.state.currentTreeMonth) {
            viewMonthCategories(CG.state.currentTreeMonth);
        }
    }

    // ------------------------------------------------------------------
    // Nível 3: Subcategorias (só quando a categoria realmente usa)
    // ------------------------------------------------------------------
    async function viewCategorySubcategories(month, category) {
        CG.state.currentTreeCategory = category;
        CG.state.currentTreeSubcategory = null;

        try {
            const res = await CG.api.call('get_subcategories_by_month_and_category', month, category);
            const buckets = (res.success && res.data) ? res.data : [];

            // Se a categoria não usa subcategorias (só o balde "sem
            // subcategoria", ou nenhum dado), pula direto para a lista de
            // despesas — ninguém precisa de um clique extra.
            const onlyEmptyBucket = buckets.length === 0 || (buckets.length === 1 && buckets[0].subcategory === '');
            if (onlyEmptyBucket) {
                CG.state.currentTreeHasSubcategoryLevel = false;
                viewCategoryExpenses(month, category, null);
                return;
            }

            CG.state.currentTreeHasSubcategoryLevel = true;
            updateBreadcrumb();
            showLevel('subcategories');

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
            CG.state.currentTreeHasSubcategoryLevel = false;
            viewCategoryExpenses(month, category, null);
        }
    }

    function showSubcategoriesForCategory() {
        if (CG.state.currentTreeMonth && CG.state.currentTreeCategory) {
            viewCategorySubcategories(CG.state.currentTreeMonth, CG.state.currentTreeCategory);
        }
    }

    function goBackFromExpenses() {
        if (CG.state.currentTreeHasSubcategoryLevel) {
            showSubcategoriesForCategory();
        } else {
            showCategoriesForMonth();
        }
    }

    // ------------------------------------------------------------------
    // Nível 4: Despesas individuais
    // ------------------------------------------------------------------
    async function viewCategoryExpenses(month, category, subcategory = null) {
        CG.state.currentTreeCategory = category;
        CG.state.currentTreeSubcategory = subcategory;
        updateBreadcrumb();
        showLevel('expenses');

        let title = `${formatMonth(month)} > ${category}`;
        if (subcategory) title += ` > ${subcategory}`;
        else if (subcategory === '') title += ` > Sem subcategoria`;
        document.getElementById('tree-exp-title').textContent = title;

        const tbody = document.getElementById('tree-expenses-body');
        tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400"><i class="ph ph-spinner animate-spin text-2xl"></i></td></tr>';

        try {
            const res = await CG.api.call('get_expenses_by_month_and_category', month, category, subcategory);
            tbody.innerHTML = '';

            if (!res.success || !res.data.length) {
                tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400">Nenhuma despesa encontrada.</td></tr>`;
                return;
            }

            res.data.forEach(exp => {
                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-800/50 transition';

                // Se a despesa foi lançada por quantidade x preço unitário
                // (quantidade != 1), mostra essa composição abaixo da descrição.
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
                            <button onclick="CG.modals.openEdit(${exp.id})" class="p-2 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 transition" title="Editar">
                                <i class="ph ph-pencil-simple text-lg"></i>
                            </button>
                            <button onclick="CG.modals.openDelete(${exp.id})" class="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition" title="Excluir">
                                <i class="ph ph-trash text-lg"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-red-400">Erro ao carregar despesas.</td></tr>`;
        }
    }

    // ------------------------------------------------------------------
    // Breadcrumb
    // ------------------------------------------------------------------
    function updateBreadcrumb() {
        const bc = document.getElementById('tree-breadcrumb');
        const st = CG.state;
        let html = `<button onclick="CG.tree.showMonthsList()" class="hover:text-primary-600 dark:hover:text-primary-400 transition font-medium">Meses</button>`;

        if (st.currentTreeMonth) {
            html += ` <span class="text-slate-300">/</span> <button onclick="CG.tree.showCategoriesForMonth()" class="hover:text-primary-600 dark:hover:text-primary-400 transition">${formatMonth(st.currentTreeMonth)}</button>`;
        }
        if (st.currentTreeCategory) {
            if (st.currentTreeHasSubcategoryLevel) {
                html += ` <span class="text-slate-300">/</span> <button onclick="CG.tree.showSubcategoriesForCategory()" class="hover:text-primary-600 dark:hover:text-primary-400 transition">${escapeHtml(st.currentTreeCategory)}</button>`;
            } else {
                html += ` <span class="text-slate-300">/</span> <span class="text-slate-700 dark:text-slate-200 font-medium">${escapeHtml(st.currentTreeCategory)}</span>`;
            }
        }
        if (st.currentTreeHasSubcategoryLevel && st.currentTreeSubcategory !== null) {
            const label = st.currentTreeSubcategory === '' ? 'Sem subcategoria' : st.currentTreeSubcategory;
            html += ` <span class="text-slate-300">/</span> <span class="text-slate-700 dark:text-slate-200 font-medium">${escapeHtml(label)}</span>`;
        }

        bc.innerHTML = html;
    }

    /** Atualiza a listagem atual após editar/excluir uma despesa. */
    function refreshCurrentView() {
        const st = CG.state;
        if (st.currentTreeMonth && st.currentTreeCategory) {
            viewCategoryExpenses(st.currentTreeMonth, st.currentTreeCategory, st.currentTreeSubcategory);
        } else if (st.currentTreeMonth) {
            viewMonthCategories(st.currentTreeMonth);
        } else {
            showMonthsList();
        }
    }

    return {
        ensureTreeViewActive,
        showMonthsList,
        viewMonthCategories,
        showCategoriesForMonth,
        viewCategorySubcategories,
        showSubcategoriesForCategory,
        goBackFromExpenses,
        viewCategoryExpenses,
        updateBreadcrumb,
        refreshCurrentView,
    };
})();
