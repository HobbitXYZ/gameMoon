import pickle

def send_data(sock, data):
    sock.sendall(pickle.dumps(data))

def receive_data(sock):
    return pickle.loads(sock.recv(4096))