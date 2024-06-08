import csv
import datetime as dt
from prettytable import PrettyTable
import logging

from constants import (
    BASE_DIR, DATETIME_FORMAT, MODE_PRETTY, MODE_FILE, RESULTS_FILE
    )


# Контроль вывода результатов парсинга.
def control_output(results, cli_args):
    output = cli_args.output
    if output == MODE_PRETTY:
        pretty_output(results)
    elif output == MODE_FILE:
        file_output(results, cli_args)
    else:
        default_output(results)


# Вывод данных в терминал построчно.
def default_output(results):
    for row in results:
        print(*row)


# Вывод данных в формате PrettyTable.
def pretty_output(results):
    table = PrettyTable()
    table.field_names = results[0]
    table.align = 'l'
    table.add_rows(results[1:])
    print(table)


# Создание директории с результатами парсинга.
def file_output(results, cli_args):
    results_dir = BASE_DIR / RESULTS_FILE
    results_dir.mkdir(exist_ok=True)
    parser_mode = cli_args.mode
    now = dt.datetime.now()
    now_formatted = now.strftime(DATETIME_FORMAT)
    file_name = f'{parser_mode}_{now_formatted}.csv'
    file_path = results_dir / file_name
    with open(file_path, 'w', encoding='utf-8') as f:
        writer = csv.writer(f, dialect='unix', quoting=csv.QUOTE_MINIMAL)
        writer.writerows(results)
    logging.info(f'Файл с результатами был сохранён: {file_path}')
