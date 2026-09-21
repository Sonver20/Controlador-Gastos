/**
 * scripts/features/balance.js - Modal de Saldo & Salário.
 */
window.CG = window.CG || {};

CG.balance = (function () {
    const { formatCurrency } = CG.utils;

    async function load() {
        try {
            const res = await CG.api.call('get_balance');
            if (res.success) {
                document.getElementById('header-balance').textContent = formatCurrency(res.balance);
            }
        } catch (e) {
            console.error('Erro ao carregar saldo:', e);
        }
    }

    async function openModal() {
        document.getElementById('balance-modal').classList.remove('hidden');
        document.getElementById('balance-modal').classList.add('flex');
        await loadModalValues();
        document.getElementById('balance-input').focus();
    }

    function closeModal() {
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

    async function loadModalValues() {
        try {
            const balRes = await CG.api.call('get_balance');
            const salRes = await CG.api.call('get_salary');
            const vacRes = await CG.api.call('get_vacation_month');
            if (balRes.success) {
                document.getElementById('balance-input').value = Number(balRes.balance) !== 0 ? balRes.balance : '';
            }
            if (salRes.success) {
                document.getElementById('salary-input').value = Number(salRes.salary) !== 0 ? salRes.salary : '';
                const salaryDisplay = document.getElementById('salary-display');
                if (salaryDisplay) {
                    salaryDisplay.textContent = salRes.salary > 0
                        ? `Salário atual: ${formatCurrency(salRes.salary)}`
                        : 'Nenhum salário configurado';
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

    async function submit() {
        const balanceVal = document.getElementById('balance-input').value.trim();
        const salaryVal = document.getElementById('salary-input').value.trim();
        const vacationVal = document.getElementById('vacation-month-input').value;
        const nextDateVal = document.getElementById('next-salary-date-input').value;

        // String crua vai para o Python (Decimal); parseFloat aqui é só validação.
        const balanceStr = balanceVal === '' ? '0' : balanceVal;
        const salaryStr = salaryVal === '' ? '0' : salaryVal;
        const vacationMonth = vacationVal === '' ? 7 : parseInt(vacationVal);

        if (isNaN(parseFloat(balanceStr)) || isNaN(parseFloat(salaryStr)) || isNaN(vacationMonth)) {
            CG.toast.show('Informe valores válidos.', 'warning');
            return;
        }

        try {
            const balRes = await CG.api.call('set_balance', balanceStr);
            const salRes = await CG.api.call('set_salary', salaryStr);
            const vacRes = await CG.api.call('set_vacation_month', vacationMonth);
            // Salva próxima data de recebimento (se preenchida) — âncora do
            // auto-crédito de 30 em 30 dias e do calendário de salários.
            let dateRes = { success: true };
            if (nextDateVal) {
                dateRes = await CG.api.call('set_next_salary_date', nextDateVal);
            }

            if (balRes.success && salRes.success && vacRes.success && dateRes.success) {
                CG.toast.show('Saldo, salário e mês de férias atualizados!', 'success');
                document.getElementById('header-balance').textContent = formatCurrency(balRes.balance);
                closeModal();
            } else {
                CG.toast.show(balRes.message || salRes.message || vacRes.message || dateRes.message, 'error');
            }
        } catch (e) {
            CG.toast.show('Erro ao salvar.', 'error');
        }
    }

    return { load, openModal, closeModal, loadModalValues, submit };
})();
