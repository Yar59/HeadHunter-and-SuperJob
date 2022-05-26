import requests
from itertools import count

from dotenv import dotenv_values
from terminaltables import AsciiTable


def get_vacancies_hh(languages):
    url = "https://api.hh.ru/vacancies"

    for language in languages:
        languages[language]["average"] = 0
        languages[language]["vacancies_processed"] = 0
        for page in count(0):
            payload = {
                "text": f"Программист {language}",
                "area": 1,
                "page": page,
                "per_page": 100
            }
            response = requests.get(url, params=payload)
            response.raise_for_status()
            vacancies = response.json()["items"]
            total_vacancies = response.json()["found"]
            for vacancy in vacancies:
                salary = calculate_rub_salary_hh(vacancy)
                if salary:
                    languages[language]["average"] += salary
                    languages[language]["vacancies_processed"] += 1
            languages[language]["vacancies_found"] = total_vacancies
            if page >= response.json()['pages'] - 1:
                break
        languages[language]["average"] = int(languages[language]["average"] / languages[language]["vacancies_processed"])
        print(f"Получены данные по языку {language}")
    return languages


def calculate_rub_salary_hh(vacancy):
    if vacancy["salary"]:
        currency = vacancy["salary"]["currency"]
        salary_from = vacancy["salary"]["from"]
        salary_to = vacancy["salary"]["to"]
        if currency == "RUR":
            return calculate_salary(salary_from, salary_to)
    return None


def calculate_rub_salary_sj(vacancy):
    salary_from = vacancy["payment_from"]
    salary_to = vacancy["payment_to"]
    currency = vacancy["currency"]
    if currency == "rub":
        return calculate_salary(salary_from, salary_to)
    return None


def calculate_salary(salary_from, salary_to):
    if salary_from:
        if salary_to:
            return (salary_from + salary_to) / 2
        else:
            return salary_from * 1.2
    elif salary_to:
        return salary_to * 0.8
    return None


def get_vacancies_sj(languages, key):
    url = "https://api.superjob.ru/2.0/vacancies/"
    headers = {
        "X-Api-App-Id": key,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    for language in languages:
        languages[language]["average"] = 0
        languages[language]["vacancies_processed"] = 0
        languages[language]["vacancies_found"] = 0
        for page in count(0):
            payload = {
                "keyword": f'Программист {language}',
                "town": 4,
                "page": page,
                "count": 100
            }
            response = requests.get(url, headers=headers, params=payload)
            response.raise_for_status()
            vacancies = response.json()["objects"]
            total_vacancies = response.json()["total"]
            for vacancy in vacancies:
                salary = calculate_rub_salary_sj(vacancy)
                if salary:
                    languages[language]["average"] += salary
                    languages[language]["vacancies_processed"] += 1
                    languages[language]["vacancies_found"] += total_vacancies

            if not response.json()['more']:
                break
        languages[language]["average"] = int(languages[language]["average"] / languages[language]["vacancies_processed"])
    return languages


def clever_print(statistics, title):
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


if __name__ == "__main__":
    top_languages = {
        "JavaScript": {},
        "Java": {},
        "Python": {},
        "Ruby": {},
        "PHP": {},
    }
    sj_key = dotenv_values(".env")["SJ_SECRET_KEY"]
    try:
        print(
            clever_print(
                get_vacancies_hh(top_languages),
                "Вакансии HeadHunter в Москве"
            ),
            end="\n\n"
        )
        print(clever_print(
            get_vacancies_sj(top_languages, sj_key),
            "Вакансии SuperJob в Москве"
        ))
    except requests.exceptions.HTTPError as error:
        exit("Can't get data from server:\n{0}".format(error))
