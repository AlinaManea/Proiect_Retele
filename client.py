import socket
import sys
import threading
import pickle
import time
import os
import tempfile
import subprocess
import atexit

class Client:
    def __init__(self, processing_port):
        self.processing_port = processing_port
        self.server_address = ('127.0.0.1', 5000)
        self.task_socket = None
        self.is_running = True
        
        
        atexit.register(self.cleanup)

    def register_with_server(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            mesaj = f"register:{self.processing_port}"
            s.sendto(mesaj.encode(), self.server_address)
            print(f"[CLIENT] M-am înregistrat la server cu portul de procesare {self.processing_port}")
            s.close()
        except Exception as e:
            print(f"[CLIENT] Eroare la înregistrarea cu serverul: {e}")
            sys.exit(1)

    def unregister_from_server(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            mesaj = f"unregister:{self.processing_port}"
            s.sendto(mesaj.encode(), self.server_address)
            print(f"[CLIENT] M-am delogat de la server (port {self.processing_port})")
            s.close()
        except Exception as e:
            print(f"[CLIENT] Eroare la delogare: {e}")

    def cleanup(self):
        """Funcție apelată la închiderea programului"""
        if self.is_running:
            self.is_running = False
            self.unregister_from_server()
            if self.task_socket:
                self.task_socket.close()

    def execute_task(self, task_data):
        """Execută un task primit de la server"""
        try:
            print("[CLIENT] Pregătesc executarea task-ului...")
            
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.py', mode='w') as temp_file:
                temp_file.write(task_data['code'])
                temp_file_path = temp_file.name

            print(f"[CLIENT] Execut task-ul cu argumentele: {task_data['args']}")
            
            
            result = subprocess.run(
                ['python', temp_file_path] + task_data['args'],
                capture_output=True,
                text=True,
                timeout=30  
            )
            
            
            os.unlink(temp_file_path)
            
            print(f"[CLIENT] Task executat cu exit code: {result.returncode}")
            
            return {
                'exit_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except subprocess.TimeoutExpired:
            print("[CLIENT] Task-ul a depășit timpul de execuție permis")
            return {
                'exit_code': -1,
                'error': 'Task execution timeout'
            }
        except Exception as e:
            print(f"[CLIENT] Eroare la executarea task-ului: {e}")
            return {
                'exit_code': -1,
                'error': str(e)
            }

    def handle_tasks(self):
        try:
            self.task_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.task_socket.bind(('127.0.0.1', self.processing_port))
            self.task_socket.listen(1)
            print(f"[CLIENT] Ascult pe portul {self.processing_port} pentru taskuri...")

            while self.is_running:
                try:
                    self.task_socket.settimeout(1)  
                    conn, addr = self.task_socket.accept()
                    print(f"[CLIENT] Am primit un task de la {addr}")
                    
                    
                    data = conn.recv(4096)
                    task_info = pickle.loads(data)
                    
                    
                    result = self.execute_task(task_info)
                    
                    
                    conn.send(pickle.dumps(result))
                    conn.close()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[CLIENT] Error processing task: {e}")
                    if 'conn' in locals():
                        conn.close()
        except Exception as e:
            print(f"[CLIENT] Error in task handling: {e}")
        finally:
            if self.task_socket:
                self.task_socket.close()

    def start(self):
        self.register_with_server()
        
        try:
            self.handle_tasks()
        except KeyboardInterrupt:
            print("\n[CLIENT] Închidere client...")
        finally:
            self.cleanup()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Folosire: python client.py <port>")
        sys.exit(1)

    processing_port = int(sys.argv[1])
    client = Client(processing_port)
    client.start()