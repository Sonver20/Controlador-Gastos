/**
 * scripts/features/tree.js - Árvore de Gastos (drill-down).
 * Navegação hierárquica: Meses -> Categorias -> Subcategorias -> Despesas.
 */
window.CG = window.CG || {};

CG.tree = (function () {
    const { formatCurrency, formatQuantity, formatMonth, escapeHtml } = CG.utils;

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
                grid.innerHTML = `<div class="col-span-full text-center py-12 text-slate-400">${CG.i18n.t('tree.no_expenses_recorded')}</div>`;
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
                        <span class="text-slate-500 dark:text-slate-400">${CG.i18n.t('common.count_expenses', { count: row.count })}</span>
                        <span class="font-semibold text-primary-600 dark:text-primary-400">${formatCurrency(row.total)}</span>
                    </div>
                `;
                grid.appendChild(card);
            });
        } catch (e) {
            grid.innerHTML = `<div class="col-span-full text-center py-12 text-red-400">${CG.i18n.t('tree.load_months_error')}</div>`;
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
                grid.innerHTML = `<div class="col-span-full text-center py-12 text-slate-400">${CG.i18n.t('tree.no_category_found')}</div>`;
                return;
            }

            res.data.forEach(row => {
                const card = document.createElement('div');
                card.className = 'relative bg-card-light dark:bg-card-dark rounded-2xl p-5 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md hover:border-primary-300 dark:hover:border-primary-700 cursor-pointer transition-all';
                card.onclick = () => viewCategorySubcategories(month, row.category);
                card.innerHTML = `
                    <button class="rename-btn absolute top-3 right-3 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition" title="${CG.i18n.t('tree.rename_category_title')}">
                        <i class="ph ph-pencil-simple text-sm"></i>
                    </button>
                    <div class="flex items-center justify-between mb-3 pr-8">
                        <span class="text-lg font-bold">${escapeHtml(row.category)}</span>
                        <i class="ph ph-caret-right text-slate-400"></i>
                    </div>
                    <div class="flex items-center justify-between text-sm">
                        <span class="text-slate-500 dark:text-slate-400">${CG.i18n.t('common.count_items', { count: row.count })}</span>
                        <span class="font-semibold text-primary-600 dark:text-primary-400">${formatCurrency(row.total)}</span>
                    </div>
                `;
                // Listener via DOM (não onclick inline): o nome da categoria
                // pode ter aspas/apóstrofos, que quebrariam o atributo HTML.
                card.querySelector('.rename-btn').onclick = (e) => { e.stopPropagation(); openRenameCategory(row.category); };
                grid.appendChild(card);
            });
        } catch (e) {
            grid.innerHTML = `<div class="col-span-full text-center py-12 text-red-400">${CG.i18n.t('tree.load_categories_error')}</div>`;
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
                const label = isEmpty ? CG.i18n.t('tree.no_subcategory') : row.subcategory;
                const card = document.createElement('div');
                card.className = 'relative bg-card-light dark:bg-card-dark rounded-2xl p-5 shadow-sm border border-slate-200 dark:border-slate-700 hover:shadow-md hover:border-primary-300 dark:hover:border-primary-700 cursor-pointer transition-all';
                card.onclick = () => viewCategoryExpenses(month, category, row.subcategory);
                card.innerHTML = `
                    <button class="rename-btn absolute top-3 right-3 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition" title="${CG.i18n.t('tree.rename_subcategory_title')}">
                        <i class="ph ph-pencil-simple text-sm"></i>
                    </button>
                    <div class="flex items-center justify-between mb-3 pr-8">
                        <span class="text-lg font-bold ${isEmpty ? 'text-slate-400 dark:text-slate-500 italic' : ''}">${escapeHtml(label)}</span>
                        <i class="ph ph-caret-right text-slate-400"></i>
                    </div>
                    <div class="flex items-center justify-between text-sm">
                        <span class="text-slate-500 dark:text-slate-400">${CG.i18n.t('common.count_items', { count: row.count })}</span>
                        <span class="font-semibold text-primary-600 dark:text-primary-400">${formatCurrency(row.total)}</span>
                    </div>
                `;
                card.querySelector('.rename-btn').onclick = (e) => { e.stopPropagation(); openRenameSubcategory(category, row.subcategory); };
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
        else if (subcategory === '') title += ` > ${CG.i18n.t('tree.no_subcategory')}`;
        document.getElementById('tree-exp-title').textContent = title;

        const addBtn = document.getElementById('tree-exp-add-btn');
        if (addBtn) addBtn.onclick = () => openQuickAdd();

        const renameBtn = document.getElementById('tree-exp-rename-btn');
        if (renameBtn) {
            renameBtn.onclick = () => {
                if (CG.state.currentTreeHasSubcategoryLevel) {
                    openRenameSubcategory(category, subcategory);
                } else {
                    openRenameCategory(category);
                }
            };
        }

        const tbody = document.getElementById('tree-expenses-body');
        tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400"><i class="ph ph-spinner animate-spin text-2xl"></i></td></tr>';

        try {
            const res = await CG.api.call('get_expenses_by_month_and_category', month, category, subcategory);
            tbody.innerHTML = '';

            if (!res.success || !res.data.length) {
                tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400">${CG.i18n.t('tree.no_expense_found')}</td></tr>`;
                return;
            }

            // Agrupa por dia (a lista já vem ordenada por created_at DESC)
            // e insere um cabeçalho de dia antes de cada grupo, com o total
            // daquele dia. Isso resolve a confusão de duas compras na MESMA
            // subcategoria em DIAS DIFERENTES parecerem uma só: cada dia
            // fica visualmente separado, e a coluna que antes repetia a
            // data inteira em cada linha agora mostra só o horário (a data
            // já está no cabeçalho do grupo).
            const dayTotals = {};
            res.data.forEach(exp => {
                const dateKey = (exp.created_at || '').split(' ')[0];
                dayTotals[dateKey] = (dayTotals[dateKey] || 0) + Number(exp.amount);
            });

            let lastDateKey = null;
            res.data.forEach(exp => {
                const dateKey = (exp.created_at || '').split(' ')[0];
                if (dateKey !== lastDateKey) {
                    lastDateKey = dateKey;
                    const headerTr = document.createElement('tr');
                    headerTr.className = 'bg-slate-50 dark:bg-slate-800/60';
                    let dayLabel = '-';
                    if (dateKey) {
                        const weekday = new Intl.DateTimeFormat(CG.i18n.locale(), { weekday: 'long' }).format(new Date(dateKey + 'T00:00:00'));
                        dayLabel = `${weekday}, ${CG.utils.formatDateBR(dateKey)}`;
                    }
                    headerTr.innerHTML = `
                        <td colspan="4" class="px-6 py-2 text-xs font-semibold text-slate-500 dark:text-slate-400">
                            <div class="flex items-center justify-between">
                                <span class="uppercase tracking-wide">${escapeHtml(dayLabel)}</span>
                                <span class="font-semibold text-primary-600 dark:text-primary-400 normal-case">${formatCurrency(dayTotals[dateKey])}</span>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(headerTr);
                }

                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-50 dark:hover:bg-slate-800/50 transition';

                // Detalhes abaixo da descrição, cada um independente:
                // - normal (quantidade != 1): "2 × R$ 4,50" (a conta que gerou o valor);
                // - peso variável: "4 un. · valor total" (a quantidade é só a
                //   contagem de itens, o valor não foi multiplicado por ela);
                // - peso ou volume, se anotado, em qualquer modo: "0,74 kg", "500 ml".
                let descHtml = escapeHtml(exp.description);
                const qty = Number(exp.quantity);
                const hasMeasure = exp.measure_value !== null && exp.measure_value !== undefined && exp.measure_value !== '';
                const details = [];
                if (exp.is_variable_price) {
                    if (!isNaN(qty) && qty !== 1) details.push(CG.i18n.t('tree.item_count_tag', { count: formatQuantity(qty) }));
                    details.push(CG.i18n.t('tree.variable_price_tag'));
                } else if (!isNaN(qty) && qty !== 1) {
                    details.push(`${formatQuantity(qty)} &times; ${formatCurrency(exp.unit_price)}`);
                }
                // Peso/volume como foi digitado (ex.: "740 g", "1,5 L") -- as unidades são iguais em PT e EN.
                if (hasMeasure) details.push(`${formatQuantity(exp.measure_value)} ${escapeHtml(exp.measure_unit || 'kg')}`);
                if (details.length) {
                    descHtml += `<br><span class="text-xs text-slate-400">${details.join(' · ')}</span>`;
                }
                if (exp.subcategory) {
                    descHtml += ` <span class="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded-full ml-1">${escapeHtml(exp.subcategory)}</span>`;
                }

                tr.innerHTML = `
                    <td class="px-6 py-4 text-sm text-slate-500 dark:text-slate-400">${CG.utils.formatTime(exp.created_at)}</td>
                    <td class="px-6 py-4 font-medium">${descHtml}</td>
                    <td class="px-6 py-4 text-right font-semibold">${formatCurrency(exp.amount)}</td>
                    <td class="px-6 py-4 text-center">
                        <div class="flex items-center justify-center gap-2">
                            <button onclick="CG.modals.openEdit(${exp.id})" class="p-2 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 transition" title="${CG.i18n.t('tree.edit_title')}">
                                <i class="ph ph-pencil-simple text-lg"></i>
                            </button>
                            <button onclick="CG.modals.openDelete(${exp.id})" class="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-400 transition" title="${CG.i18n.t('tree.delete_title')}">
                                <i class="ph ph-trash text-lg"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-red-400">${CG.i18n.t('tree.load_expenses_error')}</td></tr>`;
        }
    }

    // ------------------------------------------------------------------
    // Renomear categoria / subcategoria
    // ------------------------------------------------------------------
    let renameContext = null; // { type: 'category'|'subcategory', category, subcategory }

    function openRenameCategory(category) {
        renameContext = { type: 'category', category };
        document.getElementById('rename-modal-title').textContent = CG.i18n.t('tree.rename_category_modal_title');
        document.getElementById('rename-current-name').textContent = category;
        const input = document.getElementById('rename-new-name');
        input.value = category;
        document.getElementById('rename-modal').classList.remove('hidden');
        document.getElementById('rename-modal').classList.add('flex');
        input.focus();
        input.select();
    }

    function openRenameSubcategory(category, subcategory) {
        renameContext = { type: 'subcategory', category, subcategory };
        const currentLabel = subcategory ? subcategory : CG.i18n.t('tree.no_subcategory');
        document.getElementById('rename-modal-title').textContent = CG.i18n.t('tree.rename_subcategory_modal_title');
        document.getElementById('rename-current-name').textContent = `${category} > ${currentLabel}`;
        const input = document.getElementById('rename-new-name');
        input.value = subcategory || '';
        document.getElementById('rename-modal').classList.remove('hidden');
        document.getElementById('rename-modal').classList.add('flex');
        input.focus();
        input.select();
    }

    function closeRenameModal() {
        document.getElementById('rename-modal').classList.add('hidden');
        document.getElementById('rename-modal').classList.remove('flex');
        renameContext = null;
    }

    async function submitRename() {
        if (!renameContext) return;
        const newName = document.getElementById('rename-new-name').value.trim();

        try {
            let res;
            if (renameContext.type === 'category') {
                if (!newName) {
                    CG.toast.show(CG.i18n.t('tree.rename_name_required'), 'warning');
                    return;
                }
                res = await CG.api.call('rename_category', renameContext.category, newName);
            } else {
                res = await CG.api.call('rename_subcategory', renameContext.category, renameContext.subcategory, newName);
            }

            if (res.success) {
                CG.i18n.showApiResult(res, 'success');
                closeRenameModal();
                CG.register.loadCategoryList();
                CG.register.loadSubcategoryList();
                CG.dashboard.load();
                // Re-renderiza a árvore a partir do nível mais alto que
                // ainda faz sentido (o nome pode ter mudado o suficiente
                // pra árvore de subcategorias precisar recarregar do zero).
                if (renameContext.type === 'category') {
                    showCategoriesForMonth();
                } else {
                    showSubcategoriesForCategory();
                }
            } else {
                CG.i18n.showApiResult(res, 'error');
            }
        } catch (e) {
            CG.toast.show(CG.i18n.t('tree.rename_error_generic'), 'error');
        }
    }

    // ------------------------------------------------------------------
    // Adicionar item rápido (direto na subcategoria/categoria atual)
    // ------------------------------------------------------------------
    function openQuickAdd() {
        const category = CG.state.currentTreeCategory;
        const subcategory = CG.state.currentTreeHasSubcategoryLevel ? CG.state.currentTreeSubcategory : null;
        const label = subcategory ? `${category} > ${subcategory}` : (subcategory === '' ? `${category} > ${CG.i18n.t('tree.no_subcategory')}` : category);
        document.getElementById('quickadd-context').textContent = label;
        document.getElementById('quickadd-description').value = '';
        document.getElementById('quickadd-price').value = '';
        document.getElementById('quickadd-quantity').value = '1';
        document.getElementById('quickadd-measure').value = '';
        document.getElementById('quickadd-measure-unit').value = 'kg';
        document.getElementById('quickadd-variable-price').checked = false;
        applyQuickAddVariablePriceUI(false);
        updateQuickAddTotal();
        document.getElementById('quickadd-modal').classList.remove('hidden');
        document.getElementById('quickadd-modal').classList.add('flex');
        document.getElementById('quickadd-description').focus();
    }

    function closeQuickAdd() {
        document.getElementById('quickadd-modal').classList.add('hidden');
        document.getElementById('quickadd-modal').classList.remove('flex');
    }

    function applyQuickAddVariablePriceUI(checked) {
        // Só o rótulo do preço muda (unitário x total pago); quantidade e
        // peso não são afetados pelo interruptor -- ver modals.js.
        const priceLabel = document.getElementById('quickadd-price-label');
        const priceKey = checked ? 'edit_modal.total_paid_label' : 'edit_modal.unit_price';
        priceLabel.setAttribute('data-i18n', priceKey);
        priceLabel.textContent = CG.i18n.t(priceKey);
    }

    function toggleQuickAddVariablePrice() {
        applyQuickAddVariablePriceUI(document.getElementById('quickadd-variable-price').checked);
        updateQuickAddTotal();
    }

    function stepQuickAddQty(delta) {
        const qtyInput = document.getElementById('quickadd-quantity');
        let qty = CG.utils.parseLocaleNumber(qtyInput.value);
        qty = Math.max(0.001, qty + delta);
        qtyInput.value = CG.utils.formatQuantity(Math.round(qty * 1000) / 1000);
        updateQuickAddTotal();
    }

    function updateQuickAddTotal() {
        const price = CG.utils.parseLocaleNumber(document.getElementById('quickadd-price').value);
        const qty = CG.utils.parseLocaleNumber(document.getElementById('quickadd-quantity').value);
        const isVariable = document.getElementById('quickadd-variable-price').checked;
        document.getElementById('quickadd-total-display').textContent = formatCurrency(isVariable ? price : price * qty);
    }

    async function submitQuickAdd() {
        const category = CG.state.currentTreeCategory;
        const subcategory = CG.state.currentTreeHasSubcategoryLevel ? CG.state.currentTreeSubcategory : null;
        const description = document.getElementById('quickadd-description').value.trim();
        const priceStr = document.getElementById('quickadd-price').value.trim().replace(',', '.');
        const qtyStr = document.getElementById('quickadd-quantity').value.trim().replace(',', '.');
        const isVariablePrice = document.getElementById('quickadd-variable-price').checked;
        const measureStr = document.getElementById('quickadd-measure').value.trim().replace(',', '.');
        const measureUnit = document.getElementById('quickadd-measure-unit').value;

        const price = parseFloat(priceStr);
        const qty = parseFloat(qtyStr);
        if (!description || !priceStr || isNaN(price) || price <= 0 || !qtyStr || isNaN(qty) || qty <= 0) {
            CG.toast.show(CG.i18n.t('tree.quickadd_fill_warning'), 'warning');
            return;
        }
        if (measureStr && (isNaN(parseFloat(measureStr)) || parseFloat(measureStr) <= 0)) {
            CG.toast.show(CG.i18n.t('edit_modal.invalid_measure_warning'), 'warning');
            return;
        }

        try {
            const res = await CG.api.call('add_expense', category, description, null, subcategory, qtyStr, priceStr, isVariablePrice,
                measureStr || null, measureStr ? measureUnit : null);
            if (res.success) {
                CG.i18n.showApiResult(res, 'success');
                closeQuickAdd();
                CG.register.loadCategoryList();
                CG.register.loadSubcategoryList();
                CG.dashboard.load();
                CG.balance.load();
                refreshCurrentView();
            } else {
                CG.i18n.showApiResult(res, 'error');
            }
        } catch (e) {
            CG.toast.show(CG.i18n.t('tree.quickadd_error_generic'), 'error');
        }
    }

    // ------------------------------------------------------------------
    // Breadcrumb
    // ------------------------------------------------------------------
    function updateBreadcrumb() {
        const bc = document.getElementById('tree-breadcrumb');
        const st = CG.state;
        let html = `<button onclick="CG.tree.showMonthsList()" class="hover:text-primary-600 dark:hover:text-primary-400 transition font-medium">${CG.i18n.t('tree.breadcrumb_months')}</button>`;

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
            const label = st.currentTreeSubcategory === '' ? CG.i18n.t('tree.no_subcategory') : st.currentTreeSubcategory;
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
        openRenameCategory,
        openRenameSubcategory,
        closeRenameModal,
        submitRename,
        openQuickAdd,
        closeQuickAdd,
        toggleQuickAddVariablePrice,
        stepQuickAddQty,
        updateQuickAddTotal,
        submitQuickAdd,
    };
})();
