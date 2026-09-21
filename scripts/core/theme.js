/**
 * scripts/core/theme.js - Tema claro/escuro (persistido via backend).
 */
window.CG = window.CG || {};

CG.theme = (function () {
    const themeBtn = () => document.getElementById('btn-theme');
    const themeIcon = () => document.getElementById('icon-theme');

    function applyDark(isDark) {
        document.documentElement.classList.toggle('dark', isDark);
        const icon = themeIcon();
        if (icon) {
            icon.classList.toggle('ph-moon', !isDark);
            icon.classList.toggle('ph-sun', isDark);
        }
    }

    async function init() {
        try {
            const res = await CG.api.call('get_theme');
            const savedTheme = res.success ? res.theme : 'light';
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            const isDark = savedTheme === 'dark' || (!savedTheme && prefersDark);
            applyDark(isDark);
        } catch (e) {
            console.error('Falha ao carregar tema:', e);
        }

        themeBtn().addEventListener('click', toggle);
    }

    async function toggle() {
        const isDark = document.documentElement.classList.toggle('dark');
        const icon = themeIcon();
        if (icon) {
            icon.classList.toggle('ph-moon');
            icon.classList.toggle('ph-sun');
        }
        try {
            await CG.api.call('set_theme', isDark ? 'dark' : 'light');
        } catch (e) {
            console.error('Falha ao salvar tema:', e);
        }
    }

    return { init, toggle };
})();
