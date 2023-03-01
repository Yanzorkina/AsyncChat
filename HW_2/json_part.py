import json


def write_order_to_json(item, quantity, price, buyer, date):
    # если файла с заказами нет - надо его сделать автоматически
    try:
        with open('orders.json', 'r', encoding='utf-8') as file_read:
            data = json.load(file_read)
            print(data)
    except FileNotFoundError:
        data = {'orders': []}

    # переданные параметры помещаем в словарь и записываем его в json на место значения к ключу 'orders'
    with open('orders.json', 'w', encoding='utf-8') as file_write:
        orders = data['orders']
        order_details = dict(item=item, quantity=quantity, price=price, buyer=buyer, date=date)
        orders.append(order_details)
        json.dump(data, file_write, indent=4, ensure_ascii=False)


write_order_to_json('багет', '2', '80', 'Вася', '25.02.2023')
write_order_to_json('пицца', '3', '150', 'Петя', '26.02.2023')
write_order_to_json('чебурек', '6', '360', 'Фёдор', '27.02.2023')
