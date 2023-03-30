import subprocess
from ipaddress import ip_address
import platform
from tabulate import tabulate


def host_ping(addresses_list, pack_num="1", timeout="1"):
    """
    Показывает доступность введенных адресов.

    :param addresses_list:
    :param pack_num:
    :param timeout:
    :return:
    """
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    for address in addresses_list:
        current_ip = ip_address(address)
        command = ['ping', param, pack_num, '-w', timeout, str(current_ip)]
        if (subprocess.call(command, stdout=subprocess.PIPE)) == 0:
            print(f'{address} Узел доступен ')
        else:
            print(f'{address} Узел недоступен ')


def host_range_ping(address_to_check, octet_range, pack_num="1", timeout="1"):
    """
    Показывает доступность адресов, от введенного до конца указанного диапазона, с учтом изменения
    последнего октета на 1.

    :param address_to_check:
    :param octet_range:
    :param pack_num:
    :param timeout:
    :return:
    """
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    address_to_check = ip_address(address_to_check)
    for address in range(octet_range):
        command = ['ping', param, pack_num, '-w', timeout, str(address_to_check)]
        if (subprocess.call(command, stdout=subprocess.PIPE)) == 0:
            print(f'{address_to_check} Узел доступен ')
        else:
            print(f'{address_to_check} Узел недоступен ')
        address_to_check += 1


def host_range_ping_tab(address_to_check, octet_range, pack_num="1", timeout="1"):
    """
    Показывает доступность адресов, от введенного до конца указанного диапазона, с учтом изменения
    последнего октета на 1. Выводит таблицу.

    :param address_to_check:
    :param octet_range:
    :param pack_num:
    :param timeout:
    :return:
    """
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    address_to_check = ip_address(address_to_check)
    result_list = []
    for address in range(octet_range):
        command = ['ping', param, pack_num, '-w', timeout, str(address_to_check)]
        if (subprocess.call(command, stdout=subprocess.PIPE)) == 0:
            result_list.append({'Узел доступен': str(address_to_check)})
        else:
            result_list.append({'Узел недоступен': str(address_to_check)})
        address_to_check += 1
    print(tabulate(result_list, headers='keys'))


if __name__ == '__main__':
    print('Вывод задачи 1')
    ip_addresses = ['5.255.255.70', '1.2.3.4', '91.109.200.200', '192.168.0.101']
    host_ping(ip_addresses)
    print('\n\nВывод задачи 2')
    host_range_ping("5.255.255.70", 5)
    print('\n\nВывод задачи 3')
    host_range_ping_tab("5.255.255.70", 5)
