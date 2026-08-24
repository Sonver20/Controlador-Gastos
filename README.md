# Controlador de Gastos

Aplicativo desktop nativo para controle financeiro pessoal, construído com **Python + PyWebView** e interface moderna em **HTML/CSS/JS**.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![PyWebView](https://img.shields.io/badge/PyWebView-5.0+-green?logo=python)
![SQLite](https://img.shields.io/badge/SQLite-3-orange?logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Sobre

O **Controlador de Gastos** é um app de gerenciamento financeiro pessoal que roda nativamente no **Ubuntu Linux** (e compatíveis). Ele foi projetado para ser simples, rápido e funcional — sem depender de serviços em nuvem ou conexão com a internet.

Toda a lógica de negócio e persistência de dados roda localmente via **SQLite**, enquanto a interface é uma **Single Page Application (SPA)** moderna com tema claro/escuro, animações suaves e navegação intuitiva.

---

## Funcionalidades

| Recurso | Descrição |
|---------|-----------|
| **Cadastro de Despesas** | Adicione despesas individuais com categoria, descrição e valor |
| **Cadastro em Massa** | Cole múltiplas linhas no formato `Descrição, Valor` e importe de uma vez |
| **Árvore de Gastos** | Navegue hierarquicamente: **Ano/Mês → Categoria → Despesas** |
| **Dashboard** | Resumo mensal com totais, contagem e maior categoria |
| **Parser de Texto** | Cole notificações bancárias — o app extrai descrição e valor automaticamente |
| **Saldo da Conta** | Informe seu saldo atual — o app subtrai automaticamente a cada despesa |
| **Salário Mensal** | Configure seu salário — creditado automaticamente no início de cada mês |
| **Tema Claro/Escuro** | Alterne entre temas com persistência no disco |
| **Edição/Exclusão** | Edite ou exclua despesas diretamente na árvore de gastos |

---

## Screenshots

*(Adicione screenshots do app aqui)*

---

## Requisitos

- **Ubuntu Linux** (ou derivados: Mint, Pop!_OS, etc.)
- **Python 3.10+**
- Dependências do sistema GTK/WebKit

---

## Instalação Rápida

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/controlador-de-gastos.git
cd controlador-de-gastos
```

### 2. Instale as dependências do sistema

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-gi python3-gst-1.0 gir1.2-gtk-3.0 webkit2gtk-4.0
```

### 3. Instale o PyWebView

```bash
pip3 install pywebview
```

### 4. Execute o app

```bash
python3 app.py
```

---

## Instalação Automática (recomendado)

Execute o script de instalação que configura tudo automaticamente:

```bash
chmod +x install.sh
./install.sh
```

Isso irá:
- Verificar e instalar dependências do sistema
- Criar um virtualenv com acesso ao GTK do sistema
- Instalar o PyWebView
- Criar o launcher `run.sh`
- Registrar o app no menu do Ubuntu

Após a instalação, abra o app pelo menu do sistema: pressione `Super` e digite **"Controlador de Gastos"**.

---

## Estrutura do Projeto

```
controlador-de-gastos/
├── app.py              # Ponto de entrada — inicializa a janela PyWebView
├── database.py         # Lógica SQLite (CRUD, agregações, parser)
├── config.py           # Persistência de configurações (tema, etc.)
├── index.html          # Interface SPA (HTML5 + Tailwind CSS)
├── script.js           # Lógica frontend (navegação, chamadas API)
├── style.css           # Estilos customizados e animações
├── icon.svg            # Ícone do app
├── run.sh              # Script de execução (gerado pelo install.sh)
├── install.sh          # Script de instalação automática
├── tests.py            # Testes automatizados (43 testes)
├── gastos.db           # Banco de dados SQLite (gerado automaticamente)
└── app_config.json     # Configurações do usuário (gerado automaticamente)
```

---

## Arquitetura

```
┌─────────────────────────────────────────┐
│           PyWebView Window              │
│  ┌─────────────────────────────────┐    │
│  │      HTML/CSS/JS Frontend       │    │
│  │   (SPA com Tailwind + Phosphor) │    │
│  └─────────────┬───────────────────┘    │
│                │ pywebview.api          │
│  ┌─────────────▼───────────────────┐    │
│  │      Python API Bridge        │    │
│  │         (class Api)           │    │
│  └─────────────┬───────────────────┘    │
│                │                        │
│  ┌─────────────▼───────────────────┐    │
│  │    database.py  │  config.py   │    │
│  │    (SQLite)     │  (JSON)      │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

---

## Testes

Execute os testes automatizados:

```bash
python3 tests.py -v
```

Cobertura:
- **CRUD completo** (create, read, update, delete)
- **Agregações mensais** e drill-down hierárquico
- **Cadastro em massa** (parsing de "Descrição, Valor")
- **Parser de texto** (extração de notificações bancárias)
- **Casos de borda** (unicode, caracteres especiais, precisão float)
- **API Bridge** (todos os métodos expostos ao JS)

---

## Tecnologias

| Camada | Tecnologia |
|--------|------------|
| Backend | Python 3, SQLite3 |
| Desktop Wrapper | PyWebView (GTK/WebKit) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| UI Framework | Tailwind CSS (CDN) |
| Ícones | Phosphor Icons |

---

## Roadmap

- [ ] Gráficos de gastos (Chart.js)
- [ ] Exportação para CSV/Excel
- [ ] Categorias pré-definidas com ícones
- [ ] Backup automático do banco de dados
- [ ] Suporte a múltiplas contas/bancos
- [ ] Lembrete de contas a pagar

---

## Licença

MIT License — livre para uso pessoal e comercial.

---

## Autor

Feito com por [Seu Nome](https://github.com/seu-usuario).

---

## Agradecimentos

- [PyWebView](https://pywebview.flowrl.com/) — por tornar apps desktop Python possíveis
- [Tailwind CSS](https://tailwindcss.com/) — por acelerar o desenvolvimento de UI
- [Phosphor Icons](https://phosphoricons.com/) — pelos ícones limpos e modernos
