/**
 * scripts/features/monthly.js - Despesas Mensais.
 *
 * Templates de despesas recorrentes: cada grupo tem um nome e uma lista
 * de itens, onde CADA ITEM tem sua própria categoria/subcategoria (diferente
 * da Nova Despesa, que compartilha uma categoria para todos os produtos).
 *
 * Todo mês, ao abrir o app, os grupos são aplicados automaticamente: os
 * itens viram despesas no banco de dados e o total é debitado do saldo.
 * Também é possível aplicar manualmente com "Aplicar agora".
 */
window.CG = window.CG || {};

CG.monthly = (function () {
    const { formatCurrency, formatQuantity, formatMonth, escapeHtml } = CG.utils;
    let itemRowCounter = 0;

    // ==================================================================
    // LISTAGEM
    // ==================================================================
    async function renderList() {
        const container = document.getElementById('monthly-groups-list');
        if (!container) return;
        container.innerHTML = '<div class="text-center py-12 text-slate-400 col-span-full"><i class="ph ph-spinner animate-spin text-3xl"></i></div>';

        try {
            const res = await CG.api.call('get_monthly_groups');
            container.innerHTML = '';

            if (!res.success || !res.data.length) {
                container.innerHTML = `
                    <div class="col-span-full text-center py-16 text-slate-400 space-y-3">
                        <i class="ph ph-repeat text-4xl block mx-auto"></i>
                        <p>${CG.i18n.t('monthly.empty_title')}</p>
                        <p class="text-sm">${CG.i18n.t('monthly.empty_desc')}</p>
                    </div>`;
                return;
            }

            const currentMonth = CG.utils.currentMonthKey();

            res.data.forEach(group => {
                const isApplied = group.last_applied_month === currentMonth;

                const card = document.createElement('div');
                card.className = 'bg-card-light dark:bg-card-dark rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 overflow-hidden';

                const itemsHtml = group.items.map(item => `
                    <div class="flex items-center justify-between gap-3 py-1.5 text-sm">
                        <div class="min-w-0">
                            <span class="font-medium">${escapeHtml(item.description)}</span>
                            <span class="text-xs text-slate-400 ml-1">(${escapeHtml(item.category)}${item.subcategory ? ' > ' + escapeHtml(item.subcategory) : ''})</span>
                        </div>
                        <div class="text-right shrink-0">
                            <span class="font-semibold">${formatCurrency(item.amount)}</span>
                            ${Number(item.quantity) !== 1 ? `<span class="text-xs text-slate-400 block">${formatQuantity(item.quantity)} × ${formatCurrency(item.unit_price)}</span>` : ''}
                        </div>
                    </div>
                `).join('');

                card.innerHTML = `
                    <div class="px-5 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between gap-3">
                        <div class="min-w-0">
                            <h4 class="font-bold truncate">${escapeHtml(group.name)}</h4>
                            <p class="text-xs text-slate-400">${CG.i18n.t('monthly.items_count', { count: group.items.length })}</p>
                        </div>
                        <div class="flex items-center gap-2 shrink-0">
                            ${isApplied
                                ? '<span class="text-xs bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 px-2 py-1 rounded-full font-medium"><i class="ph ph-check"></i> ' + CG.i18n.t('monthly.applied_in', { month: formatMonth(group.last_applied_month) }) + '</span>'
                                : '<span class="text-xs bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 px-2 py-1 rounded-full font-medium"><i class="ph ph-clock"></i> ' + CG.i18n.t('monthly.pending') + '</span>'}
                        </div>
                    </div>
                    <div class="px-5 py-3 divide-y divide-slate-100 dark:divide-slate-700/60">${itemsHtml}</div>
                    <div class="px-5 py-3 bg-slate-50 dark:bg-slate-800/40 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
                        <span class="text-sm text-slate-500 dark:text-slate-400">${CG.i18n.t('monthly.monthly_total')}</span>
                        <span class="font-bold text-primary-600 dark:text-primary-400">${formatCurrency(group.total)}</span>
                    </div>
                    <div class="px-5 py-3 border-t border-slate-200 dark:border-slate-700 flex gap-2">
                        <button onclick="CG.monthly.openForm(${group.id})"
                            class="px-3 py-1.5 rounded-lg text-sm border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition flex items-center gap-1">
                            <i class="ph ph-pencil-simple"></i> ${CG.i18n.t('monthly.edit_button')}
                        </button>
                        <button onclick="CG.monthly.applyGroup(${group.id})"
                            class="px-3 py-1.5 rounded-lg text-sm bg-primary-600 hover:bg-primary-700 text-white transition flex items-center gap-1" title="${CG.i18n.t('monthly.apply_title')}">
                            <i class="ph ph-lightning"></i> ${CG.i18n.t('monthly.apply_button')}
                        </button>
                        <button onclick="CG.monthly.deleteGroup(${group.id})"
                            class="px-3 py-1.5 rounded-lg text-sm border border-red-200 dark:border-red-900/50 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition flex items-center gap-1 ml-auto">
                            <i class="ph ph-trash"></i> ${CG.i18n.t('monthly.delete_button')}
                        </button>
                    </div>
                `;
                container.appendChild(card);
            });
        } catch (e) {
            container.innerHTML = `<div class="col-span-full text-center py-12 text-red-400">${CG.i18n.t('monthly.load_error')}</div>`;
        }
    }

    // ==================================================================
    // FORMULÁRIO (novo / editar)
    // ==================================================================
    function openForm(groupId = null) {
        CG.state.editingMonthlyGroupId = groupId;
        document.getElementById('monthly-list-view').classList.add('hidden');
        document.getElementById('monthly-form-view').classList.remove('hidden');

        document.getElementById('monthly-group-name').value = '';
        document.getElementById('monthly-items-list').innerHTML = '';
        document.getElementById('monthly-form-title').textContent = groupId ? CG.i18n.t('monthly.form_edit_title') : CG.i18n.t('monthly.form_new_title');
        addItemRow();

        if (groupId) {
            // Carrega os dados do grupo para edição
            CG.api.call('get_monthly_groups').then(res => {
                if (!res.success) return;
                const group = res.data.find(g => g.id === groupId);
                if (!group) return;
                document.getElementById('monthly-group-name').value = group.name;
                document.getElementById('monthly-items-list').innerHTML = '';
                group.items.forEach(item => {
                    addItemRow(item);
                });
            }).catch(e => console.error(e));
        }
    }

    function closeForm() {
        CG.state.editingMonthlyGroupId = null;
        document.getElementById('monthly-form-view').classList.add('hidden');
        document.getElementById('monthly-list-view').classList.remove('hidden');
        renderList();
    }

    /**
     * Adiciona uma linha de item. Cada item tem CATEGORIA PRÓPRIA
     * (é o que diferencia Despesas Mensais da Nova Despesa).
     * `preset` opcional: {category, subcategory, description, unit_price, quantity}.
     */
    function addItemRow(preset = null) {
        const list = document.getElementById('monthly-items-list');
        const rowId = `mrow-${++itemRowCounter}`;
        const row = document.createElement('div');
        row.className = 'monthly-item-row bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 border border-slate-200 dark:border-slate-700 space-y-3';
        row.dataset.rowId = rowId;
        row.innerHTML = `
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input type="text" class="mi-category px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 outline-none transition text-sm" list="category-list"
                    placeholder="${CG.i18n.t('monthly.item_category_placeholder')}" oninput="CG.monthly.updateFormTotal()">
                <input type="text" class="mi-subcategory px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 outline-none transition text-sm" list="subcategory-list"
                    placeholder="${CG.i18n.t('monthly.item_subcategory_placeholder')}" oninput="CG.monthly.updateFormTotal()">
            </div>
            <div class="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center">
                <input type="text" class="mi-name flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 outline-none transition text-sm"
                    placeholder="${CG.i18n.t('monthly.item_name_placeholder')}" oninput="CG.monthly.updateFormTotal()">
                <input type="number" class="mi-price w-full sm:w-28 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 outline-none transition text-sm"
                    placeholder="${CG.i18n.t('monthly.item_price_placeholder')}" step="0.01" min="0" oninput="CG.monthly.updateFormTotal()">
                <div class="flex items-center gap-2 justify-center">
                    <button type="button" onclick="CG.monthly.stepItemQty('${rowId}', -1)"
                        class="w-8 h-8 shrink-0 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition font-bold">-</button>
                    <input type="number" class="mi-qty w-16 text-center px-2 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 outline-none transition text-sm"
                        value="1" step="0.001" min="0.001" oninput="CG.monthly.updateFormTotal()">
                    <button type="button" onclick="CG.monthly.stepItemQty('${rowId}', 1)"
                        class="w-8 h-8 shrink-0 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition font-bold">+</button>
                </div>
                <span class="mi-subtotal text-sm font-semibold text-slate-600 dark:text-slate-300 w-24 text-right shrink-0">${formatCurrency(0)}</span>
                <button type="button" onclick="CG.monthly.removeItemRow('${rowId}')"
                    class="text-red-500 hover:text-red-700 dark:hover:text-red-400 p-1 shrink-0" title="${CG.i18n.t('monthly.remove_item_title')}">
                    <i class="ph ph-trash text-lg"></i>
                </button>
            </div>
        `;
        list.appendChild(row);

        if (preset) {
            row.querySelector('.mi-category').value = preset.category || '';
            row.querySelector('.mi-subcategory').value = preset.subcategory || '';
            row.querySelector('.mi-name').value = preset.description || '';
            row.querySelector('.mi-price').value = preset.unit_price || '';
            row.querySelector('.mi-qty').value = preset.quantity || '1';
        }
        updateFormTotal();
    }

    function removeItemRow(rowId) {
        const list = document.getElementById('monthly-items-list');
        const row = list.querySelector(`[data-row-id="${rowId}"]`);
        if (row) row.remove();
        if (list.children.length === 0) addItemRow();
        updateFormTotal();
    }

    function stepItemQty(rowId, delta) {
        const row = document.getElementById('monthly-items-list').querySelector(`[data-row-id="${rowId}"]`);
        if (!row) return;
        const qtyInput = row.querySelector('.mi-qty');
        let qty = parseFloat(qtyInput.value) || 0;
        qty = Math.max(0.001, qty + delta);
        qtyInput.value = Math.round(qty * 1000) / 1000;
        updateFormTotal();
    }

    function updateFormTotal() {
        const rows = document.querySelectorAll('#monthly-items-list .monthly-item-row');
        let grandTotal = 0;
        rows.forEach(row => {
            const price = parseFloat(row.querySelector('.mi-price').value) || 0;
            const qty = parseFloat(row.querySelector('.mi-qty').value) || 0;
            const subtotal = price * qty;
            row.querySelector('.mi-subtotal').textContent = formatCurrency(subtotal);
            grandTotal += subtotal;
        });
        document.getElementById('monthly-grand-total').textContent = formatCurrency(grandTotal);
    }

    async function submitForm() {
        const name = document.getElementById('monthly-group-name').value.trim();
        if (!name) {
            CG.toast.show(CG.i18n.t('monthly.name_required'), 'warning');
            return;
        }

        const rows = document.querySelectorAll('#monthly-items-list .monthly-item-row');
        const items = [];
        let hasInvalidRow = false;

        rows.forEach(row => {
            const category = row.querySelector('.mi-category').value.trim();
            const subcategory = row.querySelector('.mi-subcategory').value.trim();
            const description = row.querySelector('.mi-name').value.trim();
            const priceStr = row.querySelector('.mi-price').value.trim();
            const qtyStr = row.querySelector('.mi-qty').value.trim();

            // Linha totalmente vazia (clicou em "+" e não usou) -- ignora
            if (!category && !description && !priceStr) return;

            const price = parseFloat(priceStr);
            const qty = parseFloat(qtyStr);
            if (!category || !description || !priceStr || isNaN(price) || price <= 0 || !qtyStr || isNaN(qty) || qty <= 0) {
                hasInvalidRow = true;
                return;
            }
            items.push({
                category,
                subcategory: subcategory || null,
                description,
                unit_price: priceStr,
                quantity: qtyStr,
            });
        });

        if (hasInvalidRow) {
            CG.toast.show(CG.i18n.t('monthly.invalid_items_warning'), 'warning');
            return;
        }
        if (items.length === 0) {
            CG.toast.show(CG.i18n.t('monthly.add_one_item_warning'), 'warning');
            return;
        }

        try {
            const res = await CG.api.call('save_monthly_group', name, items, CG.state.editingMonthlyGroupId);
            if (res.success) {
                CG.i18n.showApiResult(res, 'success');
                CG.register.loadCategoryList();
                CG.register.loadSubcategoryList();
                closeForm();
            } else {
                CG.i18n.showApiResult(res, 'error');
            }
        } catch (e) {
            CG.toast.show(CG.i18n.t('monthly.save_error'), 'error');
        }
    }

    // ==================================================================
    // AÇÕES
    // ==================================================================
    async function deleteGroup(groupId) {
        try {
            const res = await CG.api.call('delete_monthly_group', groupId);
            if (res.success) {
                CG.i18n.showApiResult(res, 'success');
                renderList();
            } else {
                CG.i18n.showApiResult(res, 'error');
            }
        } catch (e) {
            CG.toast.show(CG.i18n.t('monthly.delete_error_generic'), 'error');
        }
    }

    async function applyGroup(groupId) {
        try {
            const res = await CG.api.call('apply_monthly_group', groupId);
            if (res.success) {
                CG.i18n.showApiResult(res, 'success');
                CG.balance.load();
                CG.dashboard.load();
                renderList();
            } else {
                CG.i18n.showApiResult(res, 'error');
            }
        } catch (e) {
            CG.toast.show(CG.i18n.t('monthly.apply_error_generic'), 'error');
        }
    }

    /**
     * Verificação automática na inicialização do app: aplica os grupos
     * do mês corrente que ainda não foram lançados e debita do saldo.
     */
    async function checkAuto() {
        try {
            const res = await CG.api.call('check_monthly_expenses');
            if (res.success && res.applied_count > 0) {
                CG.i18n.showApiResult(res, 'success');
                CG.balance.load();
                CG.dashboard.load();
            }
        } catch (e) {
            console.error('Erro na verificação automática de despesas mensais:', e);
        }
    }

    function onEnterView() {
        CG.register.loadCategoryList();
        CG.register.loadSubcategoryList();
        closeForm();
    }

    return {
        renderList,
        openForm,
        closeForm,
        addItemRow,
        removeItemRow,
        stepItemQty,
        updateFormTotal,
        submitForm,
        deleteGroup,
        applyGroup,
        checkAuto,
        onEnterView,
    };
})();
