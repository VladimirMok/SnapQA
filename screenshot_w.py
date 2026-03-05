import pyautogui
import keyboard
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
import ctypes
from ctypes import wintypes
import psutil

# Константы для Windows API
user32 = ctypes.WinDLL('user32')
kernel32 = ctypes.WinDLL('kernel32')

user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]

# Переменная для хранения времени последнего скриншота и счётчика
last_minute = None
counter = 0

def get_active_window_info():
    """Получает заголовок окна и название процесса (только для Windows)."""
    try:
        # Получаем дескриптор активного окна
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "No Active Window", "No Process"

        # Получаем заголовок окна
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            window_title = "Window with no title"
        else:
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            window_title = buffer.value
            if not window_title:
                window_title = "Untitled Window"

        # Получаем PID и имя процесса
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            process = psutil.Process(pid.value)
            process_name = process.name()
            # Убираем расширение .exe
            if process_name.lower().endswith('.exe'):
                process_name = process_name[:-4]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_name = "Unknown Process"

        return window_title, process_name

    except Exception as e:
        print(f"Ошибка Windows API: {e}")
        return "Unknown Window", "Unknown Process"

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

    # Находим подходящий шрифт (только Windows)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
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

def main():
    # Настройка папки для сохранения
    save_folder = setup_folder()

    print("\nСкрипт запущен. Нажмите Ctrl+Alt+Пробел для создания скриншота.")
    print("Для выхода нажмите ESC.")

    # Назначаем обработчик для Ctrl+Alt+Пробел
    keyboard.add_hotkey('ctrl+alt+space', lambda: take_screenshot_with_info(save_folder))

    # Ждём нажатия ESC для выхода
    keyboard.wait('esc')
    print("Работа скрипта завершена.")

if __name__ == "__main__":
    main()
