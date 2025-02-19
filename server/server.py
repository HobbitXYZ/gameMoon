import socket
import threading
import random
import os
from utils import send_data, receive_data

# Предустановленные лобби и блокировки для каждого лобби
lobbies = {f"Lobby {i}": [] for i in range(1, 7)}
lobby_locks = {lobby_name: threading.Lock() for lobby_name in lobbies}

def log_endgame_to_file(player_name, time, landed):
    """Записывает имя игрока и время в файл, если таких данных нет."""
    log_file = "endgame_log.txt"

    # Приводим всё к строкам для корректного сравнения
    time = str(time)
    landed = str(landed)

    # Проверяем, существует ли файл
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            existing_logs = set(line.strip() for line in f)  # Читаем строки и убираем пробелы

        # Формируем новую запись
        new_entry = f"{player_name},{time},{landed}"

        # Если такая запись уже есть — выходим
        if new_entry in existing_logs:
            return  

    # Записываем новую строку
    with open(log_file, "a") as f:
        f.write(f"{player_name},{time},{landed}\n")

def handle_client(client_socket, address):
    """Обрабатывает подключение клиента."""
    lobby_name = None
    send_results_file(client_socket)
    try:
        send_data(client_socket, f"Доступные лобби: {', '.join(lobbies.keys())}")
        send_data(client_socket, "Введите номер лобби (например, '1' для Lobby 1):")

        lobby_choice = receive_data(client_socket)
        lobby_name = f"Lobby {lobby_choice}"

        if lobby_name in lobbies:
            with lobby_locks[lobby_name]:
                # Проверка переполненности лобби
                if len(lobbies[lobby_name]) >= 2:
                    send_data(client_socket, "full")  # Лобби переполнено
                    print("Лобби переполнено, перенаправляем игрока")
                    
                    # Очистка буфера, чтобы клиент не отправлял "status" перед повторным выбором лобби
                    try:
                        client_socket.settimeout(0.5)
                        while receive_data(client_socket):  # Пытаемся считать оставшиеся данные
                            pass
                    except:
                        pass  # Игнорируем ошибки тайм-аута

                    return handle_client(client_socket, address)  # Перезапускаем выбор лобби

                # Назначение цвета
                color = "blue" if len(lobbies[lobby_name]) == 0 else "red"
                lobbies[lobby_name].append((client_socket, color))

                # Генерация случайных координат для платформы
                if color == "blue":
                    platform_start = random.randint(4, 330)
                    platform_end = platform_start + 60
                else:
                    platform_start = random.randint(404, 730)
                    platform_end = platform_start + 60

                print(f"[DEBUG] {color} - Координаты платформы: {platform_start}, {platform_end}")

                # Отправляем **единый пакет** с цветом и координатами
                send_data(client_socket, (color, platform_start, platform_end))

            send_data(client_socket, f"Вы подключились к {lobby_name}")
            broadcast_lobby_state(lobby_name)

            while True:
                try:
                    request = receive_data(client_socket)
                    if request == "":
                        print(1)
                        break
                    if request.startswith("status"):
                        send_lobby_status(client_socket, lobby_name)
                    elif request.startswith("move:"):
                        broadcast_game_update(request, lobby_name, client_socket)
                    elif request.startswith("endgame:"):
                        # Извлекаем имя игрока и время из запроса
                        player_name, time, landed = request[len("endgame:"):].split(":")
                        # Логируем информацию в файл
                        log_endgame_to_file(player_name, time, landed)
                        # Формируем сообщение для другого игрока
                        print(1)
                        endgame_message = f"endgame:{player_name}:{time}:{landed}"
                        print(2)
                        # Отправляем это сообщение другому клиенту в лобби
                        send_endgame_message(lobby_name, endgame_message, client_socket)
                    elif request.startswith("theend:"):
                        if lobby_name:
                            clean_up_client(client_socket, lobby_name, color)
                    else:
                        print(f"Неизвестный запрос от клиента: {request}")
                except (ConnectionResetError, ConnectionAbortedError):
                    print(f"Соединение с клиентом {address} потеряно.")
                    break
        else:
            send_data(client_socket, "full.")

    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        if lobby_name:
            clean_up_client(client_socket, lobby_name, color)

def send_endgame_message(lobby_name, message, sender_socket):
    """Отправляет сообщение об окончании игры другому игроку в лобби."""
    with lobby_locks[lobby_name]:
        clients = lobbies.get(lobby_name, [])
        for client, color in clients:
            if client != sender_socket:
                try:
                    send_data(client, message)
                except Exception as e:
                    print(f"Ошибка отправки сообщения об окончании игры: {e}")
                    clients.remove((client, color))

def clean_up_client(client_socket, lobby_name, color):
    """Очистка состояния клиента и лобби."""
    with lobby_locks[lobby_name]:
        if (client_socket, color) in lobbies[lobby_name]:  # проверка с учетом цвета
            lobbies[lobby_name].remove((client_socket, color))
            print(f"[DEBUG] Клиент {client_socket} удален из {lobby_name}.")
    
    broadcast_lobby_state(lobby_name)
    client_socket.close()

def broadcast_game_update(request, lobby_name, sender_socket):
    """Рассылает обновление игры всем клиентам в лобби, кроме отправителя."""
    with lobby_locks[lobby_name]:
        clients = lobbies.get(lobby_name, [])
        #print(f"Рассылка движения: {request} в {lobby_name} для {len(clients)} игроков")  # Логирование

        for client, color in clients:
            if client != sender_socket:
                try:
                    #print(f"Отправка {request} клиенту {color}")  # Лог
                    send_data(client, request)
                except Exception as e:
                    print(f"Ошибка отправки: {e}")
                    clients.remove((client, color))

def send_lobby_status(client_socket, lobby_name):
    """Отправляет статус лобби клиенту."""
    with lobby_locks[lobby_name]:
        clients = lobbies[lobby_name]
        num_clients = len(clients)

    if num_clients == 2:
        send_data(client_socket, "2")  # Зеленый индикатор
    elif num_clients == 1:
        send_data(client_socket, "1")  # Желтый индикатор
    else:
        send_data(client_socket, "0")  # Красный индикатор
        
def broadcast_lobby_state(lobby_name):
    """Уведомляет всех игроков в лобби о текущем количестве игроков."""
    with lobby_locks[lobby_name]:
        clients = lobbies.get(lobby_name, [])
        for client, color in clients:
            try:
                send_data(client, f"Вы в лобби '{lobby_name}' с {len(clients)} игроками.")
            except:
                clients.remove((client, color))

def start_server():
    """Запускает сервер."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('0.0.0.0', 5555))
    server_socket.listen(10)
    print("Сервер запущен и ожидает подключения...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Подключение от {addr}")
        threading.Thread(target=handle_client, args=(client_socket, addr)).start()

def send_results_file(client_socket):
    """Отправляет содержимое файла endgame_log.txt клиенту."""
    try:
        with open("endgame_log.txt", "r", encoding="utf-8") as file:
            data = file.read()
        
        if not data.strip():
            send_data(client_socket, "empty")  # Файл пуст
        else:
            send_data(client_socket, data)
    except FileNotFoundError:
        send_data(client_socket, "not_found")  # Файл не найден
    except Exception as e:
        print(f"Ошибка при отправке файла: {e}")
        send_data(client_socket, "error")  # Общая ошибка

if __name__ == "__main__":
    start_server()