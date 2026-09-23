/**
 * scripts/features/dashboard.js - Dashboard (resumo mensal, estatísticas).
 */
window.CG = window.CG || {};

CG.dashboard = (function () {
    const { formatCurrency, formatMonth } = CG.utils;

    async function load() {
        const tbody = document.getElementById('dash-months-body');
        try {
            const res = await CG.api.call('get_months_summary');
            tbody.innerHTML = '';

            if (!res.success || !res.data.length) {
                tbody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-slate-400">${CG.i18n.t('dashboard.no_expenses')}</td></tr>`;
                document.getElementById('dash-current-month').textContent = formatCurrency(0);
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
                    <td class="px-6 py-4 text-slate-500 dark:text-slate-400">${CG.i18n.t('common.count_expenses', { count: row.count })}</td>
                    <td class="px-6 py-4 text-right font-semibold text-primary-600 dark:text-primary-400">${formatCurrency(row.total)}</td>
                    <td class="px-6 py-4 text-right">
                        <button onclick="CG.tree.viewMonthCategories('${row.month}')" class="text-sm text-primary-600 hover:underline">${CG.i18n.t('dashboard.view_details')}</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            document.getElementById('dash-current-month').textContent = formatCurrency(currentMonthTotal);
            document.getElementById('dash-total-count').textContent = totalCount.toString();

            // Maior categoria do mês atual
            if (currentMonthTotal > 0) {
                const catRes = await CG.api.call('get_categories_by_month', currentMonthStr);
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
            console.error('Erro ao carregar dashboard:', e);
            CG.toast.show(CG.i18n.t('dashboard.load_error'), 'error');
        }
    }

    return { load };
})();
