/**
 * scripts/core/i18n.js - Internacionalização (PT / EN).
 *
 * Não guarda mais o dicionário de traduções (isso agora mora em
 * scripts/core/locales/pt_BR.js e locales/en.js, um arquivo por
 * idioma — ver o comentário em locales/pt_BR.js para o formato). Este
 * módulo só CHAMA e GERENCIA os locales: decide qual está ativo, aplica
 * as traduções no DOM e expõe t()/monthName()/weekdayShort() para o
 * resto do app.
 *
 * Elementos estáticos usam atributos `data-i18n` (texto),
 * `data-i18n-placeholder` ou `data-i18n-title`, aplicados por `apply()`.
 * Conteúdo gerado dinamicamente (features/*.js) chama
 * `CG.i18n.t(key, params)` diretamente.
 *
 * Mensagens vindas do backend (services/*.py) trazem um campo opcional
 * `key` (e `params`) além do `message` em português: `showApiResult()`
 * procura a chave no locale ativo e, se existir, usa a versão
 * traduzida; caso contrário cai para `res.message` (comportamento
 * anterior, nunca quebra).
 */
window.CG = window.CG || {};

CG.i18n = (function () {
    // Chaves para as quais um param numérico deve ser formatado como
    // moeda (na moeda configurada em CG.currency) antes de entrar no
    // texto interpolado.
    const MONEY_PARAM_KEYS = new Set(['amount', 'total']);

    const FALLBACK_LOCALE = { months: [], weekdaysShort: [], strings: {} };

    let currentLang = 'pt';

    /** Locale atualmente ativo (ou o de PT, ou um objeto vazio -- nunca undefined). */
    function activeLocale() {
        return (CG.locales && CG.locales[currentLang])
            || (CG.locales && CG.locales.pt)
            || FALLBACK_LOCALE;
    }

    /** Símbolo da moeda configurada, usado pelo token {currency} nas traduções. */
    function currencySymbol() {
        try {
            return (CG.currency && CG.currency.getSymbol()) || 'R$';
        } catch (e) {
            return 'R$';
        }
    }

    function interpolate(str, params) {
        if (!params) return str;
        return str.replace(/\{(\w+)\}/g, (match, key) => {
            if (!(key in params)) return match;
            let value = params[key];
            if (MONEY_PARAM_KEYS.has(key) && value !== null && value !== undefined && CG.utils) {
                value = CG.utils.formatCurrency(Number(value));
            }
            return value;
        });
    }

    /** Traduz uma chave para o idioma atual. */
    function t(key, params) {
        const strings = activeLocale().strings;
        const fallbackStrings = (CG.locales && CG.locales.pt && CG.locales.pt.strings) || {};
        const str = strings[key] || fallbackStrings[key] || key;
        // {currency} fica disponível em QUALQUER tradução, mesmo sem o
        // chamador passar params explicitamente (ex.: apply(), que só
        // chama t(key)) -- ver locales/pt_BR.js (balance_modal.*, etc.).
        const merged = Object.assign({ currency: currencySymbol() }, params || {});
        return interpolate(str, merged);
    }

    function getLanguage() {
        return currentLang;
    }

    /** Nome do mês (1-12) no idioma atual — usado por CG.utils.formatMonth. */
    function monthName(monthIndex1to12) {
        const months = activeLocale().months;
        return months[monthIndex1to12 - 1];
    }

    /** Abreviação do dia da semana (0=domingo .. 6=sábado) no idioma atual. */
    function weekdayShort(index0to6) {
        return activeLocale().weekdaysShort[index0to6];
    }

    /** Locale do Intl/Date a usar no idioma atual (formatação de datas). */
    function locale() {
        return currentLang === 'en' ? 'en-US' : 'pt-BR';
    }

    /**
     * Aplica as traduções a todos os elementos com data-i18n /
     * data-i18n-placeholder / data-i18n-title no documento, e ajusta
     * document.documentElement.lang.
     */
    function apply() {
        document.documentElement.lang = currentLang === 'en' ? 'en' : 'pt-BR';
        document.querySelectorAll('[data-i18n]').forEach(el => {
            el.innerHTML = t(el.getAttribute('data-i18n'));
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            el.placeholder = t(el.getAttribute('data-i18n-placeholder'));
        });
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            el.title = t(el.getAttribute('data-i18n-title'));
        });
    }

    /**
     * Re-renderiza o conteúdo dinâmico da view atualmente visível, para
     * que a troca de idioma (ou de moeda) reflita imediatamente sem
     * precisar navegar. Feito com checagens defensivas (each feature
     * pode não ter carregado ainda / não ter nada para recarregar).
     */
    function refreshDynamicContent() {
        try { CG.dashboard && CG.dashboard.load(); } catch (e) { /* view pode não estar visível ainda */ }
        try { CG.monthly && CG.monthly.renderList && !document.getElementById('monthly-list-view').classList.contains('hidden') && CG.monthly.renderList(); } catch (e) { }
        try { CG.tree && CG.tree.refreshCurrentView && CG.tree.refreshCurrentView(); } catch (e) { }
        try { CG.calendar && CG.calendar.render(); } catch (e) { }
        try { CG.balance && CG.balance.load(); } catch (e) { }
    }

    async function init() {
        try {
            const res = await CG.api.call('get_language');
            currentLang = (res.success && res.language === 'en') ? 'en' : 'pt';
        } catch (e) {
            console.error('Falha ao carregar idioma:', e);
        }
        apply();
    }

    async function setLanguage(lang) {
        currentLang = lang === 'en' ? 'en' : 'pt';
        apply();
        refreshDynamicContent();
        try {
            await CG.api.call('set_language', currentLang);
        } catch (e) {
            console.error('Falha ao salvar idioma:', e);
        }
    }

    /**
     * Mostra um toast a partir de um resultado da API (res.success,
     * res.message, res.key opcional, res.params opcional). Usa a
     * tradução de res.key quando existir; caso contrário cai para
     * res.message (texto em português vindo do backend), garantindo que
     * nada quebre para mensagens ainda não mapeadas.
     */
    function showApiResult(res, type) {
        if (!res) return;
        const kind = type || (res.success ? 'success' : 'error');
        let msg = res.message;
        const strings = activeLocale().strings;
        if (res.key && strings[res.key]) {
            const merged = Object.assign({ currency: currencySymbol() }, res.params || {});
            msg = interpolate(strings[res.key], merged);
        }
        CG.toast.show(msg, kind);
    }

    return { init, apply, t, setLanguage, getLanguage, monthName, weekdayShort, locale, showApiResult, refreshDynamicContent };
})();
