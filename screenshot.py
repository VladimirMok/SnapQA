import ctypes
from ctypes import wintypes
import os
import psutil
import subprocess
import sys
import time
from datetime import datetime

import pyautogui

from PIL import Image, ImageDraw, ImageFont
from pynput import keyboard as pynput_keyboard



# Переменная для хранения времени последнего скриншота и счётчика
last_minute = None
counter = 0

# === НАЧИНАЕМ ИНИЦИАЛИЗАЦИЮ ФЛАГОВ ДОСТУПА К БИБЛИОТЕКАМ ===

# Инициализируем флаги доступности библиотек (глобально)
HAS_KEYBOARD = False
HAS_PYNPUT = False

# Проверяем доступность keyboard (для Windows)
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    pass

# Проверяем доступность pynput (только для Linux)
if sys.platform.startswith('linux'):
    try:
        from pynput import keyboard as pynput_keyboard
        HAS_PYNPUT = True
    except ImportError:
        pass

# === ЗАКАНЧИВАЕМ ИНИЦИАЛИЗАЦИЮ — ТЕПЕРЬ МОЖНО ОПРЕДЕЛЯТЬ ФУНКЦИИ ===

def get_active_window_info():
    """Получает заголовок окна и название процесса. Работает на Windows и Linux."""
    if sys.platform.startswith('win') and HAS_KEYBOARD:
        # Код для Windows (остаётся без изменений)
        try:
            import ctypes
            from ctypes import wintypes
            # ... (код для Windows как в оригинале)
            return window_title, process_name
        except Exception as e:
            print(f"Ошибка Windows API: {e}")
            return "Unknown Window", "Unknown Process"

    elif sys.platform.startswith('linux') and HAS_PYNPUT:
        # Улучшенный код для Linux с несколькими методами получения PID
        window_title = "Unknown Window"
        process_name = "Unknown Process"

        # Метод 1: xdotool (быстрый, но не всегда надёжный)
        try:
            result = subprocess.run(['xdotool', 'getactivewindow', 'getwindowname'],
                                  capture_output=True, text=True, timeout=3)
            window_title = result.stdout.strip() or "Unknown Window"

            pid_result = subprocess.run(['xdotool', 'getwindowpid'],
                                       capture_output=True, text=True, timeout=3)
            pid = pid_result.stdout.strip()

            if pid.isdigit():
                process = psutil.Process(int(pid))
                process_name = process.name().replace('.exe', '')
                return window_title, process_name
        except (FileNotFoundError, subprocess.TimeoutExpired, psutil.NoSuchProcess, psutil.AccessDenied):
            pass  # Переходим к следующему методу

        # Метод 2: wmctrl (более надёжный)
        try:
            result = subprocess.run(['wmctrl', '-l', '-p'],
                                  capture_output=True, text=True, timeout=3)
            for line in result.stdout.splitlines():
                if '*' in line:  # Активное окно
                    parts = line.split()
                    for part in parts:
                        if part.isdigit():
                            pid = int(part)
                            try:
                                process = psutil.Process(pid)
                                process_name = process.exe().split('/')[-1].replace('.exe', '')
                                # Заголовок — всё после PID
                                window_title = ' '.join(parts[parts.index(part) + 1:])
                                return window_title.strip(), process_name
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass  # Переходим к следующему методу

        # Метод 3: xprop (последний резерв)
        try:
            window_id_result = subprocess.run(['xprop', '-root', '_NET_ACTIVE_WINDOW'],
                                            capture_output=True, text=True, timeout=3)
            window_id = window_id_result.stdout.split('#')[-1].strip()
            if window_id:
                window_info = subprocess.run(['xprop', '-id', window_id, 'WM_NAME', 'WM_CLASS'],
                                           capture_output=True, text=True, timeout=3)
                for line in window_info.stdout.splitlines():
                    if 'WM_NAME' in line:
                        parts = [p.strip('"') for p in line.split('"') if p.strip('"')]
                        window_title = parts if parts else "Unknown Window"
                    elif 'WM_CLASS' in line:
                        parts = [p.strip('"') for p in line.split('"') if p.strip('"')]
                        process_name = parts if len(parts) > 1 else parts if parts else "Unknown Process"
                return window_title, process_name
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return window_title, process_name  # Возвращаем fallback

    else:
        return "Unsupported OS", "Unsupported OS"


def setup_folder():
    """Запрашивает у пользователя название папки для скриншотов."""
    print("Добро пожаловать в программу создания скриншотов!")
    print("Нажмите Enter для использования папки по умолчанию (screenshots)")
    folder_name = input("Введите название папки для сохранения скриншотов: ").strip()

    if not folder_name:
        # Если пользователь нажал Enter, сохраняем прямо в screenshots
        full_path = "screenshots"
    else:
        # Если введено название папки, создаём screenshots/название_папки
        full_path = os.path.join("screenshots", folder_name)

    os.makedirs(full_path, exist_ok=True)
    print(f"Скриншоты будут сохраняться в: {full_path}")
    return full_path


