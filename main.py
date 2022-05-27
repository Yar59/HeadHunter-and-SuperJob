import logging

import requests
from itertools import count

from dotenv import dotenv_values
from terminaltables import AsciiTable


def get_vacancies_hh(language):
    url = "https://api.hh.ru/vacancies"
    vacancies_pages = []

    for page in count(0):
        payload = {
            "text": f"Программист {language}",
            "area": 1,
            "page": page,
            "per_page": 100
        }
        response = requests.get(url, params=payload)
        response.raise_for_status()
        vacancies_page = response.json()
        if not vacancies_page["found"]:
            logging.warning(f"Данные по языку {language} от сервиса HH не найдены")
            break
        vacancies_pages.append(vacancies_page)
        if page >= vacancies_page['pages'] - 1:
            break

    logging.info(f"Завершено получение данных по языку {language} от сервиса HH")
    return vacancies_pages


def get_vacancies_sj(language, key):
    url = "https://api.superjob.ru/2.0/vacancies/"
    headers = {
        "X-Api-App-Id": key,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    vacancies_pages = []
    for page in count(0):
        payload = {
            "keyword": f'Программист {language}',
            "town": 4,
            "page": page,
            "count": 100
        }
        response = requests.get(url, headers=headers, params=payload)
        response.raise_for_status()
        vacancies_page = response.json()
        if not vacancies_page["total"]:
            logging.warning(f"Данные по языку {language} от сервиса SJ не найдены")
            break
        vacancies_pages.append(vacancies_page)
        if not vacancies_page['more']:
            break

    logging.info(f"Завершено получение данных по языку {language} от сервиса SJ")
    return vacancies_pages


def calculate_rub_salary_hh(vacancy):
    if vacancy["salary"]:
        currency = vacancy["salary"]["currency"]
        salary_from = vacancy["salary"]["from"]
        salary_to = vacancy["salary"]["to"]
        if currency == "RUR":
            return calculate_salary(salary_from, salary_to)


def calculate_rub_salary_sj(vacancy):
    salary_from = vacancy["payment_from"]
    salary_to = vacancy["payment_to"]
    currency = vacancy["currency"]
    if currency == "rub":
        return calculate_salary(salary_from, salary_to)


def calculate_salary(salary_from, salary_to):
    if salary_from:
        if salary_to:
            return (salary_from + salary_to) / 2
        else:
            return salary_from * 1.2
    elif salary_to:
        return salary_to * 0.8
    return None


def make_clever_print(statistics, title):
    table_data = [
        (
            "Язык программирования",
            "Вакансий найдено",
            "Вакансий обработано",
            "Средняя зарплата"
        )
    ]
    for language in statistics:
        info = statistics[language]
        table_data.append(
            (
                language,
                info["vacancies_found"],
                info["vacancies_processed"],
                info["average"]
            )
        )

    table_instance = AsciiTable(table_data, title)
    table_instance.justify_columns[2] = 'right'
    return table_instance.table


def process_vacancies_hh(vacancies_pages):
    language_params = {
        "average": 0,
        "vacancies_processed": 0,
        "vacancies_found": 0,
    }
    for vacancies_page in vacancies_pages:
        vacancies = vacancies_page["items"]
        total_vacancies = vacancies_page["found"]
        for vacancy in vacancies:
            salary = calculate_rub_salary_hh(vacancy)
            if salary:
                language_params["average"] += salary
                language_params["vacancies_processed"] += 1
        language_params["vacancies_found"] = total_vacancies
    language_params["average"] = int(language_params["average"] / language_params["vacancies_processed"])
    return language_params


def process_vacancies_sj(vacancies_pages):
    language_params = {
        "average": 0,
        "vacancies_processed": 0,
        "vacancies_found": 0,
    }
    for vacancies_page in vacancies_pages:
        vacancies = vacancies_page["objects"]
        total_vacancies = vacancies_page["total"]
        for vacancy in vacancies:
            salary = calculate_rub_salary_sj(vacancy)
            if salary:
                language_params["average"] += salary
                language_params["vacancies_processed"] += 1
                language_params["vacancies_found"] += total_vacancies
    language_params["average"] = int(language_params["average"] / language_params["vacancies_processed"])
    return language_params


if __name__ == "__main__":
    top_languages = [
        "JavaScript",
        "Java",
        "Python",
        "Ruby",
        "PHP",
    ]
    sj_key = dotenv_values(".env")["SJ_SECRET_KEY"]
    try:
        top_languages_info_hh = {}
        top_languages_info_sj = {}
        for language in top_languages:
            vacancies_pages_hh = get_vacancies_hh(language)
            if vacancies_pages_hh:
                top_languages_info_hh[language] = process_vacancies_hh(vacancies_pages_hh)
            vacancies_pages_sj = get_vacancies_sj(language, sj_key)
            if vacancies_pages_sj:
                top_languages_info_sj[language] = process_vacancies_sj(vacancies_pages_sj)

        print(
            make_clever_print(
                top_languages_info_hh,
                "Вакансии HeadHunter в Москве"
            ),
            end="\n\n"
        )
        print(make_clever_print(
            top_languages_info_sj,
            "Вакансии SuperJob в Москве"
        ))
    except requests.exceptions.HTTPError as error:
        exit("Can't get data from server:\n{0}".format(error))
