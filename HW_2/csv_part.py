import re
import csv
import locale

from chardet.universaldetector import UniversalDetector


def get_data():
    # создаем списки для парсинга
    files_list = ['info_1.txt', 'info_2.txt', 'info_3.txt']
    os_prod_list = []
    os_name_list = []
    os_code_list = []
    os_type_list = []
    main_data = []

    # определение кодировки файлов, подразумеваем, что все файлы исполнены в одной
    detector = UniversalDetector()

    with open(files_list[0], 'rb') as test_file:
        for i in test_file:
            detector.feed(i)
            if detector.done:
                break
        detector.close()

    # последовательно обрабатываем спецификации и берем оттуда нужные параметры
    for file in files_list:
        file_object = open(file, encoding=detector.result['encoding'])
        data = file_object.read()

        # шаблон однотипный - от наименования параметра до переноса строки с отбрасыванием пробелов в начале
        os_prod_list.append(re.compile(r'Изготовитель системы:.*').findall(data)[0].split(":")[1].lstrip())
        os_name_list.append(re.compile(r'Название ОС:.*').findall(data)[0].split(":")[1].lstrip())
        os_code_list.append(re.compile(r'Код продукта:.*').findall(data)[0].split(":")[1].lstrip())
        os_type_list.append(re.compile(r'Тип системы:.*').findall(data)[0].split(":")[1].lstrip())

    # создаем "шапку"
    headers = ['№п/п', 'Изготовитель системы', 'Название ОС', 'Код продукта', 'Тип системы']
    main_data.append(headers)

    # формируем строки для таблицы и построчно вносим в итоговый список
    number = 1
    for item in range(len(files_list)):
        row_data = [number, os_prod_list[item], os_name_list[item], os_code_list[item], os_type_list[item]]
        main_data.append(row_data)
        number += 1
    return main_data


def write_to_csv(result_file, encod=locale.getpreferredencoding()):
    # пишем полученный итоговый список в csv-файл построчно
    # даем пользователю возможность явно указать кодировку, иначе - стндартная кодировка системы
    main_data = get_data()
    with open(result_file, 'w', encoding=encod) as file:
        writer = csv.writer(file, quoting=csv.QUOTE_NONNUMERIC)
        for row in main_data:
            writer.writerow(row)

write_to_csv('data_report.csv')
