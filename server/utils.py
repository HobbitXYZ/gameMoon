import pickle

def send_data(sock, data):
    sock.sendall(pickle.dumps(data))

def receive_data(sock):
    data = sock.recv(8192)
    if not data:  # Если получили пустые данные
        raise ConnectionError("Клиент отключился")  # Поднимаем исключение
    return pickle.loads(data)