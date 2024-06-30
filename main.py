import asyncio
import getpass
import logging
import sys
from dataclasses import dataclass
from enum import Enum

import aiohttp
from bs4 import BeautifulSoup


@dataclass
class Subject:
    id: int
    term_id: int
    short_code: str
    name: str
    catalog_link: str
    garant_link: str
    garant_name: str


class SemesterType(Enum):
    ZS = (0,)
    LS = 1


@dataclass
class Semester:
    faculty: int
    id: int
    type: SemesterType
    yearStart: int
    yearEnd: int


@dataclass
class Faculty:
    id: int
    name: str
    # abbreviation: str


async def interactive_login(session: aiohttp.ClientSession):
    """
    Prompts the user for his login and password, then uses them to login into the system
    """
    login = str(input("Login: "))
    password = getpass.getpass()
    login_struct = {
        "login_hidden": "1",
        "destination": "/auth/?lang=en",
        "auth_id_hidden": "0",
        "auth_2fa_type": "no",
        "credential_0": login,
        "credential_1": password,
        "credential_k": "",
        "credential_2": "86400",
    }
    response = await session.post(
        "/system/login.pl", data=login_struct, allow_redirects=False
    )
    logging.debug(await response.text())
    logging.debug(response.status)
    if response.status < 400 and response.status >= 300:
        logging.info(f"Logged in as {login}!")
    else:
        raise RuntimeError("Login/password is incorrect! Can't login!")


def separate_terms(arr: list):
    """
    Parses however many terms there were to pass a subject (RT, OT, OT2 ...)
    """
    result: list = []
    arr_len = len(arr)
    # if we have X amount if terms with A, B, C, D, E, FX:
    if not arr_len % 6:
        logging.debug(f"Got {arr_len} marks and {int(arr_len/6)} terms")
        for i, el in enumerate(arr):
            if not i % 6:
                #
                result.append([])
            result[i // 6].append(el)
            # logging.debug([i, i % 6, result])
    elif not arr_len % 7:
        raise NotImplementedError("7 option table is not supported yet!")
    return result


def fix_array(arr):
    result = []
    for el in arr:
        try:
            result.append(int(el.contents[0]))
        except ValueError:
            continue
    return result


async def parse_stats_page(session: aiohttp.ClientSession):
    """
    Parses the page displaying results of a subject
    """
    page_request = await session.get(
        "/auth/student/hodnoceni.pl?fakulta=70;obdobi=665;odkud=;program=0;predmet=393372;pismeno=;lang=sk"
    )
    parse_obj = BeautifulSoup(await page_request.text(), features="html.parser")
    table = parse_obj.find(id="tmtab_1")
    cells = table.find_all("td", attrs={"class": "odsazena"})
    # logging.debug(table)
    # logging.debug(cells)
    # for item in cells:
    #     logging.debug(item.contents)
    return separate_terms(fix_array(cells))


async def get_faculties(session: aiohttp.ClientSession):  # -> list[Faculty]:
    """
    Parses the main page, to get the list of all faculties
    """
    request = await session.get("/auth/student/hodnoceni.pl")
    parsed = BeautifulSoup(await request.text(), features="html.parser")
    table = parsed.find("table")
    cells = table.find_all("td", class_="odsazena", attrs={"valign": "top"})
    logging.debug(table)
    logging.debug(cells)


async def main():
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG,
        format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    )
    # logging.debug("Test")
    # set the base URL for my uni's information system
    session: aiohttp.ClientSession = aiohttp.ClientSession(
        base_url="https://is.stuba.sk"
    )
    # get the user to login
    await interactive_login(session)
    await get_faculties(session)
    # testing the stats page parser
    logging.info(await parse_stats_page(session))
    await session.close()


asyncio.run(main())