def take_screenshot_with_info(save_folder):
    """Делает скриншот и добавляет время + название активного процесса."""
    global last_minute, counter

    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # Обновляем счётчик, если минута изменилась
    current_minute_key = now.strftime('%H%M')
    if current_minute_key != last_minute:
        last_minute = current_minute_key
        counter = 0
    else:
        counter += 1

    # Получаем информацию об активном окне и процессе
    window_title, process_name = get_active_window_info()

    # Делаем скриншот всего экрана
    screenshot = pyautogui.screenshot()

    # Подготавливаем изображение для рисования
    draw = ImageDraw.Draw(screenshot)

    # Находим подходящий шрифт
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        except IOError:
            font = ImageFont.load_default()

    # Параметры текста
    text_color = (255, 255, 255)  # Белый цвет
    background_color = (0, 0, 0, 180)  # Чёрный полупрозрачный фон

    # Текст для отображения
    text = f"Время: {current_time}\nОкно: {window_title}\nПроцесс: {process_name}"

    # Определяем размер текста
    text_bbox = draw.multiline_textbbox((10, 10), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Рисуем полупрозрачный фон под текстом
    draw.rectangle([(5, 5), (text_width + 15, text_height + 15)], fill=background_color)

    # Добавляем текст
    draw.multiline_text((10, 10), text, fill=text_color, font=font)

    # Очищаем названия для использования в имени файла
    safe_window_title = ''.join(c for c in window_title if c.isalnum() or c in (' ', '-', '_')).rstrip()[:15]
    safe_process_name = ''.join(c for c in process_name if c.isalnum() or c in ('-', '_')).rstrip()[:20]

    if not safe_window_title:
        safe_window_title = "Window"
    if not safe_process_name:
        safe_process_name = "Process"


    # Генерируем имя файла в формате ЧЧММ_n_ДДММ_Процесс_Окно.png
    time_part = now.strftime('%H%M')
    date_part = now.strftime('%d%m')
    filename = f"{time_part}_{counter}_{date_part}_{safe_process_name}_{safe_window_title}.png"
    filepath = os.path.join(save_folder, filename)

    # Сохраняем скриншот
    screenshot.save(filepath)
    print(f"Скриншот сохранён: {filepath}")


# Проверяем доступность keyboard (работает в Windows без root)
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    pass  # Если keyboard не установлен, флаг остаётся False

# Проверяем доступность pynput (работает в Linux без root)
if sys.platform.startswith('linux'):
    try:
        from pynput import keyboard as pynput_keyboard
        HAS_PYNPUT = True
    except ImportError:
        pass  # Если pynput не установлен, флаг остаётся False

def main():
    # Настройка папки для сохранения
    save_folder = setup_folder()

    print("\nСкрипт запущен.")
    if sys.platform.startswith('win') and HAS_KEYBOARD:
        # Windows: стандартный вариант с keyboard
        print("Нажмите Ctrl+Alt+Пробел для создания скриншота.")
        print("Для выхода нажмите ESC.")
        keyboard.add_hotkey('ctrl+alt+space', lambda: take_screenshot_with_info(save_folder))
        keyboard.wait('esc')

    elif sys.platform.startswith('linux') and HAS_PYNPUT:
        # Linux: используем pynput (не требует root)
        print("Нажмите Ctrl+Alt+Пробел для создания скриншота.")
        print("Для выхода нажмите ESC.")

        # ИНИЦИАЛИЗИРУЕМ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ДО СОЗДАНИЯ СЛУШАТЕЛЯ
        global ctrl_pressed, alt_pressed
        ctrl_pressed = False
        alt_pressed = False

        # 2. ОПРЕДЕЛЯЕМ ФУНКЦИЮ ОБРАБОТЧИКА
        def on_press(key):
            if key == pynput_keyboard.Key.ctrl_l:
                global ctrl_pressed
                ctrl_pressed = True
            elif key == pynput_keyboard.Key.alt_l:
                global alt_pressed
                alt_pressed = True                
            elif (key == pynput_keyboard.Key.space and ctrl_pressed and alt_pressed):
                take_screenshot_with_info(save_folder)
                # Сбрасываем флаги после срабатывания
                ctrl_pressed = False
                alt_pressed = False
            elif key == pynput_keyboard.Key.esc:
                return False  # Останавливает слушатель

        # 3. СОЗДАЁМ СЛУШАТЕЛЬ (ПОСЛЕ инициализации и определения функции)
        with pynput_keyboard.Listener(on_press=on_press) as listener:
            listener.join()

    else:
        # Универсальный вариант для всех ОС (ввод в консоли)
        print("Нажмите Enter для создания скриншота (или 'q' для выхода):")
        while True:
            user_input = input().strip().lower()
            if user_input == 'q':
                break
            take_screenshot_with_info(save_folder)
            print("Нажмите Enter для нового скриншота или 'q' для выхода:")

    print("Работа скрипта завершена.")

if __name__ == "__main__":
    main()
