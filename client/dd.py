import random
import math
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QMessageBox, QLineEdit, QTableWidget, QTableWidgetItem, QSpacerItem, QSizePolicy
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPolygonF, QFont, QLinearGradient
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QBrush
from PyQt6.QtGui import QPen
from PyQt6.QtCore import QElapsedTimer

class SoloGameWindow(QWidget):
    FIELD_WIDTH = 400
    FIELD_HEIGHT = 800

    def __init__(self, client_socket, player_color, platform_start, platform_end, player_name):
        super().__init__()

        self.client_socket = client_socket
        self.player_name = player_name  # Сохраняем имя игрока
        print(self.player_name)
        self.setWindowTitle(f"Игра — {self.player_name}")
        self.setGeometry(100, 100, self.FIELD_WIDTH, self.FIELD_HEIGHT)
        self.setFixedSize(self.FIELD_WIDTH, self.FIELD_HEIGHT)

        platform_start = random.randint(4, 350)
        platform_end = platform_start + 60

        self.restart_opened = False

        # Позиции игроков
        self.player_positions = {"blue": [200, 50]}

        self.player_time = None

        # Координаты платформ
        self.platforms = {"blue": (platform_start, platform_end)}

        # Управление текущего игрока
        self.current_color = player_color
        self.velocity_x = 0

        self.player_angles = {"blue": 1}
        self.player_fuel = {"blue": 110}
        self.player_velocity_y = {"blue": 0}
        # Гравитация ТУТ
        self.gravity = 0.025

        # Таймер обновления игры
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_game)
        self.timer.start(30)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Словарь для отслеживания нажатых клавиш
        self.pressed_keys = {"A": False,"D": False}
        self.is_game_over = False  # Флаг завершения игры

        self.landing_timer = QElapsedTimer()

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

        # Проверка успешного приземления (обе ноги на платформе и угол < 25°)
        if (platform_start <= left_foot[0] <= platform_end and
                platform_start <= right_foot[0] <= platform_end and
                self.FIELD_HEIGHT - 20 <= left_foot[1] <= self.FIELD_HEIGHT and
                self.FIELD_HEIGHT - 20 <= right_foot[1] <= self.FIELD_HEIGHT 
                and abs(angle) <= 25 and self.player_velocity_y[self.current_color] <= 3):

            self.landed = True
            self.is_game_over = True  # Блокируем управление
            self.player_angles[self.current_color] = 0
            landing_time = self.landing_timer.elapsed() / 1000
            self.player_time = landing_time
            print(self.player_angles[self.current_color])
            print("Ракета успешно приземлилась")  # Вывод в терминал
            print(f"Время приземления: {landing_time:.3f} секунд")


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

                # Проверяем завершение игры
                self.check_end()
                return  # Выходим из функции
            
    def check_end(self):
        """Проверка конца игры. Если оба игрока отправили время, игра заканчивается."""
        # Если оба игрока отправили время, игра завершена
        if self.player_time is not None:
            self.end_game()
                    
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
            return

    def set_player_time(self, time):
        """Устанавливаем время для текущего игрока."""
        self.player_time = round(time, 3)
            
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш."""
        if self.is_game_over or self.player_fuel[self.current_color] <= 0:  # Если игра окончена или нет топлива, блокируем управление
            return
        key = event.text().upper()  # Получаем нажатую клавишу в верхнем регистре
        if key == 'A':
            self.pressed_keys["A"] = True  # Помечаем, что клавиша A нажата
        elif key == 'D':
            self.pressed_keys["D"] = True  # Помечаем, что клавиша D нажата

    def keyReleaseEvent(self, event):
        """Обработка отпускания клавиш."""
        if self.is_game_over or self.player_fuel[self.current_color] <= 0:  # Если игра окончена или нет топлива, блокируем управление
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

        if self.player_velocity_y[self.current_color] > 0.01 and not self.landing_timer.isValid():
            self.landing_timer.start()  

        if self.crashed == False:
            self.player_velocity_y[self.current_color] += self.gravity # Гравитация всегда действует
            #print(self.velocity_y)
        else:
            #print(self.velocity_y)
            self.player_velocity_y[self.current_color] = 10
            self.gravity = 0
            #print(self.velocity_y)
        
        if self.pressed_keys["A"] or self.pressed_keys["D"]:
            if self.player_fuel[self.current_color] > 0:
                self.player_fuel[self.current_color] -= 0.5  # Уменьшаем топливо при использовании двигателя

        if self.player_fuel[self.current_color] <= 0:
            self.pressed_keys["A"] = False
            self.pressed_keys["D"] = False  # Блокируем движение, если топливо закончилось

        # Если никаких кнопок не нажато, ракета падает под действием гравитации
        if not self.pressed_keys["A"] and not self.pressed_keys["D"]:
            self.velocity_x = 0  # Нет горизонтального движения
            self.player_velocity_y[self.current_color] += self.gravity  # Ракета падает под действием гравитации

        # Двигатели ракеты не дают гравитации полностью направлять её вниз
        if self.pressed_keys["A"] and self.pressed_keys["D"]:
            # Когда обе клавиши нажаты, ракета будет двигаться вверх по направлению носа
            self.velocity_x = math.sin(angle_rad) * 2  # Горизонтальное движение по направлению носа
            self.player_velocity_y[self.current_color] = math.cos(angle_rad) * -1.5  # Вертикальное движение вверх, против гравитации

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
                    self.player_angles[self.current_color] -= 0.5  # Поворот по часовой стрелке
                elif self.player_angles[self.current_color] > 0:
                    self.player_angles[self.current_color] += 0.5  # Поворот против часовой стрелки
            elif abs(self.player_angles[self.current_color]) >= 90 and abs(self.player_angles[self.current_color]) < 180:
                if self.player_angles[self.current_color] < 0:
                    self.player_angles[self.current_color] -= 0.5  # Поворот против часовой стрелки
                elif self.player_angles[self.current_color] > 0:
                    self.player_angles[self.current_color] += 0.5  # Поворот по часовой стрелке
            else:
                self.player_angles[self.current_color] = 180

        # Вычисляем новые координаты ракеты
        new_x = self.player_positions[self.current_color][0] + self.velocity_x
        new_y = self.player_positions[self.current_color][1] + self.player_velocity_y[self.current_color]

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

        self.check_landing()

        self.update()      

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

        painter.drawText(self.FIELD_WIDTH - 490, 20, f"NASA:")
        painter.drawText(self.FIELD_WIDTH - 140, 20, f"ROSCOSMOS:")

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

            # Координаты пламени относительно ракеты (без поворота)
            flame_left = [
                (x - 2, y + 7),  # Верхняя левая
                (x + 2, y + 7),  # Верхняя правая
                (x + 2, y + 25),  # Нижняя правая
                (x - 2, y + 25)   # Нижняя левая
            ]

            flame_right = [
                (x + 18, y + 7),  # Верхняя левая
                (x + 22, y + 7),  # Верхняя правая
                (x + 22, y + 25),  # Нижняя правая
                (x + 18, y + 25)   # Нижняя левая
            ]

            # Поворот пламени
            rotated_flame_left = []
            rotated_flame_right = []

            for flame in [flame_left, flame_right]:
                rotated_flame = []
                for px, py in flame:
                    rotated_x = center_x + (px - center_x) * math.cos(angle_rad) - (py - center_y) * math.sin(angle_rad)
                    rotated_y = center_y + (px - center_x) * math.sin(angle_rad) + (py - center_y) * math.cos(angle_rad)
                    rotated_flame.append(QPointF(rotated_x, rotated_y))
                if flame == flame_left:
                    rotated_flame_left = rotated_flame
                else:
                    rotated_flame_right = rotated_flame

            # Отрисовка пламени, если кнопки нажаты
            painter.setBrush(QBrush(QColor(255, 140, 0)))  # Огненно-оранжевый цвет
            if self.pressed_keys["A"]:
                painter.drawPolygon(QPolygonF(rotated_flame_right))
            if self.pressed_keys["D"]:
                painter.drawPolygon(QPolygonF(rotated_flame_left))

            # **Закрепленный текст над ракетой (но не поворачивается)**
            text_x = int(x + 35)  # Смещение текста вправо от ракеты
            text_y = int(y - 60)  # Смещение текста выше ракеты

            # Получаем значения угла, топлива и скорости
            angle_text = f"{self.player_angles[color]:.2f}"
            fuel_text = self.player_fuel[color]
            speed_text = f"{abs(self.player_velocity_y[color] + 7):.2f}"

            # Угол: зелёный, если от -20 до 20
            painter.setPen(QColor("green") if -25 <= self.player_angles[color] <= 25 else QColor("red"))
            painter.drawText(text_x, text_y, f"{angle_text}°")

            # Топливо: красное, если меньше 20
            painter.setPen(QColor("red") if fuel_text < 20 else QColor("black"))
            painter.drawText(text_x, text_y + 40, f"{fuel_text} м³")

            # Скорость: зеленая, если меньше 3
            painter.setPen(QColor("green") if abs(self.player_velocity_y[color]) <= 3 else QColor("red"))
            painter.drawText(text_x, text_y + 20, f"{speed_text} km/h")
