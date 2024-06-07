import re
from urllib.parse import urljoin
import logging

import requests_cache
from bs4 import BeautifulSoup
from tqdm import tqdm

from constants import (
    BASE_DIR, MAIN_DOC_URL, PEP_DOC_URL, EXPECTED_STATUS, DOWNLOADS_FILE
    )
from configs import configure_argument_parser, configure_logging
from exceptions import NoVersionsFoundError
from utils import get_response, find_tag, get_soup
from outputs import control_output


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    soup = get_soup(session, whats_new_url)
    div_with_ul = find_tag(soup, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )

    results = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
    for section in tqdm(sections_by_python):
        version_a_tag = section.find('a')
        version_link = urljoin(whats_new_url, version_a_tag['href'])
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, 'lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append(
            (version_link, h1.text, dl_text)
        )

    return results


def latest_versions(session):
    soup = get_soup(session, MAIN_DOC_URL)
    sidebar = find_tag(soup, 'div', {'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise NoVersionsFoundError('Ничего не нашлось')
    results = [('Ссылка на документацию', 'Версия', 'Статус')]
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (link, version, status)
        )

    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    soup = get_soup(session, downloads_url)
    table_tag = find_tag(soup, 'table', {'class': 'docutils'})
    pdf_a4_tag = find_tag(
        table_tag, 'a', {'href': re.compile(r'.+pdf-a4\.zip$')})
    pdf_a4_link = pdf_a4_tag['href']
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    downloads_dir = BASE_DIR / DOWNLOADS_FILE
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, 'wb') as file:
        response = session.get(archive_url)
        file.write(response.content)
    logging.info(f'Архив был загружен и сохранён: {archive_path}')


def pep(session):
    soup = get_soup(session, PEP_DOC_URL)
    numerical_match = find_tag(
        soup,
        'section',
        {'id': 'numerical-index'}
    )
    table_match = find_tag(
        numerical_match,
        'tbody'
    )
    tr_match = table_match.find_all(
        'tr'
    )
    sum_pep = 0
    sum_pep_status = {}
    result = [('Status', 'Quantity')]
    for _pep in tqdm(tr_match):
        sum_pep += 1

        first_column_tag = find_tag(
            _pep,
            'abbr'
        )
        preview_status = first_column_tag.text[1:]

        href_match = find_tag(
            _pep,
            'a',
            attrs={'class': 'pep reference internal'}
        )['href']
        pep_link = urljoin(PEP_DOC_URL, href_match)
        pep_soup = get_soup(session, pep_link)
        pep_summary = find_tag(
            pep_soup,
            'dl',
            attrs={'class': 'rfc2822 field-list simple'}
        )
        pep_status = pep_summary.find(
            string='Status'
        ).parent.find_next_sibling(
            'dd'
        ).string

        sum_pep_status.setdefault(pep_status, 0)
        sum_pep_status[pep_status] += 1
        if pep_status not in EXPECTED_STATUS[preview_status]:
            message = (
                f'Несовпадающие статусы:'
                f'{pep_link}'
                f'Статус в карточке: {pep_status}'
                f'Ожидаемые статусы: {EXPECTED_STATUS[preview_status]}'
            )
            logging.info(message)
    for status in sum_pep_status:
        result.append((status, sum_pep_status[status]))
    result.append(('Total', sum_pep))
    return result


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
