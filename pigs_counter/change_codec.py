import os
import time
from datetime import datetime
import urllib
import subprocess
from db_utils import set_event_video_url

env = os.environ.copy()
env["CUDA_VISIBLE_DEVICES"] = "1"


def get_file_size(filepath):
    """Возвращает размер файла в байтах."""
    return os.path.getsize(filepath) if os.path.exists(filepath) else 0


def change_codec(filepath):
    """Перекодирует видео с помощью ffmpeg и удаляет оригинал."""
    filename = os.path.basename(
        filepath).lstrip('.')  # remove dot from filename
    # For video
    new_filename = os.path.join(
        os.path.dirname(filepath), filename)
    # For url
    start_time_datetime = os.path.splitext(filename)[0].split('-', 1)[0]
    start_time_datetime = datetime.strptime(
        start_time_datetime, '%d.%m.%Y %H.%M.%S')
    start_time = start_time_datetime.strftime('%Y-%m-%d %H:%M:%S')
    start_time_dmy = start_time_datetime.strftime(r'%d.%m.%Y')
    filename_url = urllib.parse.quote(filename)
    video_url = f"http://192.168.1.116/files/data/{start_time_dmy}/{filename_url}"
    try:
        # command = ["ffmpeg", "-i", filepath, new_filename]
        command = ['ffmpeg', '-hwaccel', 'cuda', '-i', filepath, '-c:v', 'h264_nvenc',
                   '-b:v', '2M', "-fps_mode", "passthrough",  new_filename]
        subprocess.run(command, env=env, check=True)
        os.remove(filepath)  # Удаляем старый файл после успешной конвертации
        print(
            f"Файл {filepath} успешно конвертирован и сохранен как {new_filename}")
        set_event_video_url(start_time, video_url)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при обработке {filepath}: {e}")


def check_dotfiles(directory):
    """Мониторит вложенные директории (1 уровня) на наличие файлов с точкой в начале и проверяет их размер."""

    # Получаем список вложенных папок (1 уровень)
    for subdir in next(os.walk(directory))[1]:
        subdir_path = os.path.join(directory, subdir)
        for filename in os.listdir(subdir_path):
            # Проверяем скрытые видеофайлы
            if filename.startswith(".") and filename.endswith(".mp4"):
                filepath = os.path.join(subdir_path, filename)
                size1 = get_file_size(filepath)
                time.sleep(10)  # Ждем 10 секунд
                size2 = get_file_size(filepath)

                if size1 == size2 and size1 > 0:  # Если размер не изменился
                    change_codec(filepath)


if __name__ == "__main__":
    # Укажите путь к нужной директории, если не текущая
    directory_to_watch = "/data/videos"
    check_dotfiles(directory_to_watch)
