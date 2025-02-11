import socket
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from utils import send_data, receive_data

class GameWindow(QWidget):
    FIELD_WIDTH = 400
    FIELD_HEIGHT = 400

    def __init__(self, client_socket, player_color):
        super().__init__()

        self.client_socket = client_socket
        self.setWindowTitle("Космический Лэндер — Игра с двумя игроками")
        self.setGeometry(100, 100, self.FIELD_WIDTH, self.FIELD_HEIGHT)
        self.setFixedSize(self.FIELD_WIDTH, self.FIELD_HEIGHT)

        # Позиции шариков игроков
        self.player_positions = {
            "blue": [100, 200],
            "red": [300, 200]
        }

        # Управление текущего игрока
        self.current_color = player_color
        self.velocity_x = 0
        self.velocity_y = 0

        # Гравитация
        self.gravity = 0.5

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

        # Обновление координат текущего игрока
        self.player_positions[self.current_color][0] += self.velocity_x
        self.player_positions[self.current_color][1] += self.velocity_y

        # Ограничения границ поля
        self.player_positions[self.current_color][0] = max(0, min(self.FIELD_WIDTH - 10, self.player_positions[self.current_color][0]))
        self.player_positions[self.current_color][1] = max(0, min(self.FIELD_HEIGHT - 10, self.player_positions[self.current_color][1]))

        # Отправка новых позиций серверу
        try:
            x, y = self.player_positions[self.current_color]
            send_data(self.client_socket, f"move:{self.current_color},{x},{y}")
        except Exception:
            self.close()

        self.update()

    def receive_data_from_server(self):
        """Получение позиций игроков от сервера."""
        try:
            message = receive_data(self.client_socket)
            if message.startswith("move:"):
                data = message.split(":")[1].split(",")
                color = data[0]
                x, y = int(data[1]), int(data[2])
                self.player_positions[color] = [x, y]
        except:
            pass

    def paintEvent(self, event):
        """Отрисовка игроков."""
        painter = QPainter(self)

        # Рисуем игровое поле
        painter.setBrush(QColor("white"))
        painter.drawRect(0, 0, self.FIELD_WIDTH, self.FIELD_HEIGHT)

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

            send_data(self.client_socket, "status")
            status = receive_data(self.client_socket)

            if status == "2":
                self.status_label.setText("Начало игры!")
                self.timer.stop()
                self.start_game(self.player_color)
            elif status == "1":
                self.status_label.setText("Ожидаем второго игрока...")
            elif status == "3":
                self.status_label.setText("Вы наблюдатель.")
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