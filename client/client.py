import socket
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPalette
from utils import send_data, receive_data


class LobbyWindow(QWidget):
    def __init__(self, client_socket, parent_window):
        super().__init__()

        self.client_socket = client_socket
        self.parent_window = parent_window
        self.setWindowTitle("Лобби — Космический Лэндер")
        self.setGeometry(200, 200, 300, 200)

        # Создание интерфейса
        layout = QVBoxLayout()

        self.status_label = QLabel("Ожидание соединения...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Кнопка "Назад"
        self.back_button = QPushButton("Назад")
        self.back_button.clicked.connect(self.go_back)
        layout.addWidget(self.back_button)

        self.setLayout(layout)

        # Таймер для обновления статуса
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_status)
        self.timer.start(1000)  # Обновление каждые 1000 мс

    def update_status(self):
        """Получает статус подключения от сервера и меняет цвет окна."""
        try:
            send_data(self.client_socket, "status")
            status = receive_data(self.client_socket)

            if status == "2":
                self.status_label.setText("Два пользователя подключены")
                self.set_background_color("green")
                self.status_label.setStyleSheet("color: black;")
            elif status == "1":
                self.status_label.setText("Один пользователь подключен")
                self.set_background_color("yellow")
                self.status_label.setStyleSheet("color: black;")
            elif status == "3":
                self.status_label.setText("Лобби переполнено, наблюдайте за игрой")
                self.set_background_color("black")
                self.status_label.setStyleSheet("color: white;")
            else:
                self.status_label.setText("Нет соединения")
                self.set_background_color("red")
                self.status_label.setStyleSheet("color: black;")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Соединение потеряно: {e}")
            self.close()

    def set_background_color(self, color):
        """Меняет цвет фона окна."""
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(color))
        self.setPalette(palette)

    def go_back(self):
        """Закрывает текущее окно и возвращает к выбору лобби."""
        self.timer.stop()  # Останавливаем таймер
        self.client_socket.close()  # Закрываем соединение с сервером
        self.close()
        self.parent_window.show()


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

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def connect_to_lobby(self, lobby_number):
        """Подключается к серверу и отображает новое окно лобби."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect(('127.0.0.1', 5555))

            receive_data(self.client_socket)
            send_data(self.client_socket, str(lobby_number))
            response = receive_data(self.client_socket)

            self.status_label.setText(response)
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