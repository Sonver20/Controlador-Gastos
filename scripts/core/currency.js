/**
 * scripts/core/currency.js - Moeda de exibição (persistida via backend).
 *
 * Guarda só uma PREFERÊNCIA DE FORMATAÇÃO: qual código ISO 4217 (ex.:
 * "BRL", "USD") usar ao exibir valores monetários via
 * CG.utils.formatCurrency (que passa esse código pro Intl.NumberFormat).
 * NÃO é conversão de moeda de verdade — o número que o usuário digitou
 * continua exatamente o mesmo, só muda o símbolo/formato exibido (o
 * cálculo de férias em services/payroll.py, por exemplo, continua sendo
 * feito com tributos brasileiros independente da moeda escolhida aqui).
 *
 * A lista fica limitada a moedas comuns de 2 casas decimais nesta
 * primeira versão — moedas que funcionam diferente (ex.: Iene, sem
 * casas decimais) ficam de fora por enquanto.
 */
window.CG = window.CG || {};

CG.currency = (function () {
    // { code, labelKey }: labelKey aponta pra tradução do rótulo do
    // botão nas Configurações (ver locales/pt_BR.js e locales/en.js).
    const OPTIONS = [
        { code: 'BRL', labelKey: 'settings.currency_brl' },
        { code: 'USD', labelKey: 'settings.currency_usd' },
        { code: 'EUR', labelKey: 'settings.currency_eur' },
        { code: 'GBP', labelKey: 'settings.currency_gbp' },
    ];

    let current = 'BRL';

    /**
     * Pede pro próprio Intl o símbolo da moeda (respeitando o locale
     * atual), em vez de mantermos uma tabela de símbolos duplicada
     * aqui -- é o mesmo Intl.NumberFormat que CG.utils.formatCurrency
     * já usa pra formatar o valor inteiro.
     */
    function symbolFor(code) {
        try {
            const locale = (CG.i18n && CG.i18n.locale) ? CG.i18n.locale() : 'pt-BR';
            const parts = new Intl.NumberFormat(locale, { style: 'currency', currency: code }).formatToParts(0);
            const symbolPart = parts.find(p => p.type === 'currency');
            return symbolPart ? symbolPart.value : code;
        } catch (e) {
            return code;
        }
    }

    function getCode() {
        return current;
    }

    function getSymbol() {
        return symbolFor(current);
    }

    function highlightActive() {
        document.querySelectorAll('.currency-btn').forEach(btn => {
            const active = btn.dataset.currency === current;
            btn.classList.toggle('bg-primary-50', active);
            btn.classList.toggle('dark:bg-primary-900/30', active);
            btn.classList.toggle('text-primary-700', active);
            btn.classList.toggle('dark:text-primary-300', active);
            btn.classList.toggle('border-primary-300', active);
            btn.classList.toggle('dark:border-primary-700', active);
        });
    }

    async function init() {
        try {
            const res = await CG.api.call('get_currency');
            current = (res.success && res.currency) ? res.currency : 'BRL';
        } catch (e) {
            console.error('Falha ao carregar moeda:', e);
        }
        highlightActive();
    }

    async function setCurrency(code) {
        current = code;
        highlightActive();
        // Re-renderiza labels estáticas com {currency} (ex.: "Saldo
        // Atual (R$)") e o conteúdo dinâmico que exibe valores
        // monetários (dashboard, saldo, árvore, calendário...).
        CG.i18n.apply();
        CG.i18n.refreshDynamicContent();
        try {
            await CG.api.call('set_currency', code);
        } catch (e) {
            console.error('Falha ao salvar moeda:', e);
        }
    }

    return { init, setCurrency, getCode, getSymbol, OPTIONS };
})();
