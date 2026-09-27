/**
 * scripts/core/theme.js - Tema claro/escuro (persistido via backend).
 *
 * Antes era um botão único de alternância (ícone lua/sol) no cabeçalho;
 * agora o tema é escolhido por dois botões explícitos ("Claro"/"Escuro")
 * dentro de Configurações → Geral (mesmo padrão de CG.color/CG.currency:
 * `data-theme` no botão + `setTheme()`), já que o cabeçalho passou a
 * abrir a janela de Configurações em vez de alternar o tema direto.
 * `toggle()` continua exposto por compatibilidade com qualquer atalho
 * de teclado que já exista fora deste módulo.
 */
window.CG = window.CG || {};

CG.theme = (function () {
    let isDark = false;

    function applyDark(dark) {
        document.documentElement.classList.toggle('dark', dark);
    }

    function highlightActive() {
        document.querySelectorAll('.theme-btn').forEach(btn => {
            const active = (btn.dataset.theme === 'dark') === isDark;
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
            const res = await CG.api.call('get_theme');
            const savedTheme = res.success ? res.theme : 'light';
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            isDark = savedTheme === 'dark' || (!savedTheme && prefersDark);
            applyDark(isDark);
        } catch (e) {
            console.error('Falha ao carregar tema:', e);
        }
        highlightActive();
    }

    async function setTheme(theme) {
        isDark = theme === 'dark';
        applyDark(isDark);
        highlightActive();
        try {
            await CG.api.call('set_theme', isDark ? 'dark' : 'light');
        } catch (e) {
            console.error('Falha ao salvar tema:', e);
        }
    }

    function toggle() {
        return setTheme(isDark ? 'light' : 'dark');
    }

    return { init, setTheme, toggle };
})();
