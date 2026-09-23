/**
 * scripts/core/settings.js - Botão de engrenagem (canto inferior
 * esquerdo da barra lateral) e o popover de Configurações: idioma
 * (CG.i18n) e cor principal (CG.color). Este módulo só cuida da UI
 * (abrir/fechar o popover, destacar a opção ativa); a lógica de cada
 * preferência mora em seu próprio módulo.
 */
window.CG = window.CG || {};

CG.settings = (function () {
    const btn = () => document.getElementById('btn-settings');
    const popover = () => document.getElementById('settings-popover');

    function open() {
        popover().classList.remove('hidden');
    }

    function close() {
        popover().classList.add('hidden');
    }

    function toggle(e) {
        e.stopPropagation();
        popover().classList.toggle('hidden');
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

    function initLanguageButtons() {
        document.querySelectorAll('.lang-btn').forEach(b => {
            b.addEventListener('click', async () => {
                await CG.i18n.setLanguage(b.dataset.lang);
                highlightLanguage();
            });
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

    function initOutsideClickToClose() {
        document.addEventListener('click', (e) => {
            const pop = popover();
            if (pop.classList.contains('hidden')) return;
            if (pop.contains(e.target) || e.target === btn() || btn().contains(e.target)) return;
            close();
        });
    }

    async function init() {
        btn().addEventListener('click', toggle);
        initLanguageButtons();
        initColorSwatches();
        initOutsideClickToClose();

        await CG.i18n.init();
        await CG.color.init();
        highlightLanguage();
    }

    return { init, open, close };
})();
