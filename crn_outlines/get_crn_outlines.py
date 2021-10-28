"""
BCIT CRN and course outline helpers.

Author: Tim G <tguicherd@bcit.ca>
"""
import re
import sys
from functools import lru_cache
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Adjust the value below if required
DEFAULT_TERM = "202130"


### Do not change the values below!
PREFIX_URL = "https://www.bcit.ca"
API_URL = "https://www.bcit.ca/wp-json/bcit/outlines/v1/load_course_term/"
PROGRAMS = {
    "cit": "https://www.bcit.ca/programs/computer-information-technology-diploma-full-time-5540dipma/",
    "cst": "https://www.bcit.ca/programs/computer-systems-technology-diploma-full-time-5500dipma/",
}


def extract_course_links(html_data):
    """
    Takes HTML data (preferrably bytes) and returns a dictionary.
    Keys are the course names, values are the outline URLS (basepage - useless).
    """
    soup = BeautifulSoup(html_data, features="html.parser")
    courses = dict()
    lines = soup.select("table#programmatrix tr")
    for line in lines:
        course = line.select("td.course_number")
        if not course:
            continue
        course_name = course[0].text
        outline = line.select("a.course_outline")
        if not outline:
            continue

        outline_url = outline[0].attrs["href"]
        if outline_url.startswith("/"):
            outline_url = urljoin(PREFIX_URL, outline_url)

        courses[course_name] = outline_url

    return courses


@lru_cache
def _get_api_data(term, course_name):
    """Returns JSON data from BCIT's API for course outline information"""
    department, course_number = course_name.split(" ")
    department = department.lower()

    api_url = API_URL
    if api_url.endswith("/"):
        api_url = API_URL[:-1]

    url = f"{api_url}/{term}/{department}/{course_number}/"
    resp = requests.get(url)
    data = resp.json()
    return data


def get_crn_api(term, course_name):
    """Returns the CRN associated with a course name for a given term. Just takes the first one..."""
    data = _get_api_data(term, course_name)
    try:
        return data["data"]["courses"][0]["crn"]
    except TypeError:
        return None


def get_outline_url(term, course_name):
    """Returns the complete URL of the course outline for a given course name / term (full outline)"""
    crn = get_crn_api(term, course_name)
    if crn:
        return f"{PREFIX_URL}/outlines/{term}{crn}"


def main(program, term):
    """Main function - takes a program name and prints out informations about courses"""
    url = PROGRAMS[program.lower()]
    resp = requests.get(url)

    courses = extract_course_links(resp.content)

    for course in courses:
        crn = get_crn_api(term, course)
        url = get_outline_url(term, course)

        if not crn or not url:
            print(f"Something went wrong with course {course}. Sorry!")
            continue

        print(course, crn, url)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        program = sys.argv[1].lower()
    else:
        program = "cit"

    if program not in PROGRAMS:
        print(
            f"I don't know where to find info about the program {program.upper()}. Try with CIT or CST."
        )
        sys.exit(-1)

    if len(sys.argv) > 2:
        term = sys.argv[2]
    else:
        term = DEFAULT_TERM

    if not re.match(r"^20\d{2}[123]0$", term):
        print(f"Term {term} seems invalid. Sorry!")
        sys.exit(-1)

    main(program, term)
