import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import subprocess
import os
import sys
import json
import shutil
import psutil
import time

# --- Configurações e Arquivos de Estado ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "ultima_sessao.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "configuracao.json")

def load_state():
    """Carrega o estado do último cálculo do arquivo JSON."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_state(state_data):
    """Salva o estado do cálculo atual no arquivo JSON."""
    with open(STATE_FILE, "w") as f:
        json.dump(state_data, f, indent=4)

def load_config():
    """Carrega as configurações do arquivo JSON, incluindo o modo automático."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            try:
                # Retorna a configuração existente, mas garante que o auto_restart esteja ativado
                config = json.load(f)
                config["auto_restart_enabled"] = True
                return config
            except json.JSONDecodeError:
                return {"auto_restart_enabled": True}
    return {"auto_restart_enabled": True}

def save_config(config_data):
    """Salva as configurações no arquivo JSON."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_data, f, indent=4)

# --- Lógica de Execução e Verificação ---
def check_calculation_status(output_folder, fdf_name):
    """Verifica se o cálculo foi concluído com sucesso."""
    output_file = os.path.join(output_folder, fdf_name.replace('.fdf', '.out'))
    if not os.path.exists(output_file):
        return "incomplete"

    with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
        try:
            f.seek(0, os.SEEK_END)
            f.seek(max(f.tell() - 4096, 0), os.SEEK_SET)
            content = f.read()
        except IOError:
            f.seek(0)
            content = f.read()
    
    # As mensagens de sucesso agora são verificadas em uma lista
    success_messages = [
        "siesta: The run has finished",
        ">> End of run",
        "Job completed"
    ]
    
    if any(msg in content for msg in success_messages):
        return "completed"
    else:
        return "incomplete"

def get_siesta_command(fdf_name, use_restart_flag=False):
    """Determina o comando para executar o Siesta."""
    siesta_args = "-Diagon-restart" if use_restart_flag else ""
    return f"siesta {siesta_args}"

# --- Classe da Aplicação ---
class SiestaApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Siesta Runner")
        self.geometry("400x300")
        
        self.state_data = load_state()
        self.config_data = load_config()
        save_config(self.config_data)  # Garante que a configuração inicial seja salva
        self.siesta_process = None
        self.output_file_handle = None

        self.fdf_path = None
        self.psf_paths = []
        self.restarts = 0

        self.find_files_in_folder()
        self.create_widgets()
        
        self.check_last_run()
        self.iniciar_calculo_auto()

    def find_files_in_folder(self):
        """Procura por todos os arquivos .fdf e .psf na pasta do script."""
        fdf_files = [f for f in os.listdir(SCRIPT_DIR) if f.endswith('.fdf')]
        psf_files = [f for f in os.listdir(SCRIPT_DIR) if f.endswith('.psf')]

        if fdf_files:
            self.fdf_path = os.path.join(SCRIPT_DIR, fdf_files[0])
        self.psf_paths = [os.path.join(SCRIPT_DIR, f) for f in psf_files]

    def create_widgets(self):
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        fdf_frame = tk.LabelFrame(main_frame, text="Arquivo FDF", padx=10, pady=5)
        fdf_frame.pack(fill=tk.X, pady=5)
        fdf_text = f"Arquivo FDF: {os.path.basename(self.fdf_path)}" if self.fdf_path else "Nenhum selecionado."
        self.fdf_label = tk.Label(fdf_frame, text=fdf_text)
        self.fdf_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        psf_frame = tk.LabelFrame(main_frame, text="Arquivos PSF", padx=10, pady=5)
        psf_frame.pack(fill=tk.X, pady=5)
        psf_text = f"Arquivos PSF: {len(self.psf_paths)} selecionados." if self.psf_paths else "Nenhum selecionado."
        self.psf_label = tk.Label(psf_frame, text=psf_text)
        self.psf_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.stop_button = tk.Button(main_frame, text="Interromper Cálculo", command=self.interromper_calculo, state=tk.DISABLED)
        self.stop_button.pack(pady=5)

        feedback_frame = tk.LabelFrame(main_frame, text="Status", padx=10, pady=5)
        feedback_frame.pack(fill=tk.X, pady=10)

        self.restarts_label = tk.Label(feedback_frame, text="Reinícios: 0")
        self.restarts_label.pack(pady=5)
        
    def check_last_run(self):
        if not self.state_data or not self.config_data["auto_restart_enabled"]:
            return

        last_folder_path = self.state_data.get("output_folder")
        if last_folder_path and os.path.exists(last_folder_path):
            fdf_files = [f for f in os.listdir(last_folder_path) if f.endswith('.fdf')]
            if fdf_files:
                fdf_name = fdf_files[0]
                status = check_calculation_status(last_folder_path, fdf_name)
                
                if status == "incomplete":
                    self.fdf_path = os.path.join(last_folder_path, fdf_name)
                    self.psf_paths = [os.path.join(last_folder_path, f) for f in os.listdir(last_folder_path) if f.endswith('.psf')]
                    self.restarts = self.state_data.get("restarts", 0)
                    self.restarts_label.config(text=f"Reinícios: {self.restarts}")

    def iniciar_calculo_auto(self):
        if not self.fdf_path or not self.psf_paths:
            messagebox.showwarning("Aviso", "Não foi encontrado um arquivo FDF ou PSF na pasta do script. O aplicativo será fechado.")
            self.destroy()
            return
            
        restarting = self.state_data and self.config_data["auto_restart_enabled"]
        self.iniciar_calculo(restarting=restarting)

    def iniciar_calculo(self, restarting=False):
        if self.siesta_process and self.siesta_process.poll() is None:
            messagebox.showwarning("Aviso", "Já existe um cálculo em andamento. Interrompa-o primeiro.")
            return

        output_folder = os.getcwd()
        fdf_name = os.path.basename(self.fdf_path)
        output_file_name = fdf_name.replace('.fdf', '.out')
        
        if not restarting:
            self.restarts = 0
            self.state_data = {"output_folder": output_folder, "restarts": self.restarts}
            use_restart_flag = False
        else:
            self.restarts += 1
            self.state_data["restarts"] = self.restarts
            dm_file_path = os.path.join(output_folder, fdf_name.replace('.fdf', '.DM'))
            use_restart_flag = os.path.exists(dm_file_path)

        self.restarts_label.config(text=f"Reinícios: {self.restarts}")
        save_state(self.state_data)

        siesta_command = get_siesta_command(fdf_name, use_restart_flag=use_restart_flag)
        
        try:
            self.output_file_handle = open(output_file_name, 'w')
            
            with open(self.fdf_path, 'r') as fdf_input:
                self.siesta_process = subprocess.Popen(
                    siesta_command,
                    shell=True,
                    cwd=output_folder,
                    stdin=fdf_input,
                    stdout=self.output_file_handle,
                    stderr=subprocess.STDOUT
                )

            self.stop_button.config(state=tk.NORMAL)
            self.monitor_process()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível iniciar o cálculo. Erro: {e}")
            self.stop_button.config(state=tk.DISABLED)
            if self.output_file_handle:
                self.output_file_handle.close()

    def interromper_calculo(self):
        if self.siesta_process and self.siesta_process.poll() is None:
            try:
                parent = psutil.Process(self.siesta_process.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
                messagebox.showinfo("Interrompido", "Cálculo Siesta interrompido com sucesso.")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.siesta_process.kill()
                messagebox.showinfo("Interrompido", "Cálculo Siesta interrompido com sucesso (forçado).")
            finally:
                self.siesta_process = None
                if self.output_file_handle:
                    self.output_file_handle.close()
                self.stop_button.config(state=tk.DISABLED)
        else:
            messagebox.showwarning("Aviso", "Nenhum cálculo em andamento para interromper.")

    def monitor_process(self):
        if self.siesta_process and self.siesta_process.poll() is None:
            self.after(1000, self.monitor_process)
        else:
            self.stop_button.config(state=tk.DISABLED)
            if self.output_file_handle:
                self.output_file_handle.close()
            
            time.sleep(1) # Aguarda um pouco para o arquivo ser salvo completamente

            if self.fdf_path:
                output_folder = os.getcwd()
                fdf_name = os.path.basename(self.fdf_path)
                status = check_calculation_status(output_folder, fdf_name)
                
                if status == "completed":
                    concluido_file_path = os.path.join(output_folder, "concluido.txt")
                    try:
                        with open(concluido_file_path, "w") as f:
                            f.write("O cálculo Siesta foi concluído com sucesso.\n")
                            f.write(f"Data e hora de conclusão: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    except Exception as e:
                        print(f"Erro: Não foi possível criar o arquivo concluido.txt. Erro: {e}")
                    finally:
                        self.destroy()

# --- Ponto de Entrada Principal ---
if __name__ == "__main__":
    app = SiestaApp()
    app.mainloop()
