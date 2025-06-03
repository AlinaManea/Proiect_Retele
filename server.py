import socket
import threading
import pickle
import os
import tempfile
import queue
import time

class Server:
    def __init__(self, port=5000):
        self.port = port
        self.active_clients = [] 
        self.current_client_index = 0
        self.client_locks = {} 
        
        
        self.registration_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.registration_socket.bind(('127.0.0.1', port))
        
        
        self.task_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.task_socket.bind(('127.0.0.1', port + 1))
        self.task_socket.listen(5)
        
        
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()

    def handle_client_registration(self):
        print(f"[SERVER] Ascult pe portul {self.port} pentru înregistrări...")
        while True:
            try:
                mesaj, adresa_client = self.registration_socket.recvfrom(1024)
                mesaj = mesaj.decode()

                if mesaj.startswith("register:"):
                    port_client = int(mesaj.split(":")[1])
                    client = (adresa_client[0], port_client)
                    if client not in self.active_clients:
                        self.active_clients.append(client)
                        self.client_locks[client] = threading.Lock()
                        print(f"[SERVER] Client înregistrat: {client}")

                elif mesaj.startswith("unregister:"):
                    port_client = int(mesaj.split(":")[1])
                    client = (adresa_client[0], port_client)
                    if client in self.active_clients:
                        self.active_clients.remove(client)
                        if client in self.client_locks:
                            del self.client_locks[client]
                        print(f"[SERVER] Client delogat: {client}")
            except Exception as e:
                print(f"[SERVER] Eroare la procesarea înregistrării: {e}")

    def get_next_available_client(self):
        """Găsește următorul client disponibil folosind round-robin"""
        if not self.active_clients:
            return None
            
        start_index = self.current_client_index
        while True:
            client = self.active_clients[self.current_client_index]
            self.current_client_index = (self.current_client_index + 1) % len(self.active_clients)
            
            if client in self.client_locks and self.client_locks[client].acquire(blocking=False):
                return client
                
            if self.current_client_index == start_index:
                return None

    def handle_task_requests(self):
        print(f"[SERVER] Ascult pe portul {self.port + 1} pentru cereri de procesare...")
        while True:
            try:
                conn, addr = self.task_socket.accept()
                print(f"[SERVER] Am primit o cerere de procesare de la {addr}")
                
                
                task_data = conn.recv(4096)
                if not task_data:
                    continue
                    
                task_info = pickle.loads(task_data)
                
                
                client = self.get_next_available_client()
                if not client:
                    error_response = {
                        'error': 'Nu există clienți disponibili pentru procesare',
                        'exit_code': -1
                    }
                    conn.send(pickle.dumps(error_response))
                    conn.close()
                    continue

                try:
                    print(f"[SERVER] Distribuie task către clientul {client}")
                    
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.settimeout(30)  
                    
                    try:
                        client_socket.connect((client[0], client[1]))
                        client_socket.send(task_data)
                        
                        
                        result = client_socket.recv(4096)
                        
                        
                        conn.send(result)
                    except Exception as e:
                        print(f"[SERVER] Eroare la comunicarea cu clientul {client}: {e}")
                        error_response = {
                            'error': f'Eroare la comunicarea cu clientul: {str(e)}',
                            'exit_code': -1
                        }
                        conn.send(pickle.dumps(error_response))
                    finally:
                        client_socket.close()
                        
                except Exception as e:
                    print(f"[SERVER] Eroare la procesarea task-ului: {e}")
                    error_response = {
                        'error': f'Eroare la procesarea task-ului: {str(e)}',
                        'exit_code': -1
                    }
                    conn.send(pickle.dumps(error_response))
                finally:
                    
                    if client in self.client_locks:
                        self.client_locks[client].release()
                    conn.close()
                    
            except Exception as e:
                print(f"[SERVER] Eroare la acceptarea conexiunii: {e}")

    def start(self):
        
        registration_thread = threading.Thread(target=self.handle_client_registration)
        registration_thread.daemon = True
        
        
        task_thread = threading.Thread(target=self.handle_task_requests)
        task_thread.daemon = True
        
        registration_thread.start()
        task_thread.start()
        
        print("[SERVER] Server pornit și gata să proceseze cereri...")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[SERVER] Închidere server...")
        finally:
            self.registration_socket.close()
            self.task_socket.close()

if __name__ == "__main__":
    server = Server()
    server.start()