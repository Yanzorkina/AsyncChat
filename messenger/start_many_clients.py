import subprocess


def start_many():
    clients = []
    clients.append(subprocess.Popen('python server.py', creationflags=subprocess.CREATE_NEW_CONSOLE))
    clients_number = int(input(
        'Будет запущен один сервер и указанное количество клиентов.\n'
        'Имена клиентов будут иметь префикс "client" и его номер.\n'
        'Сколько клиентов запустить?\n'))

    for client in range(clients_number):
        clients.append(subprocess.Popen(f'python client.py -n client{clients_number + 1}',
                                        creationflags=subprocess.CREATE_NEW_CONSOLE))
    action = input('Чтобы закрыть все процессы, введите "kill"\n')
    if action == 'kill':
        for client in range(clients_number + 1):
            clients.pop().kill()


if __name__ == '__main__':
    start_many()
