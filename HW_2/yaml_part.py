import yaml

food_dict_py = {'food_list': ['багет', 'слойка', 'брауни'],
                'amount': 3,
                'food price': dict(багет='55₽', слойка='68₽', брауни='89₽')
                }

with open('file.yaml', 'w', encoding='utf-8') as file_in:
    yaml.dump(food_dict_py, file_in, default_flow_style=False, allow_unicode=True, sort_keys=False
              )

with open("file.yaml", 'r', encoding='utf-8') as file_out:
    food_dict_yaml = yaml.load(file_out, Loader=yaml.SafeLoader)

print("Данные сопадают" if food_dict_py == food_dict_yaml else "Данные не совпадают")
