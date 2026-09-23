/**
 * scripts/core/utils.js - Funções utilitárias puras (sem estado, sem API).
 * Formatação de moeda, datas, quantidades e escape de HTML.
 */
window.CG = window.CG || {};

CG.utils = (function () {
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
        const locale = (window.CG && CG.i18n) ? CG.i18n.locale() : 'pt-BR';
        return date.toLocaleDateString(locale, { month: 'long', year: 'numeric' });
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

    function formatDateBR(dateStr) {
        if (!dateStr) return '-';
        const [y, m, d] = dateStr.split('-');
        return `${d}/${m}/${y.slice(-2)}`;
    }

    function currentMonthKey() {
        const now = new Date();
        return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text == null ? '' : text;
        return div.innerHTML;
    }

    return {
        formatCurrency,
        formatQuantity,
        formatMonth,
        formatDateTime,
        formatDateBR,
        currentMonthKey,
        escapeHtml,
    };
})();
