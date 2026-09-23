/**
 * scripts/features/modals.js - Modais de Editar e Excluir despesa.
 */
window.CG = window.CG || {};

CG.modals = (function () {
    const { formatCurrency } = CG.utils;

    // ------------------------------------------------------------------
    // Editar
    // ------------------------------------------------------------------
    async function openEdit(id) {
        try {
            const res = await CG.api.call('get_expense', id);
            if (!res.success || !res.data) {
                CG.toast.show(CG.i18n.t('edit_modal.not_found_error'), 'error');
                return;
            }

            CG.register.loadSubcategoryList();

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
            CG.toast.show(CG.i18n.t('edit_modal.load_error'), 'error');
        }
    }

    function closeEdit() {
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
            CG.toast.show(CG.i18n.t('edit_modal.fill_correctly_warning'), 'warning');
            return;
        }

        try {
            const res = await CG.api.call('update_expense',
                id, category, description, null, subcategory || null, quantityStr, unitPriceStr, dateVal
            );
            if (res.success) {
                CG.i18n.showApiResult(res, 'success');
                closeEdit();
                // Atualiza a listagem atual (preservando filtro de subcategoria)
                CG.tree.refreshCurrentView();
                CG.dashboard.load();
                CG.balance.load();  // saldo pode ter mudado
            } else {
                CG.i18n.showApiResult(res, 'error');
            }
        } catch (e) {
            CG.toast.show(CG.i18n.t('edit_modal.update_error_generic'), 'error');
        }
    }

    // ------------------------------------------------------------------
    // Excluir
    // ------------------------------------------------------------------
    function openDelete(id) {
        document.getElementById('delete-id').value = id;
        document.getElementById('delete-modal').classList.remove('hidden');
        document.getElementById('delete-modal').classList.add('flex');
    }

    function closeDelete() {
        document.getElementById('delete-modal').classList.add('hidden');
        document.getElementById('delete-modal').classList.remove('flex');
    }

    async function confirmDelete() {
        const id = parseInt(document.getElementById('delete-id').value);

        try {
            const res = await CG.api.call('delete_expense', id);
            if (res.success) {
                CG.i18n.showApiResult(res, 'success');
                closeDelete();
                // Excluir devolve o valor da despesa ao saldo.
                CG.tree.refreshCurrentView();
                CG.dashboard.load();
                CG.balance.load();
            } else {
                CG.i18n.showApiResult(res, 'error');
            }
        } catch (e) {
            CG.toast.show(CG.i18n.t('delete_modal.error_generic'), 'error');
        }
    }

    return {
        openEdit, closeEdit, stepEditQty, updateEditTotal, submitEdit,
        openDelete, closeDelete, confirmDelete,
    };
})();
