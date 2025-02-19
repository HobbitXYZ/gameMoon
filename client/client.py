import socket
import math
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox, QLineEdit, QTableWidget, QTableWidgetItem, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPolygonF, QFont
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QBrush
from PyQt6.QtGui import QPen
from PyQt6.QtCore import QElapsedTimer
from utils import send_data, receive_data

class GameWindow(QWidget):
    FIELD_WIDTH = 800
    FIELD_HEIGHT = 800

    def __init__(self, client_socket, player_color, platform_start, platform_end, player_name):
        super().__init__()

        self.client_socket = client_socket
        self.player_name = player_name  # Сохраняем имя игрока
        print(self.player_name)
        self.setWindowTitle(f"Игра — {self.player_name}")
        self.setGeometry(100, 100, self.FIELD_WIDTH, self.FIELD_HEIGHT)
        self.setFixedSize(self.FIELD_WIDTH, self.FIELD_HEIGHT)

        self.restart_opened = False

        # Позиции игроков
        self.player_positions = {"blue": [200, 50], "red": [600, 50]}

        self.player_time = None

        # Координаты платформ
        self.platforms = {"blue": (platform_start, platform_end),"red": (platform_start, platform_end)}

        # Управление текущего игрока
        self.current_color = player_color
        self.velocity_x = 0
        self.velocity_y = 0
        self.player_angles = {"blue": 1,"red": 1}
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
        self.pressed_keys = {"A": False,"D": False}
        self.is_game_over = False  # Флаг завершения игры

         # **Таймер посадки**
        self.landing_timer = QElapsedTimer()
        self.landing_timer.start()

        self.landed = False  # Флаг успешной посадки
        self.crashed = False  # Флаг крушения
    
    def check_landing(self):
        """Проверка, приземлилась ли ракета или разбилась."""
        if self.landed or self.crashed:
            return  # Если уже есть результат, не проверяем дальше

        x, y = self.player_positions[self.current_color]
        angle = self.player_angles[self.current_color]
        platform_start, platform_end = self.platforms[self.current_color]

        # Нижние точки ракеты
        left_foot = (x, y)
        right_foot = (x + 20, y)

        # Проверка успешного приземления (обе ноги на платформе и угол < 5°)
        if (platform_start <= left_foot[0] <= platform_end and
                platform_start <= right_foot[0] <= platform_end and
                self.FIELD_HEIGHT - 20 <= left_foot[1] <= self.FIELD_HEIGHT and
                self.FIELD_HEIGHT - 20 <= right_foot[1] <= self.FIELD_HEIGHT 
                and abs(angle) < 60):

            self.landed = True
            self.is_game_over = True  # Блокируем управление
            self.player_angles[self.current_color] = 0
            landing_time = self.landing_timer.elapsed() / 1000
            self.player_time = landing_time
            print(self.player_angles[self.current_color])
            print("Ракета успешно приземлилась")  # Вывод в терминал
            print(f"Время приземления: {landing_time:.3f} секунд")

            # Отправляем серверу информацию о завершении игры
            send_data(self.client_socket, f"endgame:{self.player_name}:{landing_time:.3f}:{str(self.landed)}")
            print(f"Отправка серверу 1: endgame:{self.player_name}:{landing_time:.3f}:{str(self.landed)}")  # Проверка формата перед отправкой

            # Проверяем завершение игры
            self.check_end()
            
            return  # Завершаем функцию

        # Размеры ракет:
        rocket_width = 20
        rocket_height = 40

        # Координаты центра ракеты
        center_x = x + rocket_width / 2
        center_y = y - rocket_height / 2

        # Углы ракеты до вращения
        corners = [
            (x, y),  # Левый нижний
            (x + rocket_width, y),  # Правый нижний
            (x, y - rocket_height),  # Левый верхний
            (x + rocket_width, y - rocket_height)  # Правый верхний
        ]

        # Угол в радианах
        angle_rad = math.radians(self.player_angles[self.current_color])

        # Вращаем углы вокруг центра
        rotated_corners = []
        for px, py in corners:
            new_x = center_x + (px - center_x) * math.cos(angle_rad) - (py - center_y) * math.sin(angle_rad)
            new_y = center_y + (px - center_x) * math.sin(angle_rad) + (py - center_y) * math.cos(angle_rad)
            rotated_corners.append((new_x, new_y))

        for px, py in rotated_corners:
            # Проверка на столкновение с левой и правой границей
            if px <= 4 or px >= self.FIELD_WIDTH - 4 or (self.FIELD_WIDTH // 2 - 2) <= px <= (self.FIELD_WIDTH // 2 + 2):
                self.crashed = True
                self.landed = False
            # Проверка на столкновение с верхней границей
            elif py <= 4:
                self.crashed = True
                self.landed = False
            # Проверка на столкновение с нижней границей (если не на платформе)
            elif py >= self.FIELD_HEIGHT - 15 and not (self.FIELD_HEIGHT - 10 <= py <= self.FIELD_HEIGHT):
                self.crashed = True
                self.landed = False

            if self.crashed:
                self.is_game_over = True  # Блокируем управление
                self.player_angles[self.current_color] = 180
                crash_time = self.landing_timer.elapsed() / 1000
                print("Ракета разбилась")  # Вывод в терминал
                print(f"Время катастрофы: {crash_time:.3f} секунд")
                self.player_time = crash_time
                # Отправляем серверу информацию о завершении игры
                send_data(self.client_socket, f"endgame:{self.player_name}:{crash_time:.3f}:{str(self.landed)}")
                print(f"Отправка серверу 2: endgame:{self.player_name}:{crash_time:.3f}:{str(self.landed)}")

                # Проверяем завершение игры
                self.check_end()
                return  # Выходим из функции
            
    def check_end(self):
        """Проверка конца игры. Если оба игрока отправили время, игра заканчивается."""
        try:
            # Получаем данные от сервера
            request = receive_data(self.client_socket)
            if request.startswith("endgame:"):
                # Извлекаем информацию: цвет и время другого игрока
                message = request[len("endgame:"):]

                # Разделяем на цвет и время
                other_player_name, other_player_time, other_landed = message.split(":")

                # Сохраняем имя и время другого игрока
                self.other_player_name = other_player_name
                self.other_player_time = other_player_time
                self.other_landed = other_landed

                # Если оба игрока отправили время, игра завершена
                if self.player_time is not None and self.other_player_time is not None:
                    self.end_game()
        except Exception as e:
            print(f"Ошибка при получении сообщения о завершении игры: {e}")
                           
    def end_game(self):
        """Завершаем игру, когда оба игрока отправили свои времена."""
        self.game_over_message = f"Игра завершена! \nВремя {self.player_name}: {self.player_time}, Посадка {self.landed}, Время {self.other_player_name}: {self.other_player_time} Посадка {self.other_landed}"

        # Можно отобразить сообщение на экране (например, через QLabel или QGraphicsTextItem)
        self.display_endgame_message(self.game_over_message)

    def display_endgame_message(self, message):
        """Отображение сообщения о завершении игры на экране."""
        self.endgame_label = QLabel(self)
        self.endgame_label.setText(message)

        # Создаём объект QFont и устанавливаем размер шрифта
        font = QFont()
        font.setPointSize(16)
        
        # Устанавливаем шрифт в QLabel
        self.endgame_label.setFont(font)
        # Устанавливаем белый фон для всей области сообщения
        self.endgame_label.setStyleSheet("background-color: white; color: black;")
        
        # Устанавливаем геометрию QLabel для увеличенной площади показа
        self.endgame_label.setGeometry(0, 0, 800, 800)  # Увеличена ширина и высота
        # Выравнивание текста по центру
        self.endgame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.endgame_label.show()

        QTimer.singleShot(4000, self.close_lobby)
        
    def close_lobby(self):
        """Закрытие текущего окна и открытие нового лобби."""
        if not self.restart_opened:
            self.restart_opened = True
            self.close()  # Закрытие текущего окна
            self.game_window = SpaceLanderClient()  # Создание нового окна лобби
            self.game_window.show()
            send_data(self.client_socket, "theend:")
            return

    def set_player_time(self, time):
        """Устанавливаем время для текущего игрока."""
        self.player_time = round(time, 3)
            
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш."""
        if self.is_game_over:  # Если игра завершена, игнорируем нажатия
            return
        key = event.text().upper()  # Получаем нажатую клавишу в верхнем регистре
        if key == 'A':
            self.pressed_keys["A"] = True  # Помечаем, что клавиша A нажата
        elif key == 'D':
            self.pressed_keys["D"] = True  # Помечаем, что клавиша D нажата

    def keyReleaseEvent(self, event):
        """Обработка отпускания клавиш."""
        if self.is_game_over:  # Если игра завершена, игнорируем нажатия
            return
        key = event.text().upper()  # Получаем отпущенную клавишу в верхнем регистре
        if key == 'A':
            self.pressed_keys["A"] = False  # Помечаем, что клавиша A отпущена
        elif key == 'D':
            self.pressed_keys["D"] = False  # Помечаем, что клавиша D отпущена

    def update_game(self):
        """Обновление позиций игроков и отправка данных серверу."""
        # Рассчитываем угол наклона ракеты в радианах
        angle_rad = math.radians(self.player_angles[self.current_color])

        if self.crashed == False:
            self.velocity_y += self.gravity # Гравитация всегда действует
            #print(self.velocity_y)
        else:
            #print(self.velocity_y)
            self.velocity_y = 10
            self.velocity_y += self.gravity # Гравитация всегда действует
            #print(self.velocity_y)

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
        if self.landed == False or self.crashed == False:    
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
            if self.is_game_over:
                # Если игра завершена, отправляем endgame: с временем приземления
                send_data(self.client_socket, f"endgame:{self.player_name}:{self.player_time:.3f}:{str(self.landed)}")
                #print(f"Отправка серверу 3: endgame:{self.player_name}:{self.player_time:.3f}:{str(self.landed)}")
            else:
                # Если игра не завершена, отправляем обычное движение
                send_data(self.client_socket, f"move:{self.current_color}:{new_x}:{new_y}:{self.player_angles[self.current_color]}")
        except Exception:
            self.close()

        self.check_landing()

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

            if message.startswith("endgame:"):
                # Извлекаем информацию: цвет и время другого игрока
                message = message[len("endgame:"):]

                # Разделяем на цвет и время
                other_player_name, other_player_time, other_landed = message.split(":")
                self.other_player_name = other_player_name
                # Сохраняем время другого игрока
                self.other_player_time = other_player_time
                self.other_landed  = other_landed
                # Если оба игрока отправили время, игра завершена
                if self.player_time is not None and self.other_player_time is not None:
                    self.end_game()
                else:
                    return
        except Exception as e:
            return
        
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

        # Верхняя, нижняя, левая и правая границы
        painter.drawRect(0, 0, self.FIELD_WIDTH, 4)  # Верхняя
        painter.drawRect(0, self.FIELD_HEIGHT - 4, self.FIELD_WIDTH, 4)  # Нижняя
        painter.drawRect(0, 0, 4, self.FIELD_HEIGHT)  # Левая
        painter.drawRect(self.FIELD_WIDTH - 4, 0, 4, self.FIELD_HEIGHT)  # Правая

        # Рисуем платформы с учетом координат для каждого игрока
        for color, (start_x, end_x) in self.platforms.items():
            painter.setBrush(QColor("purple"))  # Цвет платформы
            painter.drawRect(start_x, self.FIELD_HEIGHT - 20, end_x - start_x, 20)

        # Рисуем ракеты для обоих игроков
        for color, (x, y) in self.player_positions.items():
            # Вершины ракеты (левая нижняя, правая нижняя, верхняя)
            points = [
                (x, y),  # Левая точка
                (x + 20, y),  # Правая точка
                (x + 10, y - 40),  # Верхняя точка
            ]

            painter.setPen(QPen(Qt.PenStyle.NoPen))  # Убираем контуры
            painter.setBrush(QBrush(Qt.GlobalColor.transparent))  # Прозрачная кисть (если нужно)

            # **Стабилизаторы**
            left_stabilizer = QPolygonF([
                QPointF(x - 4, y + 4),
                QPointF(x + 4, y + 4),
                QPointF(x, y - 20),
            ])
            right_stabilizer = QPolygonF([
                QPointF(x + 24, y + 4),
                QPointF(x + 16, y + 4),
                QPointF(x + 20, y - 20),
            ])

            # Применение поворота
            angle_rad = math.radians(self.player_angles[color])
            center_x = x + 5  # Центр ракеты
            center_y = y - 10

            # Поворот стабилизаторов
            rotated_left_stabilizer = []
            rotated_right_stabilizer = []

            for stabilizer in [left_stabilizer, right_stabilizer]:
                rotated_stabilizer = []
                for point in stabilizer:
                    # Поворот каждой точки
                    rotated_x = center_x + (point.x() - center_x) * math.cos(angle_rad) - (point.y() - center_y) * math.sin(angle_rad)
                    rotated_y = center_y + (point.x() - center_x) * math.sin(angle_rad) + (point.y() - center_y) * math.cos(angle_rad)
                    rotated_stabilizer.append(QPointF(rotated_x, rotated_y))
                if stabilizer == left_stabilizer:
                    rotated_left_stabilizer = rotated_stabilizer
                else:
                    rotated_right_stabilizer = rotated_stabilizer

            # Рисуем стабилизаторы с применением поворота
            painter.setBrush(QColor(color))  # Используем цвет игрока
            painter.drawPolygon(rotated_left_stabilizer)
            painter.drawPolygon(rotated_right_stabilizer)

            # Поворот основного треугольника ракеты
            rotated_points = []
            for px, py in points:
                # Поворот каждой точки
                rotated_x = center_x + (px - center_x) * math.cos(angle_rad) - (py - center_y) * math.sin(angle_rad)
                rotated_y = center_y + (px - center_x) * math.sin(angle_rad) + (py - center_y) * math.cos(angle_rad)
                rotated_points.append((rotated_x, rotated_y))

            # Рисуем основную часть ракеты (треугольник) с учетом поворота
            polygon = QPolygonF([QPointF(x, y) for x, y in rotated_points])
            painter.setBrush(QColor(color))  # Используем цвет игрока
            painter.drawPolygon(polygon)
        # Отображаем угол текущего игрока и другого игрока
        for color in self.player_positions.keys():
            angle = self.player_angles[color]
            angle_text = f"{angle:.2f}"

            # Выбор цвета текста
            if -20 <= abs(angle) <= 20:
                painter.setPen(QColor("green"))
            else:
                painter.setPen(QColor("black"))

            # Расположение текста справа от ракеты
            if color == "blue":
                # Отображаем угол для текущего игрока
                painter.drawText(self.FIELD_WIDTH - 490, 20, f"NASA:{angle_text}")
            else:
                # Отображаем угол для другого игрока
                painter.drawText(self.FIELD_WIDTH - 140, 20, f"ROSCOSMOS:{angle_text}")


class LobbyWindow(QWidget):
    def __init__(self, client_socket, parent_window):
        super().__init__()

        self.client_socket = client_socket
        self.parent_window = parent_window
        self.player_color = None
        self.player_name = ""
        self.button_pressed = False  # Флаг нажатия кнопки  
        self.setWindowTitle("Лобби — Космический Лэндер")
        self.setGeometry(200, 200, 300, 250)

        layout = QVBoxLayout()

        # Поле для ввода имени
        self.name_label = QLabel("Введите имя:")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)

        self.name_input = QLineEdit()
        self.name_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_input.setPlaceholderText("Ваше имя...")
        layout.addWidget(self.name_input)

        # Кнопка входа в лобби (изначально неактивна)
        self.enter_lobby_button = QPushButton("Войти в лобби")
        self.enter_lobby_button.setDisabled(True)  # Заблокирована до ввода имени
        self.enter_lobby_button.setStyleSheet("background-color: lightgray;")  # Серый цвет
        layout.addWidget(self.enter_lobby_button)

        # Подключение обработчика изменения текста
        self.name_input.textChanged.connect(self.check_name_input)

        # Статус подключения
        self.status_label = QLabel("Ожидание...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

        # Подключаем метод к событию нажатия кнопки
        self.enter_lobby_button.clicked.connect(self.on_lobby_button_click)


        # Таймер для проверки готовности игры
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_game_start)
        self.timer.start(500)

    def check_name_input(self):
        """Разблокирует кнопку, если введено имя."""
        if self.name_input.text().strip() and not self.button_pressed:
            self.enter_lobby_button.setDisabled(False)
            self.enter_lobby_button.setStyleSheet("")  # Убираем серый цвет
            self.enter_lobby_button.setText("Войти в лобби")  # Восстанавливаем текст
        else:
            self.enter_lobby_button.setDisabled(True)
            self.enter_lobby_button.setStyleSheet("background-color: lightgray;")  # Снова делаем серой
            self.enter_lobby_button.setText("Войти в лобби")  # На случай очистки имени
    
    def on_lobby_button_click(self):
        """Обрабатывает нажатие кнопки входа в лобби."""
        if not self.button_pressed:
            self.button_pressed = True
            self.player_name = self.name_input.text()  # Сохраняем имя игрока как атрибут
            print(f"[DEBUG] Игрок {self.player_name} вошел в лобби.")  # Логируем имя
            
            # Меняем состояние кнопки
            self.enter_lobby_button.setDisabled(True)  
            self.enter_lobby_button.setStyleSheet("background-color: lightgray; color: black;")  # Серый цвет
            self.enter_lobby_button.setText("Ожидаем второго игрока...")  
            
            self.enter_lobby_button.repaint()  # Форсируем обновление интерфейса
            self.repaint()  # Перерисовываем окно для надежности


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

            # **Добавляем проверку перед отправкой запроса**
            if not self.button_pressed:
                return  # Выходим из функции, если кнопка не нажата
        
            send_data(self.client_socket, "status")
            print("Отправка запроса статуса лобби: status")  # Логируем отправку
            status = receive_data(self.client_socket)
            print(f"Получен статус лобби: {status}")  # Логируем полученный статус

            if status == "2" and self.button_pressed:
                self.status_label.setText("Начало игры!")
                self.timer.stop()
                self.start_game(self.player_color, self.player_name)
            elif status == "1" and self.button_pressed:
                print(self.button_pressed)


        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка связи с сервером: {e}")
            self.close()

    def start_game(self, color, player_name):
        """Запускает игровое окно."""
        self.close()
        self.game_window = GameWindow(self.client_socket, color, self.platform_start, self.platform_end, player_name)
        self.game_window.show()

class SpaceLanderClient(QWidget):
    def __init__(self):
        super().__init__()

        self.client_socket = None
        self.setWindowTitle("Космический Лэндер — Выбор Лобби")
        self.setGeometry(100, 100, 350, 350)

        layout = QVBoxLayout()

        self.label = QLabel("Выберите лобби для подключения:")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

        for i in range(1, 7):
            button = QPushButton(f"Лобби {i}")
            button.clicked.connect(lambda checked, i=i: self.connect_to_lobby(i))
            layout.addWidget(button)

        # Кнопка "Таблица результатов"
        self.results_button = QPushButton("Таблица результатов")
        self.results_button.clicked.connect(self.show_results)
        layout.addWidget(self.results_button)

        spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        layout.addItem(spacer)

        self.setLayout(layout)

    def show_results(self):
        """Открывает окно с таблицей результатов."""
        self.results_window = ResultsWindow(self)
        self.results_window.show()

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

class ResultsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Таблица результатов")
        self.setGeometry(0, 0, 350, 350)

        self.client_socket = None  # Добавим атрибут для подключения к серверу

        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.load_results()
        layout.addWidget(self.table)

        # Кнопка "Назад"
        self.back_button = QPushButton("Назад")
        self.back_button.clicked.connect(self.close)
        layout.addWidget(self.back_button)

        self.setLayout(layout)

    def load_results(self):
        """Загружает результаты из файла на сервере и отображает только успешные посадки."""
        try:
            # Подключаемся к серверу
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect(('127.0.0.1', 5555))

            # Отправляем запрос на получение результатов
            send_data(self.client_socket, "get_results")
            data = receive_data(self.client_socket)

            # Если файл пуст или произошла ошибка
            if data == "empty":
                QMessageBox.information(self, "Результаты", "Файл результатов пуст.")
                return
            elif data == "not_found":
                QMessageBox.warning(self, "Ошибка", "Файл с результатами не найден.")
                return
            elif data == "error":
                QMessageBox.critical(self, "Ошибка", "Произошла ошибка при получении данных.")
                return

            # Разбираем данные
            data = [line.strip().split(",") for line in data.split("\n") if line.strip().endswith("True")]

            if not data:
                QMessageBox.information(self, "Результаты", "Нет успешных посадок.")
                return

            self.table.setRowCount(len(data))
            self.table.setColumnCount(3)  # 3 столбца: игрок, время, посадка
            self.table.setHorizontalHeaderLabels(["Игрок", "Время (сек)", "Посадка"])

            for row_idx, row in enumerate(data):
                for col_idx, value in enumerate(row):
                    self.table.setItem(row_idx, col_idx, QTableWidgetItem(value))

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных: {e}")

    def closeEvent(self, event):
        """Закрываем соединение при закрытии окна."""
        if self.client_socket:
            self.client_socket.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication([])
    client_window = SpaceLanderClient()
    client_window.show()
    app.exec()