import re
from bs4 import BeautifulSoup
from .params import base_url

def get_links(session):
    r = session.get(base_url + '/school/reports/')
    html = BeautifulSoup(r.text, 'html.parser')

    report_links = html.find('div', {'class': 'report_links'}).find_all_next('a', href=True)

    report_links = [report_links[2], report_links[3], report_links[6], report_links[7], report_links[10]]

    report_links = {tag.text: tag['href'] for tag in report_links}

    url = list(report_links.values())[0]

    for key, val in report_links.items():
        val = val.split('?')[0] + '?'
        report_links[key] = val

    year_ids = get_years_ids(url, session)

    year_ids = {
        'past': year_ids[0],
        'this': year_ids[1],
    }

    return report_links, year_ids

def get_years_ids(url, session):

    r = session.get(base_url + url)
    html = BeautifulSoup(r.text, 'html.parser')

    div = html.find('div', {'class': 'no-print'}).find_all_next('div', {'style': 'float: left; margin-left: 20px'})[-3]

    link = div.find_next('a', href=True)['href']

    past_year_id = re.findall(r'\d+', link)[0]
    this_year_id = re.findall(r'\d+', url)[0]

    return past_year_id, this_year_id

def get_years(session):
    """
    Fetches this schoolyear eg 2019/2020
    :return: list: int [year1, year2]
    """
    r = session.get('https://edu.tatar.ru/school')
    html = BeautifulSoup(r.text, 'html.parser')

    h3 = html.find('h3')
    years = list(map(int, re.findall(r'\d+', h3.text)))

    return years