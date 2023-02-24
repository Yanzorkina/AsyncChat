import subprocess
import locale

import chardet
from chardet.universaldetector import UniversalDetector

# 1
print("Задача 1. Вывод:")
words_in_str = ['разработка', 'сокет', 'декоратор']
words_in_unicode = [
    '\u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0430',
    '\u0441\u043e\u043a\u0435\u0442',
    '\u0434\u0435\u043a\u043e\u0440\u0430\u0442\u043e\u0440'
]


def check_symbols(words_list: list):
    for word in words_list:
        print(f"{word}, тип: {type(word)}, длина: {len(word)}")


check_symbols(words_in_str)
check_symbols(words_in_unicode)

# 2
print("\nЗадача 2. Вывод:")
words_in_str = ['class', 'function', 'method']
current_word = ''

for word in words_in_str:
    current_word = bytes(word, 'ascii')
    print(f"{current_word}, тип: {type(current_word)}, длина: {len(current_word)}")

# 3
print("\nЗадача 3. Вывод:")

words_in_str = ['attribute', 'класс', 'функция', 'type']
current_word = ''
unable_to_encode = []

for word in words_in_str:
    try:
        current_word = bytes(word, 'ascii')
    except UnicodeEncodeError:
        unable_to_encode.append(word)

print(f'Невозможно записать в байтовом типе с кодировкой ascii: {", ".join(unable_to_encode)}')

# 4
print("\nЗадача 4. Вывод:")

words_in_str = ['разработка', 'администрирование', 'protocol', 'standard']
words_in_bytes = []

print("Закодировано:")
for word in words_in_str:
    words_in_bytes.append(word.encode('utf-8'))
print(*words_in_bytes, sep='\n')

words_in_str = []
print()
print("Декодировано:")
for word in words_in_bytes:
    words_in_str.append(word.decode('utf-8'))
print(*words_in_str, sep='\n')

# 5
print("\nЗадача 5. Вывод:")


def get_ping_log(site: str, limit: int):
    args = ['ping', site]
    subproc_ping = subprocess.Popen(args, stdout=subprocess.PIPE)
    flag = 0
    for line in subproc_ping.stdout:
        detection = chardet.detect(line)
        print(detection)
        print(line.decode(detection['encoding']).encode('utf-8').decode('utf-8'))
        flag += 1
        if flag >= limit:
            print()
            break


get_ping_log('yandex.ru', 5)
get_ping_log('google.com', 5)

# 6
print("\nЗадача 6. Вывод:")

with open('test_file.txt', 'w') as test_file:
    test_file.write("сетевое программирование\nсокет\nдекоратор")

detector = UniversalDetector()

with open('test_file.txt', 'rb') as test_file:
    for i in test_file:
        detector.feed(i)
        if detector.done:
            break
    detector.close()
print(detector.result['encoding'])

with open('test_file.txt', encoding=detector.result['encoding']) as test_file:
    for line in test_file:
        print(line, end="")
