import time
import os
import shutil
from dotenv import load_dotenv

load_dotenv()
LIFETIME = int(os.getenv('LIFETIME'))
LIFETIME_TEMP = LIFETIME  # int(os.getenv('LIFETIME_TEMP'))


def remove_old_directories(parent_dir: str):
    """
    Delete directories with videos older then LIFETIME

    :parent_dir: str - path to directory with videos
    """
    # Получаем текущее время
    current_time = time.time()

    # Проходим по всем папкам в родительской директории
    for folder_name in os.listdir(parent_dir):
        folder_path = os.path.join(parent_dir, folder_name)

        # Проверяем, является ли это папкой
        if os.path.isdir(folder_path):
            # Получаем время создания папки
            creation_time = os.path.getctime(folder_path)
            # Проверяем, превышает ли возраст папки заданный порог
            if (current_time - creation_time) > LIFETIME * 24 * 3600:
                # Удаляем папку
                if os.path.exists(folder_path):
                    shutil.rmtree(folder_path)
                    print(f'Удалена папка: {folder_path}')
                else:
                    print(f'Папка {folder_path} не найдена')


def remove_old_temp_files(parent_dir: str):
    """
    Delete temp files older then LIFETIME_TEMP

    :parent_dir: str - path to directory with temp files
    """
    # Получаем текущее время
    current_time = time.time()

    # Проходим по всем файлам в родительской директории
    for file_name in os.listdir(parent_dir):
        if file_name == '.gitkeep':
            continue
        filename = os.path.join(parent_dir, file_name)

        # Проверяем, является ли это файл
        if os.path.isfile(filename):
            # Получаем время создания файла
            creation_time = os.path.getctime(filename)

            # Проверяем, превышает ли возраст файла заданный порог
            if (current_time - creation_time) > LIFETIME_TEMP * 3600:
                # Удаляем файл
                os.remove(filename)
                print(f'Удален файл: {filename}')
        else:
            print(f'Файл {filename} не найден')


if __name__ == '__main__':
    remove_old_directories('/videos')
