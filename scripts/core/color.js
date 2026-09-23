/**
 * scripts/core/color.js - Cor principal do app (persistida via backend).
 *
 * O Tailwind é carregado via CDN (assets/tailwind.js), que compila as
 * classes em tempo real no navegador observando o DOM. `tailwind.config`
 * é um Proxy: atribuir a qualquer propriedade aninhada (inclusive
 * `theme.extend.colors.primary`) já dispara uma recompilação completa,
 * então basta trocar a paleta em `tailwind.config` para toda a interface
 * (bg-primary-600, text-primary-400 etc.) atualizar instantaneamente.
 *
 * Cores pré-definidas usam as escalas oficiais do Tailwind (violet é a
 * cor histórica do app, mantida como padrão). Uma cor customizada
 * (hex escolhido livremente pelo usuário) gera uma escala 50-900 nova,
 * preservando matiz/saturação e usando uma curva de luminosidade fixa
 * para manter contraste e legibilidade consistentes.
 */
window.CG = window.CG || {};

CG.color = (function () {
    const PRESETS = {
        violet: { 50: '#f5f3ff', 100: '#ede9fe', 200: '#ddd6fe', 300: '#c4b5fd', 400: '#a78bfa', 500: '#8b5cf6', 600: '#7c3aed', 700: '#6d28d9', 800: '#5b21b6', 900: '#4c1d95' },
        blue: { 50: '#eff6ff', 100: '#dbeafe', 200: '#bfdbfe', 300: '#93c5fd', 400: '#60a5fa', 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8', 800: '#1e40af', 900: '#1e3a8a' },
        emerald: { 50: '#ecfdf5', 100: '#d1fae5', 200: '#a7f3d0', 300: '#6ee7b7', 400: '#34d399', 500: '#10b981', 600: '#059669', 700: '#047857', 800: '#065f46', 900: '#064e3b' },
        red: { 50: '#fef2f2', 100: '#fee2e2', 200: '#fecaca', 300: '#fca5a5', 400: '#f87171', 500: '#ef4444', 600: '#dc2626', 700: '#b91c1c', 800: '#991b1b', 900: '#7f1d1d' },
        orange: { 50: '#fff7ed', 100: '#ffedd5', 200: '#fed7aa', 300: '#fdba74', 400: '#fb923c', 500: '#f97316', 600: '#ea580c', 700: '#c2410c', 800: '#9a3412', 900: '#7c2d12' },
    };

    // Curva de luminosidade (0-1) usada para gerar a escala de uma cor
    // customizada, aproximando o "formato" das escalas oficiais do
    // Tailwind independentemente de quão clara/escura seja a cor de base.
    const LIGHTNESS_STEPS = { 50: 0.97, 100: 0.94, 200: 0.86, 300: 0.74, 400: 0.60, 500: 0.50, 600: 0.42, 700: 0.34, 800: 0.26, 900: 0.18 };

    function hexToHsl(hex) {
        let h = hex.replace('#', '');
        if (h.length === 3) h = h.split('').map(c => c + c).join('');
        const r = parseInt(h.substr(0, 2), 16) / 255;
        const g = parseInt(h.substr(2, 2), 16) / 255;
        const b = parseInt(h.substr(4, 2), 16) / 255;
        const max = Math.max(r, g, b), min = Math.min(r, g, b);
        let hue = 0, sat = 0;
        const light = (max + min) / 2;
        if (max !== min) {
            const d = max - min;
            sat = light > 0.5 ? d / (2 - max - min) : d / (max + min);
            switch (max) {
                case r: hue = (g - b) / d + (g < b ? 6 : 0); break;
                case g: hue = (b - r) / d + 2; break;
                case b: hue = (r - g) / d + 4; break;
            }
            hue /= 6;
        }
        return { h: hue, s: sat, l: light };
    }

    function hslToHex(h, s, l) {
        const hue2rgb = (p, q, tt) => {
            let t = tt;
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1 / 6) return p + (q - p) * 6 * t;
            if (t < 1 / 2) return q;
            if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
            return p;
        };
        let r, g, b;
        if (s === 0) {
            r = g = b = l;
        } else {
            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;
            r = hue2rgb(p, q, h + 1 / 3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1 / 3);
        }
        const toHex = x => Math.round(x * 255).toString(16).padStart(2, '0');
        return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    }

    function generateScale(baseHex) {
        const { h, s } = hexToHsl(baseHex);
        const scale = {};
        Object.keys(LIGHTNESS_STEPS).forEach(step => {
            scale[step] = hslToHex(h, s, LIGHTNESS_STEPS[step]);
        });
        return scale;
    }

    function isHex(value) {
        return typeof value === 'string' && /^#[0-9a-fA-F]{3,6}$/.test(value);
    }

    function paletteFor(value) {
        if (PRESETS[value]) return PRESETS[value];
        if (isHex(value)) return generateScale(value);
        return PRESETS.violet;
    }

    function highlightActive(value) {
        document.querySelectorAll('.color-swatch-btn').forEach(btn => {
            const active = btn.dataset.color === value;
            btn.classList.toggle('ring-2', active);
            btn.classList.toggle('ring-offset-2', active);
            btn.classList.toggle('ring-slate-400', active);
            btn.classList.toggle('dark:ring-slate-300', active);
        });
        const customInput = document.getElementById('settings-color-custom');
        if (customInput && isHex(value)) customInput.value = value;
    }

    function apply(value) {
        const scale = paletteFor(value);
        // Atribuir aqui já dispara a recompilação do Tailwind (ver
        // comentário no topo do arquivo).
        tailwind.config.theme.extend.colors.primary = scale;
        highlightActive(value);
    }

    let current = 'violet';

    async function init() {
        try {
            const res = await CG.api.call('get_primary_color');
            current = (res.success && res.color) ? res.color : 'violet';
        } catch (e) {
            console.error('Falha ao carregar cor principal:', e);
        }
        apply(current);
    }

    async function setColor(value) {
        current = value;
        apply(value);
        try {
            await CG.api.call('set_primary_color', value);
        } catch (e) {
            console.error('Falha ao salvar cor principal:', e);
        }
    }

    function getColor() {
        return current;
    }

    return { init, setColor, getColor, apply, PRESETS };
})();
