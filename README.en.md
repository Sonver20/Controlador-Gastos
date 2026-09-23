# Controlador de Gastos

🌐 **Language:** [Português](README.md) | English

Native desktop application for personal finance management, built with
**Python + PyWebView** and a modern **HTML/CSS/JS** interface.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![PyWebView](https://img.shields.io/badge/PyWebView-5.0+-green?logo=python)
![SQLite](https://img.shields.io/badge/SQLite-3-orange?logo=sqlite)
![Version](https://img.shields.io/badge/version-3.0.0-blueviolet)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## About

**Controlador de Gastos** ("Expense Controller") is a personal finance
management app that runs natively on **Ubuntu Linux** (and derivatives). It
was designed to be simple, fast and functional — with no dependency on
cloud services or an internet connection.

All business logic and data persistence run locally via **SQLite**, while
the interface is a modern **Single Page Application (SPA)** with light/dark
theme, smooth animations and intuitive navigation.

> **Monetary precision:** all money values (expenses, balance, salary) are
> handled with `decimal.Decimal` in Python and persisted in `DECIMAL`
> columns in SQLite, avoiding the typical rounding errors of `float`
> (e.g. `0.1 + 0.2 != 0.3`). Databases created by earlier versions (`REAL`
> columns) are migrated automatically on first launch, with no data loss.

---

## Features

| Feature | Description |
|---------|-----------|
| **Expense Registration** | Shared category and subcategory, with a list of products (name, unit price and quantity) |
| **Unit Price × Quantity** | Total calculated automatically, with support for fractional quantities (e.g. `0.750 kg` of steak at R$ 60.00/kg) |
| **Expense Tree** | Hierarchical navigation: **Month → Category → Subcategory (if used) → Expenses** |
| **Monthly Expenses** | Recurring expense templates (e.g. "Household bills", "Subscriptions"), launched and automatically debited from the balance every month |
| **Dashboard** | Monthly summary with totals, expense count and the month's top category |
| **Account Balance** | Enter your current balance — the app automatically subtracts (or refunds) it with every expense registered, edited or deleted |
| **Monthly Salary** | Configure your salary and next pay date — credited every 30 real-world days |
| **Salary Calendar** | Projection of upcoming paychecks, highlighting the vacation month and the net calculation (Brazilian INSS + IRRF taxes) |
| **Light/Dark Theme** | Switch between themes, persisted to disk |
| **Edit/Delete** | Edit or delete expenses directly from the Expense Tree, with automatic balance adjustment |

---

<details>
<summary>Screenshots</summary>

### Dashboard
![Dashboard](screenshots/dashboard.png)

### New Expense
![New Expense](screenshots/cadastro.png)

### Expense Tree
![Expense Tree](screenshots/arvore.png)

### Monthly Expenses
![Monthly Expenses](screenshots/mensais.png)

### Salary Calendar
![Salary Calendar](screenshots/calendario.png)

</details>

---

## Requirements

- **Ubuntu Linux** (or derivatives: Mint, Pop!_OS, Zorin, elementary, etc.)
- **Python 3.10+**
- GTK 3 + WebKit2GTK system dependencies

---

## Quick Install

### 1. Clone the repository

```bash
git clone https://github.com/Sonver20/Controlador-Gastos.git
cd Controlador-Gastos
```

### 2. Install system dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-gi \
    gir1.2-gtk-3.0 gir1.2-webkit2-4.0
```

### 3. Create a virtualenv and install PyWebView

```bash
python3 -m venv .venv --system-site-packages
.venv/bin/pip install pywebview
```

> `--system-site-packages` is required so the virtualenv can see the
> system-installed `gi` (PyGObject) package, which PyWebView uses to talk
> to GTK.

### 4. Run the app

```bash
.venv/bin/python app.py
```

---

## Automatic Install (recommended)

Run the install script, which sets everything up automatically:

```bash
chmod +x install.sh
./install.sh
```

This will:

- Check and install system dependencies
- Create a virtualenv with access to the system GTK
- Install PyWebView
- Create the `run.sh` launcher
- Register the app in the Ubuntu applications menu

After installation, open the app from the system menu: press `Super` and
type **"Controlador de Gastos"**.

---

## Versioning

This project follows [Semantic Versioning](https://semver.org/)
(`MAJOR.MINOR.PATCH`) starting from version 2.0.0. The current version lives
in `version.py` (the single source of truth — the app's footer fetches this
value automatically) and the change history is kept in
[CHANGELOG.md](CHANGELOG.md).

---

## Architecture

```
┌─────────────────────────────────────────┐
│           PyWebView Window              │
│  ┌─────────────────────────────────┐    │
│  │      HTML/CSS/JS Frontend       │    │
│  │  (SPA with Tailwind + Phosphor) │    │
│  └─────────────┬───────────────────┘    │
│                │ pywebview.api          │
│  ┌─────────────▼───────────────────┐    │
│  │      Python API Bridge          │    │
│  │         (class Api)             │    │
│  └───┬─────────────┬───────────────┘    │
│      │ pure reads   │ business rules    │
│      │              │                   │
│      │      ┌───────▼───────────┐       │
│      │      │  services/        │       │
│      │      │  finance.py       │       │
│      │      │  scheduler.py     │       │
│      │      │  payroll.py       │       │
│      │      │  monthly.py       │       │
│      │      └───────┬───────────┘       │
│  ┌───▼──────────────▼──────┐  ┌──────┐  │
│  │  database.py (SQLite)   │  │config│  │
│  │  connections, schema,   │  │(JSON)│  │
│  │  raw SQL                │  │      │  │
│  └─────────────────────────┘  └──────┘  │
└─────────────────────────────────────────┘
```

`database.py` is **strictly persistence**: it opens connections, creates
and migrates the schema, and runs SQL. No business decision (tax
calculation, salary cycle, balance adjustment) lives there — all of that
sits in the `services/` modules, which keeps the code testable and the
database swappable.

---

## Tests

Run the automated tests:

```bash
python3 tests.py -v
```

Coverage:

- **Full CRUD** for expenses (create, read, update, delete)
- **Monthly aggregations** and hierarchical drill-down (month → category → subcategory)
- **Subcategories and quantity × unit price** (including fractional quantities)
- **End-to-end decimal precision** (no float drift, even after reopening the database)
- **Balance and salary** (crediting, debiting, field preservation on updates)
- **Salary calendar** with 30-day-cycle projection and vacation pay calculation (Brazilian INSS/IRRF)
- **Monthly Expenses** (creation, application, no duplication within the same month)
- **Automatic migration** of legacy databases (`REAL` → `DECIMAL` columns, additive new columns)
- **Rollback** on exception mid-transaction
- **API Bridge** — every method exposed to JavaScript

---

## Technologies

| Layer | Technology |
|--------|------------|
| Backend | Python 3, SQLite3 |
| Desktop Wrapper | PyWebView (GTK/WebKit) |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| UI Framework | Tailwind CSS (local, in `assets/tailwind.js`) |
| Icons | Phosphor Icons (local font in `assets/phosphor-regular.css`) |

All frontend dependencies are **vendored in the repository** under
`assets/` — the app opens and works without any internet connection.

---

## License

MIT License — free for personal and commercial use.

---

## Author

Made by [Everson](https://github.com/Sonver20).

---

## Acknowledgements

This project only exists thanks to these tools and libraries:

- [PyWebView](https://pywebview.flowrl.com/) — the Python ↔ JavaScript bridge that makes everything possible
- [SQLite](https://sqlite.org/) — embedded, serverless database
- [Python](https://python.org/) — the backend language
- [Tailwind CSS](https://tailwindcss.com/) — interface styling
- [Phosphor Icons](https://phosphoricons.com/) — clean, modern icons
- [GTK](https://gtk.org/) and [WebKitGTK](https://webkitgtk.org/) — the graphics toolkit that runs the UI on Linux
