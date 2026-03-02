import socket
import pyaudio
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import io
import os
import queue # <--- Para manejar el audio sin bloquear la red
from datetime import datetime

# Configuración
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class ServidorMultimedia:
    def __init__(self, root):
        self.root = root
        self.root.title("Consola de Monitoreo Pro v2")
        self.root.geometry("800x600")
        self.root.configure(bg="#1e272e")
        
        self.ip_seleccionada = None
        self.sockets_clientes = {}
        self.audio_queue = queue.Queue() # Cola para el audio
        
        if not os.path.exists("capturas"): os.makedirs("capturas")
        
        # UI (Simplificada para el ejemplo)
        tk.Label(root, text="SISTEMA DE MONITOREO", font=("Arial", 16, "bold"), bg="#1e272e", fg="#0fbcf9").pack(pady=10)
        self.lista_ui = tk.Listbox(root, width=70, height=10, bg="#2f3542", fg="white")
        self.lista_ui.pack(padx=20, pady=10)
        
        btn_frame = tk.Frame(root, bg="#1e272e")
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="🔊 ESCUCHAR", command=self.escuchar, bg="#05c46b", fg="white", width=12).grid(row=0, column=0, padx=5)
        tk.Button(btn_frame, text="📸 CAPTURA", command=self.solicitar_captura, bg="#3c40c6", fg="white", width=12).grid(row=0, column=1, padx=5)
        tk.Button(btn_frame, text="■ DETENER", command=self.detener, bg="#f53b57", fg="white", width=12).grid(row=0, column=2, padx=5)

        self.lbl_status = tk.Label(root, text="ESPERANDO...", bg="#485460", fg="white")
        self.lbl_status.pack(side=tk.BOTTOM, fill=tk.X)

        # Hilo para reproducir audio (Consumidor)
        threading.Thread(target=self.reproductor_worker, daemon=True).start()
        # Hilo para aceptar conexiones
        threading.Thread(target=self.servidor_red, daemon=True).start()

    def reproductor_worker(self):
        """Este hilo solo se encarga de sonar el audio que llega a la cola."""
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)
        while True:
            data = self.audio_queue.get() # Espera a que haya datos
            if data:
                stream.write(data)

    def recv_all(self, conn, n):
        """Lee exactamente n bytes. Si falla, cierra el bucle."""
        data = bytearray()
        while len(data) < n:
            try:
                packet = conn.recv(n - len(data))
                if not packet: return None
                data.extend(packet)
            except: return None
        return data

    def manejar_datos(self, conn, ip):
        print(f"[*] Manejando datos de {ip}")
        try:
            while True:
                # 1. Leer Prefijo
                prefijo_raw = self.recv_all(conn, 4)
                if not prefijo_raw: break
                prefijo = prefijo_raw.decode('utf-8', errors='ignore')

                if prefijo == "AUD:":
                    # 2. Leer Audio (2 bytes por sample * CHUNK)
                    audio_data = self.recv_all(conn, CHUNK * 2)
                    if not audio_data: break
                    if self.ip_seleccionada == ip:
                        self.audio_queue.put(bytes(audio_data)) # Lo mandamos a la cola
                
                elif prefijo == "IMG:":
                    # 3. Leer Tamaño
                    size_bytes = self.recv_all(conn, 4)
                    if not size_bytes: break
                    size = int.from_bytes(size_bytes, byteorder='big')
                    
                    # 4. Leer Imagen
                    img_data = self.recv_all(conn, size)
                    if not img_data: break
                    self.root.after(0, self.mostrar_y_guardar_imagen, img_data, ip)
                else:
                    print(f"[!] Desincronización con {ip}. Prefijo recibido: {prefijo}")
                    break # Rompe el bucle si hay basura
        except Exception as e:
            print(f"Error: {e}")
        finally:
            conn.close()
            if ip in self.sockets_clientes: del self.sockets_clientes[ip]
            self.root.after(0, self.actualizar_lista)

    def servidor_red(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('0.0.0.0', 5001))
        s.listen(5)
        while True:
            conn, addr = s.accept()
            self.sockets_clientes[addr[0]] = conn
            self.root.after(0, self.actualizar_lista)
            threading.Thread(target=self.manejar_datos, args=(conn, addr[0]), daemon=True).start()

    # --- Métodos de UI (Iguales a los anteriores pero simplificados) ---
    def actualizar_lista(self):
        self.lista_ui.delete(0, tk.END)
        for ip in self.sockets_clientes: self.lista_ui.insert(tk.END, f"Dispositivo: {ip}")

    def escuchar(self):
        sel = self.lista_ui.curselection()
        if sel:
            self.ip_seleccionada = self.lista_ui.get(sel[0]).split(": ")[1]
            self.lbl_status.config(text=f"ESCUCHANDO A: {self.ip_seleccionada}", fg="#05c46b")

    def detener(self):
        self.ip_seleccionada = None
        self.lbl_status.config(text="SILENCIO", fg="white")

    def solicitar_captura(self):
        sel = self.lista_ui.curselection()
        if sel:
            ip = self.lista_ui.get(sel[0]).split(": ")[1]
            conn = self.sockets_clientes.get(ip)
            if conn: conn.sendall(b"SCREEN")

    def mostrar_y_guardar_imagen(self, raw_data, ip):
        timestamp = datetime.now().strftime("%H%m%S")
        with open(f"capturas/{ip}_{timestamp}.jpg", "wb") as f: f.write(raw_data)
        
        ventana = tk.Toplevel(self.root)
        img = Image.open(io.BytesIO(raw_data))
        img.thumbnail((800, 600))
        img_tk = ImageTk.PhotoImage(img)
        lbl = tk.Label(ventana, image=img_tk); lbl.image = img_tk; lbl.pack()

if __name__ == "__main__":
    root = tk.Tk()
    app = ServidorMultimedia(root)
    root.mainloop()