/**
 * scripts/core/settings.js - Janela de Configurações.
 *
 * Antes era uma engrenagem no rodapé da barra lateral que abria um
 * mini popover ancorado. Agora a engrenagem fica no cabeçalho, no lugar
 * onde ficava o botão de tema (`#btn-settings`), e abre uma janela no
 * mesmo formato dos outros modais do app (edit-modal, balance-modal,
 * ferias-modal): overlay central, com um menu de categorias à esquerda
 * (por enquanto só "Geral") e o conteúdo da categoria à direita.
 *
 * Este módulo só cuida da abertura/fechamento da janela e de ligar cada
 * controle ao módulo dono da preferência (CG.theme, CG.i18n, CG.color,
 * CG.currency) — a lógica de cada preferência continua isolada no seu
 * próprio módulo, só a UI de agrupá-las mudou.
 */
window.CG = window.CG || {};

CG.settings = (function () {
    const modal = () => document.getElementById('settings-modal');

    function open() {
        const m = modal();
        if (!m) return;
        m.classList.remove('hidden');
        m.classList.add('flex');
    }

    function close() {
        const m = modal();
        if (!m) return;
        m.classList.add('hidden');
        m.classList.remove('flex');
    }

    function toggle(e) {
        if (e) e.stopPropagation();
        const m = modal();
        if (!m) return;
        m.classList.contains('hidden') ? open() : close();
    }

    function initThemeButtons() {
        document.querySelectorAll('.theme-btn').forEach(b => {
            b.addEventListener('click', () => CG.theme.setTheme(b.dataset.theme));
        });
    }

    function initLanguageButtons() {
        document.querySelectorAll('.lang-btn').forEach(b => {
            b.addEventListener('click', async () => {
                await CG.i18n.setLanguage(b.dataset.lang);
                highlightLanguage();
            });
        });
    }

    function highlightLanguage() {
        const current = CG.i18n.getLanguage();
        document.querySelectorAll('.lang-btn').forEach(b => {
            const active = b.dataset.lang === current;
            b.classList.toggle('bg-primary-50', active);
            b.classList.toggle('dark:bg-primary-900/30', active);
            b.classList.toggle('text-primary-700', active);
            b.classList.toggle('dark:text-primary-300', active);
            b.classList.toggle('border-primary-300', active);
            b.classList.toggle('dark:border-primary-700', active);
        });
    }

    function initColorSwatches() {
        document.querySelectorAll('.color-swatch-btn[data-color]').forEach(b => {
            b.addEventListener('click', () => CG.color.setColor(b.dataset.color));
        });
        const customInput = document.getElementById('settings-color-custom');
        if (customInput) {
            customInput.addEventListener('input', () => CG.color.setColor(customInput.value));
        }
    }

    function initCurrencyButtons() {
        document.querySelectorAll('.currency-btn').forEach(b => {
            b.addEventListener('click', () => CG.currency.setCurrency(b.dataset.currency));
        });
    }

    /**
     * Categorias dentro da janela (só "Geral" por enquanto). Já deixado
     * genérico para quando novas categorias forem adicionadas: cada
     * botão de categoria mostra o painel correspondente e esconde os
     * outros.
     */
    function initCategoryNav() {
        document.querySelectorAll('.settings-category-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.settings-category-btn').forEach(b => {
                    const active = b === btn;
                    b.classList.toggle('bg-primary-50', active);
                    b.classList.toggle('dark:bg-primary-900/30', active);
                    b.classList.toggle('text-primary-700', active);
                    b.classList.toggle('dark:text-primary-300', active);
                });
                document.querySelectorAll('.settings-category-panel').forEach(panel => {
                    panel.classList.toggle('hidden', panel.id !== `settings-category-${btn.dataset.category}`);
                });
            });
        });
    }

    /**
     * Só inicializa idioma, cor e moeda — o tema é inicializado à parte
     * por scripts/main.js (`CG.theme.init()`), bem no começo do boot,
     * pra evitar um flash do tema errado antes do resto (idioma/cor/
     * moeda) terminar de carregar.
     */
    async function init() {
        const settingsBtn = document.getElementById('btn-settings');
        if (settingsBtn) settingsBtn.addEventListener('click', toggle);
        const closeBtn = document.getElementById('settings-close');
        if (closeBtn) closeBtn.addEventListener('click', close);

        initCategoryNav();
        initThemeButtons();
        initLanguageButtons();
        initColorSwatches();
        initCurrencyButtons();

        await CG.currency.init();
        await CG.i18n.init();
        await CG.color.init();
        highlightLanguage();
    }

    return { init, open, close, toggle };
})();
