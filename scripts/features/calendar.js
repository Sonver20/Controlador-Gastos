/**
 * scripts/features/calendar.js - Calendário de Salários + cálculo de Férias.
 */
window.CG = window.CG || {};

CG.calendar = (function () {
    const { formatCurrency } = CG.utils;

    // ------------------------------------------------------------------
    // Calendário de salários
    // ------------------------------------------------------------------
    async function render() {
        const container = document.getElementById('salary-calendar-grid');
        if (!container) return;
        container.innerHTML = '<div class="col-span-full text-center py-12 text-slate-400"><i class="ph ph-spinner animate-spin text-3xl"></i></div>';

        try {
            const calRes = await CG.api.call('get_salary_calendar');
            container.innerHTML = '';

            if (!calRes.success) {
                container.innerHTML = `<div class="col-span-full text-center py-12 text-red-400">${CG.i18n.t('calendar.load_error')}</div>`;
                return;
            }

            if (!calRes.has_reference_date) {
                container.innerHTML = `
                    <div class="col-span-full text-center py-16 text-slate-400 space-y-3">
                        <i class="ph ph-calendar-x text-4xl block mx-auto"></i>
                        <p>${CG.i18n.t('calendar.no_reference_msg')}</p>
                        <button onclick="CG.balance.openModal()" class="text-primary-600 hover:underline text-sm font-medium">${CG.i18n.t('calendar.configure_now')}</button>
                    </div>`;
                return;
            }

            calRes.data.forEach((entry, idx) => {
                const d = new Date(entry.date + 'T00:00:00');
                const dd = String(d.getDate()).padStart(2, '0');
                const mm = String(d.getMonth() + 1).padStart(2, '0');
                const yy = String(d.getFullYear()).slice(-2);
                const dateLabel = `${dd}/${mm}/${yy}`;

                // O primeiro item da lista é sempre o próximo recebimento
                // (a lista já vem ordenada a partir de hoje, 30 em 30 dias).
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

                // Rótulo calculado no frontend (em vez do entry.label vindo
                // do backend, que só existe em português) para acompanhar
                // o idioma selecionado.
                const label = (entry.amount === null || entry.amount === undefined)
                    ? CG.i18n.t('calendar.not_configured')
                    : entry.is_vacation
                        ? CG.i18n.t('calendar.vacation_net')
                        : CG.i18n.t('calendar.monthly_salary');

                card.innerHTML = `
                    <div class="flex items-center justify-between">
                        <span class="font-bold ${entry.is_vacation ? 'text-amber-700 dark:text-amber-400' : ''}">${dateLabel}</span>
                        <div class="flex gap-1.5">
                            ${entry.is_vacation ? `<span class="text-xs bg-amber-200 dark:bg-amber-800 text-amber-800 dark:text-amber-200 px-2 py-0.5 rounded-full font-medium">${CG.i18n.t('calendar.vacation_badge')}</span>` : ''}
                            ${isNext ? `<span class="text-xs bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 px-2 py-0.5 rounded-full font-medium">${CG.i18n.t('calendar.next_badge')}</span>` : ''}
                        </div>
                    </div>
                    <div class="mt-1">
                        <p class="text-lg font-semibold ${entry.is_vacation ? 'text-amber-700 dark:text-amber-400' : 'text-primary-600 dark:text-primary-400'}">${valorDisplay}</p>
                        <p class="text-xs text-slate-400">${entry.is_vacation ? CG.i18n.t('calendar.click_details') : label}</p>
                    </div>
                `;

                if (entry.is_vacation) {
                    card.addEventListener('click', () => openFeriasModal());
                }

                container.appendChild(card);
            });
        } catch (e) {
            container.innerHTML = `<div class="col-span-full text-center py-12 text-red-400">${CG.i18n.t('calendar.load_error')}</div>`;
        }
    }

    // ------------------------------------------------------------------
    // Modal de férias
    // ------------------------------------------------------------------
    async function openFeriasModal() {
        const modal = document.getElementById('ferias-modal');
        const resultDiv = document.getElementById('ferias-result');
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        resultDiv.innerHTML = '';

        // Pega o salário configurado como default
        try {
            const res = await CG.api.call('get_salary');
            const input = document.getElementById('ferias-salario-input');
            if (res.success && res.salary > 0) {
                input.value = CG.utils.formatPrice(res.salary);
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
        const salarioStr = input.value.trim().replace(',', '.');
        const salario = parseFloat(salarioStr);
        const resultDiv = document.getElementById('ferias-result');

        if (!salarioStr || isNaN(salario) || salario <= 0) {
            resultDiv.innerHTML = `<p class="text-amber-600 dark:text-amber-400 text-sm">${CG.i18n.t('ferias.invalid_salary_warning')}</p>`;
            return;
        }

        try {
            const res = await CG.api.call('calcular_ferias', salarioStr);
            if (res.success) {
                resultDiv.innerHTML = `
                    <div class="space-y-2 text-sm">
                        <div class="flex justify-between"><span class="text-slate-500 dark:text-slate-400">${CG.i18n.t('ferias.result_gross')}</span><span class="font-medium">${formatCurrency(res.salario_bruto)}</span></div>
                        <div class="flex justify-between"><span class="text-slate-500 dark:text-slate-400">${CG.i18n.t('ferias.result_third')}</span><span class="font-medium">${formatCurrency(res.terco_constitucional)}</span></div>
                        <div class="flex justify-between border-t border-slate-200 dark:border-slate-700 pt-1"><span class="text-slate-500 dark:text-slate-400">${CG.i18n.t('ferias.result_total_gross')}</span><span class="font-semibold">${formatCurrency(res.total_bruto)}</span></div>
                        <div class="flex justify-between text-red-600 dark:text-red-400"><span>${CG.i18n.t('ferias.result_inss')}</span><span>-${formatCurrency(res.inss)}</span></div>
                        <div class="flex justify-between"><span class="text-slate-500 dark:text-slate-400">${CG.i18n.t('ferias.result_irrf_base')}</span><span>${formatCurrency(res.base_irrf)}</span></div>
                        <div class="flex justify-between text-red-600 dark:text-red-400"><span>${CG.i18n.t('ferias.result_irrf_calc')}</span><span>-${formatCurrency(res.irrf_calculado)}</span></div>
                        <div class="flex justify-between text-emerald-600 dark:text-emerald-400"><span>${CG.i18n.t('ferias.result_additional_discount')}</span><span>+${formatCurrency(res.desconto_adicional)}</span></div>
                        <div class="flex justify-between border-t border-slate-200 dark:border-slate-700 pt-1"><span class="text-slate-500 dark:text-slate-400">${CG.i18n.t('ferias.result_irrf_final')}</span><span class="font-medium">-${formatCurrency(res.irrf_final)}</span></div>
                        <div class="flex justify-between text-lg font-bold text-primary-600 dark:text-primary-400 pt-1"><span>${CG.i18n.t('ferias.result_net')}</span><span>${formatCurrency(res.salario_liquido)}</span></div>
                    </div>
                `;
            } else {
                resultDiv.innerHTML = `<p class="text-red-600 dark:text-red-400 text-sm">${res.message}</p>`;
            }
        } catch (e) {
            resultDiv.innerHTML = `<p class="text-red-600 dark:text-red-400 text-sm">${CG.i18n.t('ferias.calc_error')}</p>`;
        }
    }

    return { render, openFeriasModal, closeFeriasModal, calcularFerias };
})();
