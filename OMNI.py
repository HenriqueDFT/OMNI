# Adicionar cabeçalho de licença ao arquivo principal
HEADER='"
OMNI - Orchestrated Modeling of Nanomaterials under electric-field Influence

Copyright 2024 HenriqueDFT (Henrique Lago) - Grupo de Nanofísica Computacional (GNC-UFPI)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"

# Adicionar ao início do arquivo
echo "$HEADER" | cat - src/OMNI.py > temp && mv temp src/OMNI.py


import os
import re
import shutil
import subprocess
import time
import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from PIL import Image, ImageTk
import threading
import sys
import glob
import json
try:
    from tkinter import font
    import sv_ttk  # Para temas modernos
except ImportError:
    sv_ttk = None
    print("sv_ttk não disponível para temas modernos")
    
class CalculationState:
    def __init__(self):
        self.fdf_path = None
        self.psf_files = []
        self.fields = []
        self.base_dir_name = "electric_field_calculations"
        self.siesta_python_path = None
        self.last_completed_index = -1
        self.is_running = False
        self.paused_for_fdf = False
        self.last_dir = None
        
    def to_dict(self):
        return {
            "fdf_path": self.fdf_path,
            "psf_files": self.psf_files,
            "fields": self.fields,
            "base_dir_name": self.base_dir_name,
            "siesta_python_path": self.siesta_python_path,
            "last_completed_index": self.last_completed_index
        }

    @staticmethod
    def from_dict(data):
        state = CalculationState()
        state.fdf_path = data.get("fdf_path")
        state.psf_files = data.get("psf_files", [])
        state.fields = data.get("fields", [])
        state.base_dir_name = data.get("base_dir_name", "electric_field_calculations")
        state.siesta_python_path = data.get("siesta_python_path")
        state.last_completed_index = data.get("last_completed_index", -1)
        return state

class SiestaElectricFieldGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OMNI")
        self.root.geometry("1200x900")
       
        self.images = {}  # Dicionário para armazenar as imagens
 
        # Configurar tema moderno (ADICIONE ESTA LINHA)
        self.setup_theme()
        # Variáveis de controle
        self.state_file = Path.cwd() / "calculation_state.json"
        self.autostart_file = Path.cwd() / "autostart.cfg"
        self.state = CalculationState()
        self.fdf_path = tk.StringVar()
        self.psf_files = []
        self.fields = []
        self.base_dir_name = tk.StringVar(value="electric_field_calculations")
        self.siesta_python_path = tk.StringVar()
        self.completed_file = "concluido.txt"
        self.current_dir = Path.cwd()
        self.is_running = False
        self.paused_for_fdf = False
        self.last_dir = None
        
        # Configurar interface e tentar carregar o estado
        self.setup_ui()
        self.qrcode_tk = None  # Variável para a imagem do QR code
        self.check_for_siesta_py()
        self.root.after(100, self.load_state_on_start)
        
    def configure_styles(self):
        """Configura estilos manuais se sv_ttk não estiver disponível"""
        self.style.configure('TFrame', background=self.colors['background'])
        self.style.configure('TLabel', background=self.colors['background'], 
                            foreground=self.colors['text'])
        self.style.configure('TButton', padding=6, relief='flat',
                            background=self.colors['secondary'],
                            foreground='white')
        self.style.map('TButton', 
                      background=[('active', self.colors['primary']),
                                 ('pressed', self.colors['dark'])])
        self.style.configure('Header.TLabel', font=('Segoe UI', 14, 'bold'),
                            foreground=self.colors['primary'])
        self.style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'),
                            foreground=self.colors['primary'])
        self.style.configure('Accent.TButton', background=self.colors['accent'])
        self.style.configure('Success.TButton', background=self.colors['success'])
        self.style.configure('Warning.TButton', background=self.colors['warning'])

    def setup_icons(self):
        """Configura ícones (pode ser deixado vazio por enquanto)"""
        pass

    def setup_modern_menu(self):
        """Configura um menu moderno"""
        menu_bar = tk.Menu(self.root, tearoff=0)
        self.root.config(menu=menu_bar)
    
        # Menu Ajuda
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Ajuda", menu=help_menu)
        help_menu.add_command(label="Sobre", command=self.show_about)
        help_menu.add_command(label="Tutorial", command=self.show_tutorial)
        
        # Menu Tema (se sv_ttk estiver disponível)
        if sv_ttk:
            theme_menu = tk.Menu(menu_bar, tearoff=0)
            menu_bar.add_cascade(label="Tema", menu=theme_menu)
            theme_menu.add_command(label="Claro", command=lambda: sv_ttk.set_theme("light"))
            theme_menu.add_command(label="Escuro", command=lambda: sv_ttk.set_theme("dark"))
    def setup_ui(self):
        # Configurar o frame principal com padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Notebook para abas com estilo moderno
        style = ttk.Style()
        style.configure('TNotebook', tabposition='nw')
        style.configure('TNotebook.Tab', padding=[12, 6], font=('Segoe UI', 10, 'bold'))
        
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill='both', expand=True)
    
        # Aba de configuração principal
        config_frame = ttk.Frame(notebook, padding="15")
        notebook.add(config_frame, text="Configuração Principal")
    
        # Aba de campos elétricos
        field_frame = ttk.Frame(notebook, padding="15")
        notebook.add(field_frame, text="Campos Elétricos")
    
        # Aba de execução e logs
        log_frame = ttk.Frame(notebook, padding="15")
        notebook.add(log_frame, text="Execução e Logs")
    
        # Configurar cada aba com estilo moderno
        self.setup_config_tab(config_frame)
        self.setup_field_tab(field_frame)
        self.setup_log_tab(log_frame)
        self.setup_header(main_frame)
        
        # Adicionar rodapé
        self.setup_footer()
    
        # Menu modernizado
        self.setup_modern_menu()
    def setup_footer(self):
        # Rodapé com copyright
        footer_frame = ttk.Frame(self.root, style='Footer.TFrame')
        footer_frame.pack(side='bottom', fill='x', pady=5)
        
        # Configurar estilo do rodapé
        self.style.configure('Footer.TFrame', background=self.colors['dark'])
        
        copyright_text = "© 2024 OMNI Software - Desenvolvido por Henrique Lago - Grupo de Nanofísica Computacional (GNC-UFPI)"
        copyright_label = ttk.Label(footer_frame, text=copyright_text, 
                                   font=("TkDefaultFont", 8), 
                                   foreground="white",
                                   background=self.colors['dark'])
        copyright_label.pack(pady=3)

    def setup_header(self, parent):
        """Configura o cabeçalho com logo e nome do software"""
        header_frame = ttk.Frame(parent, style='Header.TFrame')
        header_frame.pack(fill='x', pady=(0, 10))
    
        # Configurar estilo do cabeçalho
        self.style.configure('Header.TFrame', background=self.colors['primary'])
        
        # Logo UFPI à esquerda
        left_frame = ttk.Frame(header_frame, style='Header.TFrame')
        left_frame.pack(side='left', padx=10, pady=5)
    
        current_dir = Path(__file__).parent
        image_paths = {
            'ufpi': current_dir / "imagens" / "ufpi.png",
            'gnc': current_dir / "imagens" / "gnc.png"
        }
    
        # Carregar e exibir logo UFPI (esquerda)
        try:
            if os.path.exists(image_paths['ufpi']):
                img = Image.open(image_paths['ufpi'])
                img = img.resize((60, 60), Image.LANCZOS)
                self.images['ufpi'] = ImageTk.PhotoImage(img)
                label = ttk.Label(left_frame, image=self.images['ufpi'], 
                                  background=self.colors['primary'])
                label.pack()
            else:
                placeholder = tk.Canvas(left_frame, width=40, height=40, 
                                    bg=self.colors['primary'], highlightthickness=0)
                placeholder.create_text(20, 20, text="UFPI", fill='white')
                placeholder.pack()
        except Exception as e:
            print(f"Erro ao carregar logo UFPI: {e}")
            placeholder = tk.Canvas(left_frame, width=40, height=40, 
                                bg=self.colors['primary'], highlightthickness=0)
            placeholder.create_text(20, 20, text="UFPI", fill='white')
            placeholder.pack()
    
        # Nome do software no centro (destacado)
        title_frame = ttk.Frame(header_frame, style='Header.TFrame')
        title_frame.pack(side='left', expand=True, fill='x')
    
        software_name = ttk.Label(title_frame, text="OMNI", 
                                  font=('Segoe UI', 24, 'bold'),
                                  foreground='white',
                                  background=self.colors['primary'])
        software_name.pack(pady=5)
    
        software_desc = ttk.Label(title_frame, 
                                  text="Automação de Campo Elétrico - SIESTA DFT",
                                  font=('Segoe UI', 10),
                                  foreground='white',
                                  background=self.colors['primary'])
        software_desc.pack(pady=(0, 5))
    
        # Logo GNC à direita
        right_frame = ttk.Frame(header_frame, style='Header.TFrame')
        right_frame.pack(side='right', padx=10, pady=5)
    
        # Carregar e exibir logo GNC (direita)
        try:
            if os.path.exists(image_paths['gnc']):
                img = Image.open(image_paths['gnc'])
                img = img.resize((60, 60), Image.LANCZOS)
                self.images['gnc'] = ImageTk.PhotoImage(img)
                label = ttk.Label(right_frame, image=self.images['gnc'], 
                                  background=self.colors['primary'])
                label.pack()
            else:
                placeholder = tk.Canvas(right_frame, width=40, height=40, 
                                    bg=self.colors['primary'], highlightthickness=0)
                placeholder.create_text(20, 20, text="GNC", fill='white')
                placeholder.pack()
        except Exception as e:
            print(f"Erro ao carregar logo GNC: {e}")
            placeholder = tk.Canvas(right_frame, width=40, height=40, 
                                bg=self.colors['primary'], highlightthickness=0)
            placeholder.create_text(20, 20, text="GNC", fill='white')
            placeholder.pack()
    def setup_config_tab(self, parent):
        # Configurar grid
        parent.columnconfigure(1, weight=1)
    
        # Título mais simples (já temos o nome no cabeçalho)
        title_label = ttk.Label(parent, text="Configuração Principal", 
                           font=('Segoe UI', 12, 'bold'),
                           foreground=self.colors['primary'])
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 15))
        
        # Arquivo FDF
        ttk.Label(parent, text="Arquivo FDF:").grid(row=1, column=0, sticky='w', padx=5, pady=8)
        fdf_entry = ttk.Entry(parent, textvariable=self.fdf_path, width=70)
        fdf_entry.grid(row=1, column=1, sticky='we', padx=5, pady=8)
        ttk.Button(parent, text="Procurar", command=self.browse_fdf).grid(row=1, column=2, padx=5, pady=8)
        
        # Caminho para siesta.py
        ttk.Label(parent, text="Caminho para siesta.py:").grid(row=2, column=0, sticky='w', padx=5, pady=8)
        siesta_entry = ttk.Entry(parent, textvariable=self.siesta_python_path, width=70)
        siesta_entry.grid(row=2, column=1, sticky='we', padx=5, pady=8)
        ttk.Button(parent, text="Procurar", command=self.browse_siesta_python).grid(row=2, column=2, padx=5, pady=8)
        
        # Arquivos PSF
        ttk.Label(parent, text="Arquivos PSF:").grid(row=3, column=0, sticky='nw', padx=5, pady=8)
        
        # Frame para a listbox com borda
        psf_frame = ttk.Frame(parent, relief='sunken', borderwidth=1)
        psf_frame.grid(row=3, column=1, sticky='we', padx=5, pady=8)
        psf_frame.columnconfigure(0, weight=1)
        
        self.psf_listbox = tk.Listbox(psf_frame, width=70, height=5, 
                                     borderwidth=0, highlightthickness=0)
        self.psf_listbox.grid(row=0, column=0, sticky='we', padx=2, pady=2)
        
        # Adicionar scrollbar à listbox
        psf_scrollbar = ttk.Scrollbar(psf_frame, orient='vertical', command=self.psf_listbox.yview)
        psf_scrollbar.grid(row=0, column=1, sticky='ns', pady=2)
        self.psf_listbox.configure(yscrollcommand=psf_scrollbar.set)
        
        psf_btn_frame = ttk.Frame(parent)
        psf_btn_frame.grid(row=3, column=2, sticky='n', padx=5, pady=8)
        ttk.Button(psf_btn_frame, text="Adicionar", command=self.add_psf).pack(pady=4, fill='x')
        ttk.Button(psf_btn_frame, text="Remover", command=self.remove_psf).pack(pady=4, fill='x')
        
        # Nome da pasta base
        ttk.Label(parent, text="Nome da Pasta Base:").grid(row=4, column=0, sticky='w', padx=5, pady=8)
        ttk.Entry(parent, textvariable=self.base_dir_name, width=40).grid(row=4, column=1, sticky='w', padx=5, pady=8)
        
        # Botão para gerar pré-visualização
        ttk.Button(parent, text="Pré-visualizar Campos", command=self.preview_fields, 
                  style='Accent.TButton').grid(row=5, column=1, pady=15, sticky='e')
    
    def setup_theme(self):
        """Configura o tema visual moderno da aplicação"""
        # Configurar estilo
        self.style = ttk.Style()
        
        # Configurar fonte padrão
        self.default_font = ("Segoe UI", 10)  # Fonte moderna
        self.root.option_add("*Font", self.default_font)
        
        # Configurar cores
        self.colors = {
            'primary': '#2c3e50',      # Azul escuro
            'secondary': '#3498db',    # Azul
            'accent': '#e74c3c',       # Vermelho
            'success': '#2ecc71',      # Verde
            'warning': '#f39c12',      # Laranja
            'light': '#ecf0f1',        # Cinza claro
            'dark': '#34495e',         # Cinza escuro
            'text': '#2c3e50',         # Texto escuro
            'background': '#f5f7fa'    # Fundo claro
        }
        
        # Aplicar tema sv_ttk se disponível
        if sv_ttk:
            sv_ttk.set_theme("light")
        else:
            # Configurar estilo manualmente se sv_ttk não estiver disponível
            self.configure_styles()
        
        # Configurar ícones (opcional)
        self.setup_icons()
        
    def setup_field_tab(self, parent):
        # Título
        title_label = ttk.Label(parent, text="Configuração dos Campos Elétricos", 
                               style='Header.TLabel')
        title_label.pack(pady=(0, 15))
        
        # Frame para campos de entrada
        field_input_frame = ttk.LabelFrame(parent, text="Campos Elétricos (V/Ang)", 
                                         padding="10")
        field_input_frame.pack(fill='x', padx=5, pady=5)
        
        # Cabeçalhos
        headers = ["Eixo", "Início", "Fim", "Passo", "Ativo"]
        for col, header in enumerate(headers):
            ttk.Label(field_input_frame, text=header, font=('Segoe UI', 9, 'bold')).grid(
                row=0, column=col, padx=5, pady=5)
        
        # Campos para X
        ttk.Label(field_input_frame, text="X:").grid(row=1, column=0, padx=5, pady=8)
        self.x_start = tk.DoubleVar(value=0.0)
        self.x_end = tk.DoubleVar(value=0.0)
        self.x_step = tk.DoubleVar(value=0.001)
        self.x_active = tk.BooleanVar(value=False)
        ttk.Entry(field_input_frame, textvariable=self.x_start, width=10).grid(row=1, column=1, padx=5, pady=8)
        ttk.Entry(field_input_frame, textvariable=self.x_end, width=10).grid(row=1, column=2, padx=5, pady=8)
        ttk.Entry(field_input_frame, textvariable=self.x_step, width=10).grid(row=1, column=3, padx=5, pady=8)
        ttk.Checkbutton(field_input_frame, variable=self.x_active).grid(row=1, column=4, padx=5, pady=8)
        
        # Campos para Y
        ttk.Label(field_input_frame, text="Y:").grid(row=2, column=0, padx=5, pady=8)
        self.y_start = tk.DoubleVar(value=0.0)
        self.y_end = tk.DoubleVar(value=0.0)
        self.y_step = tk.DoubleVar(value=0.001)
        self.y_active = tk.BooleanVar(value=False)
        ttk.Entry(field_input_frame, textvariable=self.y_start, width=10).grid(row=2, column=1, padx=5, pady=8)
        ttk.Entry(field_input_frame, textvariable=self.y_end, width=10).grid(row=2, column=2, padx=5, pady=8)
        ttk.Entry(field_input_frame, textvariable=self.y_step, width=10).grid(row=2, column=3, padx=5, pady=8)
        ttk.Checkbutton(field_input_frame, variable=self.y_active).grid(row=2, column=4, padx=5, pady=8)
        
        # Campos para Z
        ttk.Label(field_input_frame, text="Z:").grid(row=3, column=0, padx=5, pady=8)
        self.z_start = tk.DoubleVar(value=0.0)
        self.z_end = tk.DoubleVar(value=0.0)
        self.z_step = tk.DoubleVar(value=0.001)
        self.z_active = tk.BooleanVar(value=False)
        ttk.Entry(field_input_frame, textvariable=self.z_start, width=10).grid(row=3, column=1, padx=5, pady=8)
        ttk.Entry(field_input_frame, textvariable=self.z_end, width=10).grid(row=3, column=2, padx=5, pady=8)
        ttk.Entry(field_input_frame, textvariable=self.z_step, width=10).grid(row=3, column=3, padx=5, pady=8)
        ttk.Checkbutton(field_input_frame, variable=self.z_active).grid(row=3, column=4, padx=5, pady=8)
        
        # Botão para gerar campos
        ttk.Button(field_input_frame, text="Gerar Campos", command=self.generate_fields,
                  style='Accent.TButton').grid(row=4, column=0, columnspan=5, pady=10)
        
        # Lista de campos gerados
        field_list_frame = ttk.LabelFrame(parent, text="Campos Gerados", padding="10")
        field_list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configurar treeview com estilo moderno
        style = ttk.Style()
        style.configure("Treeview", 
                        background=self.colors['light'],
                        foreground=self.colors['text'],
                        rowheight=25,
                        fieldbackground=self.colors['light'])
        style.map('Treeview', background=[('selected', self.colors['secondary'])])
        
        columns = ("#", "X", "Y", "Z")
        self.field_tree = ttk.Treeview(field_list_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.field_tree.heading(col, text=col)
            self.field_tree.column(col, width=100, anchor='center')
        
        # Adicionar scrollbar
        tree_scrollbar = ttk.Scrollbar(field_list_frame, orient='vertical', command=self.field_tree.yview)
        self.field_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        self.field_tree.pack(side='left', fill='both', expand=True, padx=(0, 5), pady=5)
        tree_scrollbar.pack(side='right', fill='y', pady=5)
        
        # Botões para manipular campos
        field_btn_frame = ttk.Frame(field_list_frame)
        field_btn_frame.pack(pady=5, fill='x')
        
        ttk.Button(field_btn_frame, text="Remover Selecionado", command=self.remove_field).pack(side='left', padx=5, pady=2)
        ttk.Button(field_btn_frame, text="Limpar Todos", command=self.clear_fields, 
                  style='Warning.TButton').pack(side='left', padx=5, pady=2)
        ttk.Button(field_btn_frame, text="Adicionar Campo Manual", command=self.add_manual_field,
                  style='Success.TButton').pack(side='left', padx=5, pady=2)
    def setup_log_tab(self, parent):
        # Título
        title_label = ttk.Label(parent, text="Execução e Logs", style='Header.TLabel')
        title_label.pack(pady=(0, 10))
        
        # Área de log com estilo moderno
        log_frame = ttk.Frame(parent)
        log_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        ttk.Label(log_frame, text="Log de Execução:").pack(anchor='w', pady=(0, 5))
        
        # Text area com borda
        text_frame = ttk.Frame(log_frame, relief='sunken', borderwidth=1)
        text_frame.pack(fill='both', expand=True)
        
        self.log_text = scrolledtext.ScrolledText(text_frame, width=100, height=25,
                                                font=('Consolas', 10),  # Fonte monoespaçada para log
                                                borderwidth=0, highlightthickness=0)
        self.log_text.pack(fill='both', expand=True, padx=2, pady=2)
        
        # Botões de execução com estilo moderno
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Preparar Arquivos", command=self.prepare_files,
                  style='Success.TButton').pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Executar Cálculos", command=self.run_calculations,
                  style='Accent.TButton').pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Parar Execução", command=self.stop_execution,
                  style='Warning.TButton').pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Tornar Inicial", command=self.set_autostart).pack(side='left', padx=5)

    def load_state_on_start(self):
        if self.autostart_file.exists() or self.state_file.exists():
            if self.autostart_file.exists() and not self.state_file.exists():
                messagebox.showerror("Erro de Autoinício", "O arquivo de autoinício existe, mas o estado do cálculo não foi encontrado.")
                self.autostart_file.unlink()
                return

            if self.state_file.exists():
                try:
                    with open(self.state_file, 'r') as f:
                        data = json.load(f)
                        self.state = CalculationState.from_dict(data)
                    
                    if self.state.last_completed_index < len(self.state.fields) - 1:
                        if self.autostart_file.exists() or messagebox.askyesno("Retomar Cálculo", "Um cálculo anterior foi interrompido. Deseja continuar de onde parou?"):
                            self.log("Estado de cálculo restaurado. Iniciando a partir do último ponto salvo.")
                            self.restore_gui_from_state()
                            if self.autostart_file.exists():
                                self.autostart_file.unlink()
                                self.run_calculations()
                        else:
                            self.log("Cálculo anterior não será retomado. Iniciando um novo.")
                            self.state = CalculationState()
                            self.state_file.unlink()
                except (IOError, json.JSONDecodeError) as e:
                    messagebox.showerror("Erro", f"Falha ao carregar o estado do cálculo: {e}")

    def save_state(self):
        try:
            self.state.fdf_path = self.fdf_path.get()
            self.state.siesta_python_path = self.siesta_python_path.get()
            self.state.psf_files = self.psf_files
            self.state.fields = self.fields
            self.state.base_dir_name = self.base_dir_name.get()
            
            with open(self.state_file, 'w') as f:
                json.dump(self.state.to_dict(), f, indent=4)
        except Exception as e:
            self.log(f"Erro ao salvar o estado: {e}")

    def restore_gui_from_state(self):
        self.fdf_path.set(self.state.fdf_path or "")
        self.siesta_python_path.set(self.state.siesta_python_path or "")
        self.psf_files = self.state.psf_files
        self.fields = self.state.fields
        self.base_dir_name.set(self.state.base_dir_name)
        self.update_psf_listbox()
        self.update_field_tree()

    def set_autostart(self):
        if not self.fdf_path.get() or not self.fields or not self.siesta_python_path.get():
            messagebox.showerror("Erro", "Configure os campos FDF, PSF, siesta.py e os campos elétricos antes de configurar o autoinício.")
            return

        self.save_state()
        try:
            with open(self.autostart_file, "w") as f:
                f.write("autostart=True")
            messagebox.showinfo("Configurado", "Cálculo configurado para ser retomado automaticamente na próxima inicialização.")
        except IOError:
            messagebox.showerror("Erro", "Não foi possível criar o arquivo de autostart.")
            
    def check_for_siesta_py(self):
        siesta_path = self.current_dir / "siesta.py"
        if siesta_path.exists():
            self.siesta_python_path.set(str(siesta_path))
            self.log("Script 'siesta.py' encontrado na pasta atual e selecionado automaticamente.")
            
    def browse_fdf(self):
        filename = filedialog.askopenfilename(
            title="Selecionar arquivo FDF",
            filetypes=[("FDF files", "*.fdf"), ("All files", "*.*")]
        )
        if filename:
            self.fdf_path.set(filename)
            
    def browse_siesta_python(self):
        filename = filedialog.askopenfilename(
            title="Selecionar script siesta.py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if filename:
            self.siesta_python_path.set(filename)
            
    def add_psf(self):
        filenames = filedialog.askopenfilenames(
            title="Selecionar arquivos PSF",
            filetypes=[("PSF files", "*.psf *.PSF *.psf.gz *.PSF.GZ"), ("All files", "*.*")]
        )
        for filename in filenames:
            if filename not in self.psf_files:
                self.psf_files.append(filename)
                self.psf_listbox.insert(tk.END, filename)
                
    def remove_psf(self):
        selection = self.psf_listbox.curselection()
        if selection:
            index = selection[0]
            self.psf_files.pop(index)
            self.psf_listbox.delete(index)
            
    def update_psf_listbox(self):
        self.psf_listbox.delete(0, tk.END)
        for item in self.psf_files:
            self.psf_listbox.insert(tk.END, item)
            
    def generate_fields(self):
        x_values = [0.0]
        y_values = [0.0]
        z_values = [0.0]
        
        if self.x_active.get():
            x_values = self.generate_axis_values(self.x_start.get(), self.x_end.get(), self.x_step.get())
        
        if self.y_active.get():
            y_values = self.generate_axis_values(self.y_start.get(), self.y_end.get(), self.y_step.get())
        
        if self.z_active.get():
            z_values = self.generate_axis_values(self.z_start.get(), self.z_end.get(), self.z_step.get())
        
        self.fields = []
        for x in x_values:
            for y in y_values:
                for z in z_values:
                    self.fields.append([x, y, z])
        
        self.update_field_tree()
        self.log(f"Gerados {len(self.fields)} campos elétricos.")
        
    def generate_axis_values(self, start, end, step):
        if start == end:
            return [start]
        
        if step == 0:
            return [start]
            
        if start < end:
            values = np.arange(start, end + step/2, step)
        else:
            values = np.arange(start, end - step/2, -step)
            
        return [round(v, 6) for v in values]
    
    def update_field_tree(self):
        for item in self.field_tree.get_children():
            self.field_tree.delete(item)
            
        for i, field in enumerate(self.fields):
            self.field_tree.insert("", "end", values=(i+1, field[0], field[1], field[2]))
            
    def remove_field(self):
        selection = self.field_tree.selection()
        if selection:
            index = self.field_tree.index(selection[0])
            if 0 <= index < len(self.fields):
                self.fields.pop(index)
                self.update_field_tree()
                
    def clear_fields(self):
        self.fields = []
        self.update_field_tree()
        
    def add_manual_field(self):
        manual_window = tk.Toplevel(self.root)
        manual_window.title("Adicionar Campo Manual")
        manual_window.geometry("300x150")
        
        ttk.Label(manual_window, text="X:").grid(row=0, column=0, padx=5, pady=5)
        x_val = tk.DoubleVar(value=0.0)
        ttk.Entry(manual_window, textvariable=x_val, width=10).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(manual_window, text="Y:").grid(row=1, column=0, padx=5, pady=5)
        y_val = tk.DoubleVar(value=0.0)
        ttk.Entry(manual_window, textvariable=y_val, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(manual_window, text="Z:").grid(row=2, column=0, padx=5, pady=5)
        z_val = tk.DoubleVar(value=0.0)
        ttk.Entry(manual_window, textvariable=z_val, width=10).grid(row=2, column=1, padx=5, pady=5)
        
        def add_field():
            self.fields.append([x_val.get(), y_val.get(), z_val.get()])
            self.update_field_tree()
            manual_window.destroy()
            
        ttk.Button(manual_window, text="Adicionar", command=add_field).grid(row=3, column=0, columnspan=2, pady=10)
        
    def preview_fields(self):
        if not self.fdf_path.get():
            messagebox.showerror("Erro", "Selecione um arquivo FDF primeiro.")
            return
            
        if not self.fields:
            messagebox.showwarning("Aviso", "Nenhum campo elétrico foi gerado.")
            return
            
        preview = f"Serão criadas {len(self.fields)} pastas com os seguintes campos:\n\n"
        for i, field in enumerate(self.fields[:10]):
            preview += f"Pasta {i+1}: [{field[0]:.6f}, {field[1]:.6f}, {field[2]:.6f}] V/Ang\n"
            
        if len(self.fields) > 10:
            preview += f"... e mais {len(self.fields) - 10} campos\n"
            
        messagebox.showinfo("Pré-visualização", preview)
        
    def log(self, message):
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def prepare_files(self):
        if not self.fdf_path.get():
            messagebox.showerror("Erro", "Selecione um arquivo FDF.")
            return
            
        if not self.fields:
            messagebox.showerror("Erro", "Gere pelo menos um campo elétrico.")
            return
            
        try:
            base_dir = self.current_dir / self.base_dir_name.get()
            base_dir.mkdir(exist_ok=True)
            
            field_dirs = []
            for i, field in enumerate(self.fields):
                field_name = f"E_{field[0]:.4f}_{field[1]:.4f}_{field[2]:.4f}".replace('.', 'p').replace('-', 'm')
                field_dir = base_dir / field_name
                field_dir.mkdir(exist_ok=True)
                field_dirs.append(field_dir)
                
                self.prepare_field_files(field_dir, field, i == 0)
                
            self.log(f"Preparados {len(self.fields)} diretórios com arquivos de campo elétrico.")
            messagebox.showinfo("Sucesso", f"Arquivos preparados em {base_dir}")
            
        except Exception as e:
            self.log(f"Erro ao preparar arquivos: {str(e)}")
            messagebox.showerror("Erro", f"Falha ao preparar arquivos: {str(e)}")
            
    def prepare_field_files(self, field_dir, field_values, is_first_field):
        if is_first_field:
            with open(self.fdf_path.get(), 'r', encoding='utf-8') as f:
                content = f.readlines()
            
            content = self.update_electric_field_block(content, field_values)
            
            new_fdf_path = field_dir / Path(self.fdf_path.get()).name
            with open(new_fdf_path, 'w', encoding='utf-8') as f:
                f.writelines(content)
        
        for psf_path in self.psf_files:
            shutil.copy2(psf_path, field_dir)
            
        if self.siesta_python_path.get():
            shutil.copy2(self.siesta_python_path.get(), field_dir)
            
    def update_electric_field_block(self, content, field_values):
        block_start, block_end, commented = self.find_electric_field_block(content)
        
        new_block = [
            "%block ExternalElectricField\n",
            f"{field_values[0]:.6f} {field_values[1]:.6f} {field_values[2]:.6f} V/Ang\n",
            "%endblock ExternalElectricField\n"
        ]
        
        if commented and block_start != -1:
            for i in range(block_start, block_end + 1):
                content[i] = content[i].replace('#', '').replace('!', '')
        
        if block_start != -1 and block_end != -1:
            del content[block_start:block_end + 1]
            content[block_start:block_start] = new_block
        else:
            insert_pos = 0
            for i, line in enumerate(content):
                if not line.strip().startswith(('#', '!')) and line.strip():
                    insert_pos = i
                    break
            
            header = "# -- ELECTRIC FIELD --\n"
            content.insert(insert_pos, header)
            content[insert_pos + 1:insert_pos + 1] = new_block
        
        return content
    
    def find_electric_field_block(self, content):
        block_start = -1
        block_end = -1
        commented = False
        
        for i, line in enumerate(content):
            if "ExternalElectricField" in line:
                if line.strip().startswith(('#', '!')):
                    commented = True
                block_start = i
                
                for j in range(i + 1, len(content)):
                    if "%endblock ExternalElectricField" in content[j]:
                        block_end = j
                        break
                break
        
        return block_start, block_end, commented
    
    def run_calculations(self):
        if not self.fields:
            messagebox.showerror("Erro", "Nenhum campo elétrico foi gerado.")
            return
            
        if not self.siesta_python_path.get():
            messagebox.showerror("Erro", "Selecione o caminho para siesta.py.")
            return
            
        self.is_running = True
        self.save_state()
        thread = threading.Thread(target=self.run_calculations_thread)
        thread.daemon = True
        thread.start()
        
    def stop_execution(self):
        self.is_running = False
        self.log("Parando execução...")
        
    def run_calculations_thread(self):
        base_dir = self.current_dir / self.base_dir_name.get()
        previous_dir = self.last_dir
        start_index = self.state.last_completed_index + 1
        
        for i in range(start_index, len(self.fields)):
            if not self.is_running:
                break
                
            field = self.fields[i]
            field_name = f"E_{field[0]:.4f}_{field[1]:.4f}_{field[2]:.4f}".replace('.', 'p').replace('-', 'm')
            field_dir = base_dir / field_name
            
            self.log(f"Executando cálculo {i+1}/{len(self.fields)}: {field_name}")
            
            try:
                if i > 0 and previous_dir:
                    result = self.create_fdf_from_previous(field_dir, previous_dir, field)
                    if not result:
                        continue
                
                siesta_script = field_dir / Path(self.siesta_python_path.get()).name
                
                if not siesta_script.exists():
                    self.log(f"Erro: siesta.py não encontrado em {field_dir}")
                    continue
                
                process = subprocess.Popen(
                    [sys.executable, str(siesta_script)],
                    cwd=field_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                stdout, stderr = process.communicate()
                
                if process.returncode == 0:
                    self.log(f"Cálculo {i+1} concluído com sucesso.")
                    completion_file = field_dir / self.completed_file
                    if completion_file.exists():
                        self.log(f"Arquivo de conclusão encontrado: {completion_file}")
                    else:
                        self.log(f"Aviso: Arquivo de conclusão não encontrado em {field_dir}")
                    self.state.last_completed_index = i
                    self.save_state()
                else:
                    self.log(f"Erro no cálculo {i+1}: {stderr}")
                    
                previous_dir = field_dir
                self.last_dir = previous_dir
                
            except Exception as e:
                self.log(f"Exceção no cálculo {i+1}: {str(e)}")
                
        self.is_running = False
        self.log("Todos os cálculos foram concluídos.")
        messagebox.showinfo("Concluído", "Todos os cálculos foram finalizados.")
        self.state_file.unlink()
        self.state.last_completed_index = -1
    
    def create_fdf_from_previous(self, current_dir, previous_dir, field_values):
        try:
            out_files = list(previous_dir.glob("*.out"))
            if not out_files:
                self.log(f"Nenhum arquivo .out encontrado em {previous_dir}")
                return False
                
            latest_out = max(out_files, key=os.path.getctime)
            
            fdf_files = list(previous_dir.glob("*.fdf"))
            if not fdf_files:
                self.log(f"Nenhum arquivo .fdf encontrado em {previous_dir}")
                return False
                
            latest_fdf = fdf_files[0]
            
            vetores, coordenadas, status = self.extrair_dados_otimizacao_final(latest_out, latest_fdf)
            
            if not vetores or not coordenadas:
                self.log(f"Dados de otimização não encontrados em {latest_out}")
                return False
            
            if status == "unrelaxed":
                self.is_running = False
                self.paused_for_fdf = True
                self.log("Aviso: O cálculo anterior não relaxou. Pausando a execução.")
                
                new_fdf_path = filedialog.askopenfilename(
                    title="O cálculo anterior não convergiu. Selecione o novo arquivo FDF para continuar",
                    filetypes=[("FDF files", "*.fdf"), ("All files", "*.*")]
                )
                
                if new_fdf_path:
                    shutil.copy2(new_fdf_path, current_dir)
                    self.fdf_path.set(new_fdf_path)
                    self.paused_for_fdf = False
                    self.is_running = True
                    return True
                else:
                    self.log("Seleção de novo FDF cancelada. Execução parada.")
                    return False
            
            vetores_formatados = "\n".join([f"    {linha.strip()}" for linha in vetores])
            coordenadas_formatadas = "\n".join([f"    {linha.strip()}" for linha in coordenadas])
            
            conteudo_vetores = f"""%block LatticeVectors
{vetores_formatados}
%endblock LatticeVectors"""
            
            conteudo_coordenadas = f"""%block AtomicCoordinatesAndAtomicSpecies
{coordenadas_formatadas}
%endblock AtomicCoordinatesAndAtomicSpecies"""

            conteudo_campo = f"""%block ExternalElectricField
    {field_values[0]:.6f} {field_values[1]:.6f} {field_values[2]:.6f} V/Ang
%endblock ExternalElectricField"""

            with open(latest_fdf, 'r', encoding='utf-8') as f:
                linhas_fdf = f.readlines()

            novo_conteudo_fdf = []
            campo_encontrado = False
            
            i = 0
            while i < len(linhas_fdf):
                linha = linhas_fdf[i]
                
                if 'ExternalElectricField' in linha and ('%block' in linha or '#%block' in linha):
                    novo_conteudo_fdf.append(conteudo_campo + '\n')
                    campo_encontrado = True
                    while i < len(linhas_fdf) and 'endblock ExternalElectricField' not in linhas_fdf[i]:
                        i += 1
                    i += 1
                    continue

                if 'LatticeVectors' in linha and ('%block' in linha or '#%block' in linha):
                    novo_conteudo_fdf.append(conteudo_vetores + '\n')
                    while i < len(linhas_fdf) and 'endblock LatticeVectors' not in linhas_fdf[i]:
                        i += 1
                    i += 1
                    continue

                if 'AtomicCoordinatesAndAtomicSpecies' in linha and ('%block' in linha or '#%block' in linha):
                    novo_conteudo_fdf.append(conteudo_coordenadas + '\n')
                    while i < len(linhas_fdf) and 'endblock AtomicCoordinatesAndAtomicSpecies' not in linhas_fdf[i]:
                        i += 1
                    i += 1
                    continue
                    
                novo_conteudo_fdf.append(linha)
                i += 1

            if not campo_encontrado:
                novo_conteudo_fdf.append(f"\n{conteudo_campo}\n")
                    
            nome_base = Path(self.fdf_path.get()).stem
            x_str = f"{field_values[0]:.4f}".replace('.', '_').replace('-', 'm')
            y_str = f"{field_values[1]:.4f}".replace('.', '_').replace('-', 'm')
            z_str = f"{field_values[2]:.4f}".replace('.', '_').replace('-', 'm')
            
            nome_saida = f"{nome_base}_E_{x_str}_{y_str}_{z_str}.fdf"
            caminho_novo_arquivo = current_dir / nome_saida
            
            with open(caminho_novo_arquivo, 'w') as f:
                f.writelines(novo_conteudo_fdf)

            self.log(f"FDF criado com sucesso: {caminho_novo_arquivo}")
            return True
                
        except Exception as e:
            self.log(f"Erro ao criar FDF: {str(e)}")
            return False
    
    def extrair_dados_otimizacao_final(self, out_file_path, fdf_file_path):
        def get_num_vectors_from_fdf(file_path):
            try:
                with open(file_path, 'r') as file:
                    lines = file.readlines()
            except FileNotFoundError:
                return 0
            
            in_block = False
            count = 0
            for line in lines:
                if 'LatticeVectors' in line and '%block' in line:
                    in_block = True
                    continue
                if '%endblock LatticeVectors' in line:
                    in_block = False
                    break
                if in_block and line.strip() and not line.strip().startswith(('#', '!')):
                    count += 1
            return count

        num_vectors = get_num_vectors_from_fdf(fdf_file_path)
        if num_vectors == 0:
            return None, None, "unrelaxed"

        try:
            with open(out_file_path, 'r') as arquivo:
                linhas = arquivo.readlines()
        except FileNotFoundError:
            return None, None, "unrelaxed"

        coordenadas_bloco_final = []
        vetores_bloco_final = []
        
        current_coor_block_lines = []
        current_cell_block_lines = []
        
        status = "unrelaxed" # Assume unrelaxed por padrão
        
        state = 0
        cell_vector_counter = 0

        for linha in linhas:
            if 'outcoor: Relaxed atomic coordinates (Ang):' in linha:
                current_coor_block_lines = []
                state = 1
                status = "relaxed"
            elif 'outcoor: Final atomic coordinates (unrelaxed) (Ang):' in linha:
                current_coor_block_lines = []
                state = 1
                status = "unrelaxed"
            
            elif state == 1:
                if 'outcell: Unit cell vectors (Ang):' in linha:
                    processed_coor = []
                    for line in current_coor_block_lines:
                        if 'outcoor:' not in line and line.strip():
                            parts = line.split()
                            if len(parts) >= 4:
                                processed_coor.append(' '.join(parts[:4]))
                    coordenadas_bloco_final = processed_coor
                    
                    current_cell_block_lines = []
                    cell_vector_counter = 0
                    state = 2
                else:
                    current_coor_block_lines.append(linha)
            
            elif state == 2:
                if cell_vector_counter < num_vectors:
                    current_cell_block_lines.append(linha)
                    cell_vector_counter += 1
                else:
                    vetores_bloco_final = [line.lstrip() for line in current_cell_block_lines if 'outcell:' not in line and line.strip()]
                    state = 0
                    
        if state == 2:
            vetores_bloco_final = [line.lstrip() for line in current_cell_block_lines if 'outcell:' not in line and line.strip()]

        return vetores_bloco_final, coordenadas_bloco_final, status

    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("Sobre - OMNI")
        about_window.geometry("600x800")
        about_window.configure(bg=self.colors['light'])
        
        # Frame principal
        main_frame = ttk.Frame(about_window, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Título
        title_label = ttk.Label(main_frame, text="SOBRE O SOFTWARE OMNI", 
                               style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Conteúdo
        text_content = """
O OMNI é um software desenvolvido em Python com o propósito de automatizar fluxos de trabalho computacionais para a simulação de sistemas quânticos. Utilizando a Teoria do Funcional da Densidade (DFT) e o pacote SIESTA, o programa otimiza a preparação e execução de cálculos de campo elétrico.

A ferramenta foi projetada para otimizar tarefas rotineiras e repetitivas em simulações computacionais. Suas funcionalidades incluem:

- Geração automatizada de arquivos de entrada (.fdf) para a aplicação de vetores de campo elétrico em múltiplos eixos.
- Gerenciamento de diretórios para cada cálculo, assegurando a organização dos dados.
- Monitoramento em tempo real da execução dos cálculos SIESTA.

O software surgiu da necessidade de garantir maior reprodutibilidade e eficiência nas análises de dados, permitindo a otimização de parâmetros de cálculo de forma ágil e confiável.

O desenvolvimento do OMNI foi realizado por Henrique Lago, físico graduando da Universidade Federal do Piauí (UFPI), no âmbito de pesquisa do Grupo de Nanofísica Computacional (GNC-UFPI), sob a orientação do Professor Dr. Ramon Sampaio Ferreira.

Para mais informações sobre o grupo, escaneie o QR Code abaixo:
"""
        content_label = ttk.Label(main_frame, text=text_content, wraplength=550, 
                                 justify='center')
        content_label.pack(pady=10)
        
        # QR Code
        qr_path = os.path.join("imagens", "qr.png")
        try:
            img_qrcode = Image.open(qr_path)
            img_qrcode = img_qrcode.resize((200, 200), Image.LANCZOS)
            self.qrcode_tk = ImageTk.PhotoImage(img_qrcode)
            qr_label = ttk.Label(main_frame, image=self.qrcode_tk)
            qr_label.pack(pady=10)
        except Exception as e:
            error_label = ttk.Label(main_frame, text="QR Code não encontrado")
            error_label.pack(pady=10)
        
        # Botão fechar
        close_btn = ttk.Button(main_frame, text="Fechar", command=about_window.destroy,
                              style='Accent.TButton')
        close_btn.pack(pady=20)
    def show_tutorial(self):
	    tutorial_window = tk.Toplevel(self.root)
	    tutorial_window.title("Guia de Uso")
	    tutorial_window.geometry("650x500")

	    # Caixa de texto rolável
	    text = scrolledtext.ScrolledText(
		tutorial_window, wrap=tk.WORD, font=("TkDefaultFont", 11)
	    )
	    text.pack(fill='both', expand=True, padx=10, pady=10)

	    # Configuração de tags para destaques sutis e profissionais
	    text.tag_config("title", font=("TkDefaultFont", 12, "bold"), justify="center")
	    text.tag_config("section", font=("TkDefaultFont", 11, "bold"))
	    text.tag_config("keyword", font=("TkDefaultFont", 11, "bold"))
	    text.tag_config("important", font=("TkDefaultFont", 11, "bold"), foreground="darkred")

	    # Cabeçalho
	    text.insert(tk.END, "========================================\n", "title")
	    text.insert(tk.END, "    GUIA RÁPIDO: CÁLCULOS DE CAMPO\n", "title")
	    text.insert(tk.END, "          ELÉTRICO NO SIESTA\n", "title")
	    text.insert(tk.END, "========================================\n\n", "title")

	    text.insert(tk.END, "Este guia apresenta as etapas essenciais para utilização do programa de forma eficiente.\n\n")

	    # Passo 1
	    text.insert(tk.END, "----------------------------------------\n", "section")
	    text.insert(tk.END, "PASSO 1: CONFIGURAÇÃO INICIAL\n", "section")
	    text.insert(tk.END, "----------------------------------------\n\n", "section")
	    text.insert(tk.END, "- ", ""); text.insert(tk.END, "Arquivo FDF", "keyword"); text.insert(tk.END, ": selecione o arquivo principal do SIESTA.\n")
	    text.insert(tk.END, "- ", ""); text.insert(tk.END, "Caminho para siesta.py", "keyword"); text.insert(tk.END, ": indique a localização do script. O programa tentará detectá-lo automaticamente.\n")
	    text.insert(tk.END, "- ", ""); text.insert(tk.END, "Arquivos PSF", "keyword"); text.insert(tk.END, ": adicione todos os arquivos *.psf necessários ao sistema.\n")
	    text.insert(tk.END, "- ", ""); text.insert(tk.END, "Nome da pasta", "keyword"); text.insert(tk.END, ": defina o diretório de saída para os resultados.\n\n")

	    # Passo 2
	    text.insert(tk.END, "----------------------------------------\n", "section")
	    text.insert(tk.END, "PASSO 2: DEFINIÇÃO DOS CAMPOS\n", "section")
	    text.insert(tk.END, "----------------------------------------\n\n", "section")
	    text.insert(tk.END, "- Informe os valores de início, fim e passo para os campos nos eixos X, Y e Z.\n")
	    text.insert(tk.END, "- Selecione os eixos que serão utilizados.\n")
	    text.insert(tk.END, "- Clique em ", ""); text.insert(tk.END, "Gerar Campos", "keyword"); text.insert(tk.END, " para criar a tabela de campos a serem calculados.\n\n")

	    # Passo 3
	    text.insert(tk.END, "----------------------------------------\n", "section")
	    text.insert(tk.END, "PASSO 3: EXECUÇÃO DOS CÁLCULOS\n", "section")
	    text.insert(tk.END, "----------------------------------------\n\n", "section")
	    text.insert(tk.END, "- ", ""); text.insert(tk.END, "Preparar Arquivos", "keyword"); text.insert(tk.END, ": cria uma pasta para cada campo com o arquivo FDF atualizado.\n")
	    text.insert(tk.END, "- ", ""); text.insert(tk.END, "Executar Cálculos", "keyword"); text.insert(tk.END, ": inicia a execução do SIESTA. O progresso é exibido no log.\n")
	    text.insert(tk.END, "- ", ""); text.insert(tk.END, "Parar Execução", "keyword"); text.insert(tk.END, ": interrompe a execução de forma segura.\n")
	    text.insert(tk.END, "- ", ""); text.insert(tk.END, "Tornar Inicial", "keyword"); text.insert(tk.END, ": salva o estado atual para retomada futura.\n\n")

	    # Observações
	    text.insert(tk.END, "----------------------------------------\n", "section")
	    text.insert(tk.END, "OBSERVAÇÕES IMPORTANTES\n", "section")
	    text.insert(tk.END, "----------------------------------------\n\n", "section")
	    text.insert(tk.END, "- ", ""); text.insert(tk.END, "Requisitos", "important"); text.insert(tk.END, ": confirme que o SIESTA está instalado e que o script 'siesta.py' é funcional.\n")
	    text.insert(tk.END, "- ", ""); text.insert(tk.END, "Localização", "important"); text.insert(tk.END, ": recomenda-se manter o script do programa e o 'siesta.py' no mesmo diretório.\n")
	    text.insert(tk.END, "- ", ""); text.insert(tk.END, "Falhas de cálculo", "important"); text.insert(tk.END, ": em caso de interrupção, será solicitado um novo arquivo FDF para continuidade.\n")

	    # Bloquear edição
	    text.config(state='disabled')

	    # Botão fechar
	    close_btn = tk.Button(tutorial_window, text="Fechar", command=tutorial_window.destroy)
	    close_btn.pack(pady=5)

		
if __name__ == "__main__":
    root = tk.Tk()
    app = SiestaElectricFieldGUI(root)
    root.mainloop() 
