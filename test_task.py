import socket
import pickle
import sys

def submit_task(task_code, args):
    """Trimite un task către server pentru procesare"""
    try:
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('127.0.0.1', 5001))  
        
        
        task_data = {
            'code': task_code,
            'args': args
        }
        
        
        s.send(pickle.dumps(task_data))
        
       
        result = pickle.loads(s.recv(4096))
        s.close()
        
        return result
    except Exception as e:
        return {
            'exit_code': -1,
            'error': f'Eroare la trimiterea task-ului: {str(e)}'
        }

if __name__ == "__main__":
    
    task_code = """
import sys

try:
    if len(sys.argv) < 3:
        print("Error: Need 2 arguments")
        sys.exit(1)
    
    a = float(sys.argv[1])
    b = float(sys.argv[2])
    suma = a + b
    print(f"{a} + {b} = {suma}")
    sys.exit(0)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
"""
    
    
    args = ["15", "25"]
    
    print(f"Trimit task pentru suma: {args[0]} + {args[1]}")
    
    
    result = submit_task(task_code, args)
    
    
    print(f"Exit code: {result.get('exit_code', 'N/A')}")
    
    if 'stdout' in result and result['stdout']:
        print(f"Output: {result['stdout'].strip()}")
    
    if 'stderr' in result and result['stderr']:
        print(f"Errors: {result['stderr'].strip()}")
    
    if 'error' in result:
        print(f"System error: {result['error']}")