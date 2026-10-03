/**
 * scripts/core/utils.js - Funções utilitárias puras (sem estado, sem API).
 * Formatação de moeda, datas, quantidades e escape de HTML.
 */
window.CG = window.CG || {};

CG.utils = (function () {
    function formatCurrency(value) {
        // O valor numérico não muda com o idioma nem com a moeda de
        // exibição escolhida (CG.currency) — é o que o app calcula e o
        // que está no banco. O que muda é só a apresentação: em inglês,
        // a convenção de separador de milhar/decimal (1.234,56 em pt-BR
        // vira 1,234.56 em en-US); a moeda troca o símbolo/código
        // exibido (ex.: R$, US$, €), sem nenhuma conversão de valor —
        // Intl.NumberFormat resolve os dois a partir do locale e do
        // código ISO 4217 configurados.
        const locale = (window.CG && CG.i18n) ? CG.i18n.locale() : 'pt-BR';
        const currency = (window.CG && CG.currency) ? CG.currency.getCode() : 'BRL';
        return new Intl.NumberFormat(locale, {
            style: 'currency',
            currency: currency
        }).format(value || 0);
    }

    function formatQuantity(value) {
        const n = Number(value) || 0;
        // Mostra ate 3 casas decimais, mas sem zeros a mais (2 -> "2", 0.750 -> "0,75" em
        // pt-BR / "0.75" em en-US).
        const locale = (window.CG && CG.i18n) ? CG.i18n.locale() : 'pt-BR';
        return new Intl.NumberFormat(locale, { maximumFractionDigits: 3 }).format(n);
    }

    /**
     * Formata um valor monetário sem o símbolo da moeda — usado nos campos
     * de edição (preço unitário), onde o "R$" já aparece no rótulo do
     * campo. Sempre 2 casas decimais, separador conforme o idioma atual.
     */
    function formatPrice(value) {
        const n = Number(value) || 0;
        const locale = (window.CG && CG.i18n) ? CG.i18n.locale() : 'pt-BR';
        return new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
    }

    /**
     * Converte um número digitado/exibido em qualquer um dos dois
     * formatos (",": pt-BR ou ".": en-US) para um float JS de verdade.
     * Usado ao ler de volta campos numéricos que agora são <input type="text">
     * formatados com formatQuantity/formatPrice (que podem conter vírgula).
     */
    function parseLocaleNumber(str) {
        if (typeof str !== 'string') return Number(str) || 0;
        return parseFloat(str.trim().replace(',', '.')) || 0;
    }

    function adjustQuantity(value, delta) {
        const quantity = Math.max(0.001, parseLocaleNumber(value) + delta);
        return Math.round(quantity * 1000) / 1000;
    }

    function calculateSubtotal(price, quantity, isVariablePrice = false) {
        const parsedPrice = parseLocaleNumber(price);
        return isVariablePrice ? parsedPrice : parsedPrice * parseLocaleNumber(quantity);
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
        const locale = (window.CG && CG.i18n) ? CG.i18n.locale() : 'pt-BR';
        // Data e hora formatadas separadamente (e depois unidas com espaço)
        // pra manter o mesmo estilo visual anterior ("23/09/26 14:05"),
        // mas cada uma seguindo a ordem/convenção do idioma atual:
        // pt-BR -> "23/09/26 14:05" (24h) / en-US -> "09/23/26 2:05 PM" (12h).
        const datePart = new Intl.DateTimeFormat(locale, { day: '2-digit', month: '2-digit', year: '2-digit' }).format(date);
        return `${datePart} ${formatTime(isoString)}`;
    }

    /** Só o horário (usado na Árvore de Gastos, onde a data já vira um
     * cabeçalho de grupo por dia -- ver scripts/features/tree.js). */
    function formatTime(isoString) {
        if (!isoString) return '-';
        const date = new Date(isoString.replace(' ', 'T'));
        const locale = (window.CG && CG.i18n) ? CG.i18n.locale() : 'pt-BR';
        return new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' }).format(date);
    }

    function formatDateBR(dateStr) {
        if (!dateStr) return '-';
        const [y, m, d] = dateStr.split('-');
        const date = new Date(Number(y), Number(m) - 1, Number(d));
        const locale = (window.CG && CG.i18n) ? CG.i18n.locale() : 'pt-BR';
        // pt-BR -> "23/09/2026" / en-US -> "09/23/2026"
        return new Intl.DateTimeFormat(locale, { day: '2-digit', month: '2-digit', year: 'numeric' }).format(date);
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
        formatPrice,
        parseLocaleNumber,
        adjustQuantity,
        calculateSubtotal,
        formatMonth,
        formatDateTime,
        formatTime,
        formatDateBR,
        currentMonthKey,
        escapeHtml,
    };
})();
