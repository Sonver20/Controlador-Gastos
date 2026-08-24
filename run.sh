#!/bin/bash
# Launcher automatico do Controlador de Gastos
# Ativa o virtualenv e executa o app

source "$HOME/meu_env/bin/activate"
cd "$(dirname "$(readlink -f "$0")")"
python3 app.py
