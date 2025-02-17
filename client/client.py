import socket
import random
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from utils import send_data, receive_data

class GameWindow(QWidget):
    FIELD_WIDTH = 800
    FIELD_HEIGHT = 800
    PLATFORM_WIDTH = 50
    PLATFORM_HEIGHT = 10

    def __init__(self, client_socket, player_color):
        super().__init__()

        self.client_socket = client_socket
        self.setWindowTitle("Космический Лэндер — Игра с двумя игроками")
        self.setGeometry(100, 100, self.FIELD_WIDTH, self.FIELD_HEIGHT)
        self.setFixedSize(self.FIELD_WIDTH, self.FIELD_HEIGHT)

        # Позиции шариков игроков
        self.player_positions = {
            "blue": [200, 0],
            "red": [600, 0]
        }

        # Управление текущего игрока
        self.current_color = player_color
        self.velocity_x = 0
        self.velocity_y = 0

        # Гравитация
        self.gravity = 0.2

        # Таймер обновления игры
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(30)

        # Таймер прослушивания сервера
        self.listener = QTimer()
        self.listener.timeout.connect(self.receive_data_from_server)
        self.listener.start(30)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event):
        """Обработка нажатий клавиш."""
        key = event.text().lower()
        if key == 'w':
            self.velocity_y = -5
        elif key == 's':
            self.velocity_y = 5
        elif key == 'a':
            self.velocity_x = -5
        elif key == 'd':
            self.velocity_x = 5

    def keyReleaseEvent(self, event):
        """Остановка движения при отпускании клавиш."""
        key = event.text().lower()
        if key in {'w', 's'}:
            self.velocity_y = 0
        if key in {'a', 'd'}:
            self.velocity_x = 0

    def update_game(self):
        """Обновление позиций игроков и отправка данных серверу."""
        # Применение гравитации
        self.velocity_y += self.gravity

        # Вычисляем новые координаты
        new_x = self.player_positions[self.current_color][0] + self.velocity_x
        new_y = self.player_positions[self.current_color][1] + self.velocity_y

        # Ограничение по вертикальной границе в центре
        middle_x = self.FIELD_WIDTH // 2
        if self.current_color == "blue" and new_x + 10 > middle_x:
            new_x = middle_x - 10
        elif self.current_color == "red" and new_x < middle_x:
            new_x = middle_x

        # Ограничение по боковым границам
        new_x = max(4, min(self.FIELD_WIDTH - 14, new_x))  # 4 - левая граница, 14 - правая
        new_y = max(0, min(self.FIELD_HEIGHT - 10, new_y))  # Верх и низ

        # Обновляем позицию
        self.player_positions[self.current_color] = [new_x, new_y]

        # Отправка новых позиций серверу
        try:
            send_data(self.client_socket, f"move:{self.current_color}:{new_x}:{new_y}")
        except Exception:
            self.close()

        self.update()

    def receive_data_from_server(self):
        """Получение позиций игроков от сервера."""
        try:
            message = receive_data(self.client_socket)
            if message.startswith("move:"):

                parts = message.split(":")
                if len(parts) == 4:  # move:цвет:x:y
                    color, x, y = parts[1], float(parts[2]), float(parts[3])
                    self.player_positions[color] = [x, y]
                    self.update()
        except Exception as e:
            print(f"Ошибка получения данных: {e}")

    def paintEvent(self, event):
        """Отрисовка игроков и границ."""
        painter = QPainter(self)

        # Рисуем игровое поле
        painter.setBrush(QColor("white"))
        painter.drawRect(0, 0, self.FIELD_WIDTH, self.FIELD_HEIGHT)

        # Рисуем границы
        painter.setBrush(QColor("black"))

        # Вертикальная граница посередине
        middle_x = self.FIELD_WIDTH // 2
        painter.drawRect(middle_x - 2, 0, 4, self.FIELD_HEIGHT)  # Толщина 4 пикселя

        # Левые и правые границы
        painter.drawRect(0, 0, 4, self.FIELD_HEIGHT)  # Левая
        painter.drawRect(self.FIELD_WIDTH - 4, 0, 4, self.FIELD_HEIGHT)  # Правая

        # Рисуем синий шарик
        painter.setBrush(QColor("blue"))
        x, y = self.player_positions["blue"]
        painter.drawEllipse(int(x), int(y), 10, 10)

        # Рисуем красный шарик
        painter.setBrush(QColor("red"))
        x, y = self.player_positions["red"]
        painter.drawEllipse(int(x), int(y), 10, 10)


class LobbyWindow(QWidget):
    def __init__(self, client_socket, parent_window):
        super().__init__()

        self.client_socket = client_socket
        self.parent_window = parent_window
        self.player_color = None  # Изначально цвет не задан
        self.setWindowTitle("Лобби — Космический Лэндер")
        self.setGeometry(200, 200, 300, 200)

        self.status_label = QLabel("Подключение к серверу...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        self.setLayout(layout)

        # Таймер для запуска игры
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_game_start)
        self.timer.start(500)


    def check_game_start(self):
        """Проверяет, готово ли лобби для игры."""
        try:
            if not self.player_color:  # Получаем цвет только один раз
                self.player_color = receive_data(self.client_socket)
                print(f"Цвет игрока: {self.player_color}")

                # Если цвет "full", сразу возвращаемся к выбору лобби
                if self.player_color == "full":
                    QMessageBox.information(self, "Лобби переполнено", "Лобби переполнено. Выберите другое лобби.")
                    self.close()
                    self.timer.stop()
                    self.parent_window.show()
                    return  # ВАЖНО: Прерываем выполнение функции

            send_data(self.client_socket, "status")
            print("Отправка запроса статуса лобби: status")  # Логируем отправку
            status = receive_data(self.client_socket)
            print(f"Получен статус лобби: {status}")  # Логируем полученный статус

            if status == "2":
                self.status_label.setText("Начало игры!")
                self.timer.stop()
                self.start_game(self.player_color)
            elif status == "1":
                self.status_label.setText("Ожидаем второго игрока...")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка связи с сервером: {e}")
            self.close()

    def start_game(self, color):
        """Запускает игровое окно."""
        self.close()
        self.game_window = GameWindow(self.client_socket, color)
        self.game_window.show()

class SpaceLanderClient(QWidget):
    def __init__(self):
        super().__init__()

        self.client_socket = None
        self.setWindowTitle("Космический Лэндер — Выбор Лобби")
        self.setGeometry(100, 100, 300, 300)

        layout = QVBoxLayout()

        self.label = QLabel("Выберите лобби для подключения:")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        for i in range(1, 7):
            button = QPushButton(f"Лобби {i}")
            button.clicked.connect(lambda checked, i=i: self.connect_to_lobby(i))
            layout.addWidget(button)

        self.setLayout(layout)

    def connect_to_lobby(self, lobby_number):
        """Подключается к серверу и отображает новое окно лобби."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect(('127.0.0.1', 5555))

            receive_data(self.client_socket)
            send_data(self.client_socket, str(lobby_number))
            response = receive_data(self.client_socket)

            self.hide()

            # Открытие окна лобби
            self.lobby_window = LobbyWindow(self.client_socket, self)
            self.lobby_window.show()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка подключения: {e}")

if __name__ == "__main__":
    app = QApplication([])
    client_window = SpaceLanderClient()
    client_window.show()
    app.exec()