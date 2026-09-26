/**
 * scripts/features/register.js - Nova Despesa.
 *
 * Lista de produtos com categoria/subcategoria compartilhadas: cada
 * produto tem nome, preço unitário e quantidade com stepper +/-.
 * Também mantém os datalists de categorias/subcategorias usados por
 * outros módulos (modais de edição, Despesas Mensais).
 */
window.CG = window.CG || {};

CG.register = (function () {
    const { formatCurrency } = CG.utils;
    let productRowCounter = 0;

    // ------------------------------------------------------------------
    // Datalists (compartilhado com edit modal e Despesas Mensais)
    // ------------------------------------------------------------------
    async function loadCategoryList() {
        try {
            const res = await CG.api.call('get_all_categories');
            if (res.success) {
                const datalist = document.getElementById('category-list');
                if (!datalist) return;
                datalist.innerHTML = '';
                res.data.forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat;
                    datalist.appendChild(opt);
                });
            }
        } catch (e) {
            console.error('Falha ao carregar categorias:', e);
        }
    }

    async function loadSubcategoryList() {
        try {
            const res = await CG.api.call('get_all_subcategories');
            if (res.success) {
                const datalist = document.getElementById('subcategory-list');
                if (!datalist) return;
                datalist.innerHTML = '';
                res.data.forEach(sub => {
                    const opt = document.createElement('option');
                    opt.value = sub;
                    datalist.appendChild(opt);
                });
            }
        } catch (e) {
            console.error('Falha ao carregar subcategorias:', e);
        }
    }

    // ------------------------------------------------------------------
    // Linhas de produto
    // ------------------------------------------------------------------
    function addProductRow() {
        const list = document.getElementById('reg-products-list');
        const rowId = `prow-${++productRowCounter}`;
        const row = document.createElement('div');
        row.className = 'product-row flex flex-col sm:flex-row gap-3 items-stretch sm:items-center bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 border border-slate-200 dark:border-slate-700';
        row.dataset.rowId = rowId;
        row.innerHTML = `
            <input type="text" class="product-name flex-1 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 outline-none transition text-sm"
                placeholder="${CG.i18n.t('register.product_name_placeholder')}" oninput="CG.register.updateProductsGrandTotal()">
            <input type="text" inputmode="decimal" class="product-price w-full sm:w-28 px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 outline-none transition text-sm"
                placeholder="${CG.i18n.t('register.product_price_placeholder')}" oninput="CG.register.updateProductsGrandTotal()">
            <div class="flex items-center gap-2 justify-center">
                <button type="button" onclick="CG.register.stepProductQty('${rowId}', -1)"
                    class="w-8 h-8 shrink-0 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition font-bold">-</button>
                <input type="text" inputmode="decimal" class="product-qty w-16 text-center px-2 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:ring-2 focus:ring-primary-500 outline-none transition text-sm"
                    value="1" oninput="CG.register.updateProductsGrandTotal()">
                <button type="button" onclick="CG.register.stepProductQty('${rowId}', 1)"
                    class="w-8 h-8 shrink-0 flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 transition font-bold">+</button>
            </div>
            <span class="product-subtotal text-sm font-semibold text-slate-600 dark:text-slate-300 w-24 text-right shrink-0">${formatCurrency(0)}</span>
            <button type="button" onclick="CG.register.removeProductRow('${rowId}')"
                class="text-red-500 hover:text-red-700 dark:hover:text-red-400 p-1 shrink-0" title="${CG.i18n.t('register.remove_product_title')}">
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
        // Sempre deixa pelo menos uma linha disponível
        if (list.children.length === 0) addProductRow();
        updateProductsGrandTotal();
    }

    function stepProductQty(rowId, delta) {
        const row = document.getElementById('reg-products-list').querySelector(`[data-row-id="${rowId}"]`);
        if (!row) return;
        const qtyInput = row.querySelector('.product-qty');
        let qty = CG.utils.parseLocaleNumber(qtyInput.value);
        qty = Math.max(0.001, qty + delta);
        // Arredonda para evitar sobra de ponto flutuante (ex: 1.9999999999)
        qtyInput.value = CG.utils.formatQuantity(Math.round(qty * 1000) / 1000);
        updateProductsGrandTotal();
    }

    function updateProductsGrandTotal() {
        const rows = document.querySelectorAll('#reg-products-list .product-row');
        let grandTotal = 0;
        rows.forEach(row => {
            const price = CG.utils.parseLocaleNumber(row.querySelector('.product-price').value);
            const qty = CG.utils.parseLocaleNumber(row.querySelector('.product-qty').value);
            const subtotal = price * qty;
            row.querySelector('.product-subtotal').textContent = formatCurrency(subtotal);
            grandTotal += subtotal;
        });
        document.getElementById('reg-grand-total').textContent = formatCurrency(grandTotal);
    }

    // ------------------------------------------------------------------
    // Submissão
    // ------------------------------------------------------------------
    async function submitProductsExpense() {
        const category = document.getElementById('reg-category').value.trim();
        const subcategory = document.getElementById('reg-subcategory').value.trim();

        if (!category) {
            CG.toast.show(CG.i18n.t('register.category_required_warning'), 'warning');
            return;
        }

        const rows = document.querySelectorAll('#reg-products-list .product-row');
        const products = [];
        let hasInvalidRow = false;

        rows.forEach(row => {
            const name = row.querySelector('.product-name').value.trim();
            const priceStr = row.querySelector('.product-price').value.trim().replace(',', '.');
            const qtyStr = row.querySelector('.product-qty').value.trim().replace(',', '.');

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
            CG.toast.show(CG.i18n.t('register.fill_correctly_warning'), 'warning');
            return;
        }
        if (products.length === 0) {
            CG.toast.show(CG.i18n.t('register.add_one_warning'), 'warning');
            return;
        }

        try {
            const res = await CG.api.call('add_expenses_structured', category, subcategory || null, products);
            if (res.success) {
                CG.i18n.showApiResult(res, 'success');
                clearRegisterForm();
                loadCategoryList();
                loadSubcategoryList();
                CG.balance.load();  // atualiza saldo no header
            } else {
                CG.i18n.showApiResult(res, 'error');
            }
        } catch (e) {
            CG.toast.show(CG.i18n.t('register.comm_error'), 'error');
        }
    }

    function clearRegisterForm() {
        document.getElementById('reg-category').value = '';
        document.getElementById('reg-subcategory').value = '';
        document.getElementById('reg-products-list').innerHTML = '';
        addProductRow();
    }

    /** Chamado ao entrar na view: garante datalists e uma linha de produto. */
    function onEnterView() {
        loadCategoryList();
        loadSubcategoryList();
        if (document.getElementById('reg-products-list').children.length === 0) {
            addProductRow();
        }
    }

    return {
        loadCategoryList,
        loadSubcategoryList,
        addProductRow,
        removeProductRow,
        stepProductQty,
        updateProductsGrandTotal,
        submitProductsExpense,
        clearRegisterForm,
        onEnterView,
    };
})();
