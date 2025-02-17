import socket
import math
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPolygonF
from PyQt6.QtCore import QPointF
from utils import send_data, receive_data

class GameWindow(QWidget):
    FIELD_WIDTH = 800
    FIELD_HEIGHT = 800

    def __init__(self, client_socket, player_color, platform_start, platform_end):
        super().__init__()

        self.client_socket = client_socket
        self.setWindowTitle("Космический Лэндер — Игра с двумя игроками")
        self.setGeometry(100, 100, self.FIELD_WIDTH, self.FIELD_HEIGHT)
        self.setFixedSize(self.FIELD_WIDTH, self.FIELD_HEIGHT)

        # Позиции игроков
        self.player_positions = {
            "blue": [200, 0],
            "red": [600, 0]
        }

        # Координаты платформ
        self.platforms = {
            "blue": (platform_start, platform_end),
            "red": (platform_start, platform_end)
        }

        # Управление текущего игрока
        self.current_color = player_color
        self.velocity_x = 0
        self.velocity_y = 0
        self.player_angles = {
            "blue": 1,  # Угол для синего игрока
            "red": 1    # Угол для красного игрока
        }
        # Гравитация ТУТ
        self.gravity = 0.07

        # Таймер обновления игры
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(30)

        # Таймер прослушивания сервера
        self.listener = QTimer()
        self.listener.timeout.connect(self.receive_data_from_server)
        self.listener.start(30)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Словарь для отслеживания нажатых клавиш
        self.pressed_keys = {
            "A": False,
            "D": False
        }

    def keyPressEvent(self, event):
        """Обработка нажатий клавиш."""
        key = event.text().upper()  # Получаем нажатую клавишу в верхнем регистре
        if key == 'A':
            self.pressed_keys["A"] = True  # Помечаем, что клавиша A нажата
        elif key == 'D':
            self.pressed_keys["D"] = True  # Помечаем, что клавиша D нажата

    def keyReleaseEvent(self, event):
        """Обработка отпускания клавиш."""
        key = event.text().upper()  # Получаем отпущенную клавишу в верхнем регистре
        if key == 'A':
            self.pressed_keys["A"] = False  # Помечаем, что клавиша A отпущена
        elif key == 'D':
            self.pressed_keys["D"] = False  # Помечаем, что клавиша D отпущена

    def update_game(self):
        """Обновление позиций игроков и отправка данных серверу."""
        # Рассчитываем угол наклона ракеты в радианах
        angle_rad = math.radians(self.player_angles[self.current_color])

        self.velocity_y += self.gravity  # Гравитация всегда действует

        # Если никаких кнопок не нажато, ракета падает под действием гравитации
        if not self.pressed_keys["A"] and not self.pressed_keys["D"]:
            self.velocity_x = 0  # Нет горизонтального движения
            self.velocity_y += self.gravity  # Ракета падает под действием гравитации

        # Двигатели ракеты не дают гравитации полностью направлять её вниз
        if self.pressed_keys["A"] and self.pressed_keys["D"]:
            # Когда обе клавиши нажаты, ракета будет двигаться вверх по направлению носа
            self.velocity_x = math.sin(angle_rad) * 2  # Горизонтальное движение по направлению носа
            self.velocity_y = math.cos(angle_rad) * -2  # Вертикальное движение вверх, против гравитации

        # Обработка движения с помощью клавиш:
        if self.pressed_keys["A"] and not self.pressed_keys["D"]:
            self.player_angles[self.current_color] -= 3  # Поворот по часовой стрелке
            # Нормализация угла, чтобы он не выходил за пределы -180 до 180
            if self.player_angles[self.current_color] < -180:
                self.player_angles[self.current_color] += 360  # Приводим к положительному углу
        elif self.pressed_keys["D"] and not self.pressed_keys["A"]:
            self.player_angles[self.current_color] += 3  # Поворот против часовой стрелки
            # Нормализация угла, чтобы он не выходил за пределы -180 до 180
            if self.player_angles[self.current_color] > 180:
                self.player_angles[self.current_color] -= 360  # Приводим к отрицательному углу

        # Рассчитываем новый угол наклона ракеты на основе её движения
        if abs(self.player_angles[self.current_color]) < 90:
            if self.player_angles[self.current_color] < 0:
                self.player_angles[self.current_color] -= 1  # Поворот по часовой стрелке
            elif self.player_angles[self.current_color] > 0:
                self.player_angles[self.current_color] += 1  # Поворот против часовой стрелки
        elif abs(self.player_angles[self.current_color]) >= 90 and abs(self.player_angles[self.current_color]) < 180:
            if self.player_angles[self.current_color] < 0:
                self.player_angles[self.current_color] -= 1  # Поворот против часовой стрелки
            elif self.player_angles[self.current_color] > 0:
                self.player_angles[self.current_color] += 1  # Поворот по часовой стрелке
        else:
            self.player_angles[self.current_color] = 180

        # Вычисляем новые координаты ракеты
        new_x = self.player_positions[self.current_color][0] + self.velocity_x
        new_y = self.player_positions[self.current_color][1] + self.velocity_y

        # Ограничение по вертикальной границе
        middle_x = self.FIELD_WIDTH // 2
        if self.current_color == "blue" and new_x + 10 > middle_x:
            new_x = middle_x - 10
        elif self.current_color == "red" and new_x < middle_x:
            new_x = middle_x

        # Ограничение по боковым границам
        new_x = max(4, min(self.FIELD_WIDTH - 14, new_x))  # 4 - левая граница, 14 - правая
        new_y = max(0, min(self.FIELD_HEIGHT - 10, new_y))  # Верх и низ

        # Обновляем позицию ракеты
        self.player_positions[self.current_color] = [new_x, new_y]

        # Отправка новых позиций серверу
        try:
            send_data(self.client_socket, f"move:{self.current_color}:{new_x}:{new_y}:{self.player_angles[self.current_color]}")
        except Exception:
            self.close()

        self.update()

    def receive_data_from_server(self):
        """Получение позиций игроков от сервера и отправка своей позиции ракеты."""
        try:
            message = receive_data(self.client_socket)
            if message.startswith("move:"):
                parts = message.split(":")
                if len(parts) == 5:  # move:цвет:x:y:угол
                    color, x, y, angle = parts[1], float(parts[2]), float(parts[3]), float(parts[4])
                    self.player_positions[color] = [x, y]  # Обновляем позицию другого игрока
                    self.player_angles[color] = angle  # Обновляем угол наклона
                    self.update()
        except Exception as e:
            print(f"Ошибка получения данных: {e}")

    def send_position_to_server(self):
        """Отправка своей позиции ракеты на сервер."""
        try:
            # Получаем текущие координаты ракеты из player_positions
            new_x, new_y = self.player_positions[self.current_color]  # Теперь используем этот атрибут
            angle = self.player_angles[self.current_color]  # Получаем угол наклона ракеты
            
            # Формируем сообщение для отправки
            message = f"move:{self.current_color}:{new_x}:{new_y}:{angle}"
            
            # Отправляем данные серверу
            send_data(self.client_socket, message)
            
        except Exception as e:
            print(f"Ошибка отправки данных: {e}")
            self.close()

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

        # Рисуем платформы с учетом координат для каждого игрока
        for color, (start_x, end_x) in self.platforms.items():
            painter.setBrush(QColor("purple"))  # Цвет платформы
            painter.drawRect(start_x, self.FIELD_HEIGHT - 10, end_x - start_x, 10)

        # Рисуем ракеты для обоих игроков
        for color, (x, y) in self.player_positions.items():
            # Вершины ракеты (левая нижняя, правая нижняя, верхняя)
            points = [
                (x, y),  # Левая точка
                (x + 20, y),  # Правая точка
                (x + 10, y - 40),  # Верхняя точка
            ]

            # Применение поворота
            angle_rad = math.radians(self.player_angles[color])
            center_x = x + 5  # Центр ракеты
            center_y = y - 10

            rotated_points = []
            for px, py in points:
                # Поворот каждой точки
                rotated_x = center_x + (px - center_x) * math.cos(angle_rad) - (py - center_y) * math.sin(angle_rad)
                rotated_y = center_y + (px - center_x) * math.sin(angle_rad) + (py - center_y) * math.cos(angle_rad)
                rotated_points.append((rotated_x, rotated_y))

            # Рисуем ракету
            painter.setBrush(QColor(color))  # Используем цвет игрока
            polygon = QPolygonF([QPointF(x, y) for x, y in rotated_points])
            painter.drawPolygon(polygon)


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
                received_data = receive_data(self.client_socket)
                print(f"[DEBUG] Получены данные: {received_data}")  # Лог

                # Проверяем, что получили именно кортеж (цвет, платформа старт, платформа конец)
                if isinstance(received_data, tuple) and len(received_data) == 3:
                    self.player_color, platform_start, platform_end = received_data
                    self.platform_start = platform_start
                    self.platform_end = platform_end
                else:
                    QMessageBox.information(self, "Лобби переполнено", "Лобби переполнено. Выберите другое лобби.")
                    self.close()
                    self.timer.stop()
                    self.parent_window.show()
                    return  # ВАЖНО: Прерываем выполнение функции
                
                # Если цвет "full", сразу возвращаемся к выбору лобби
                if self.player_color == "full":
                    QMessageBox.information(self, "Лобби переполнено", "Лобби переполнено. Выберите другое лобби.")
                    self.close()
                    self.timer.stop()
                    self.parent_window.show()
                    return  # ВАЖНО: Прерываем выполнение функции
                else:
                    print(f"Цвет игрока: {self.player_color}")
                    print(f"Координаты платформы игрока {self.player_color}: Начало = {platform_start}, Конец = {platform_end}")

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
        self.game_window = GameWindow(self.client_socket, color, self.platform_start, self.platform_end)
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