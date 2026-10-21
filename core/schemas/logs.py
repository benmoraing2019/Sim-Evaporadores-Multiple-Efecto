"""
Sistema de gestion de logs en el sistema de calculo
"""

from colorama import Fore, Style
from dataclasses import dataclass

VERBOSE = True

@dataclass
class Log:

    @staticmethod
    def info(text:str, show = False):
        switch = show or VERBOSE
        text = "[INFO]....." + text
        switch and print(text)

    @staticmethod
    def ok(text:str, show = False):
        switch = show or VERBOSE
        text = Fore.LIGHTGREEN_EX +"[OK]....." + text + Style.RESET_ALL
        switch and print(text)

    @staticmethod
    def error(text:str, show = False):
        switch = show or VERBOSE
        text = Fore.LIGHTRED_EX+"[ERROR]....." + text + Style.RESET_ALL
        switch and print(text)

    @staticmethod
    def warning(text:str, show = False):
        switch = show or VERBOSE
        text = Fore.LIGHTYELLOW_EX + "[WARNING]....." + text + Style.RESET_ALL
        switch and print(text)

    @staticmethod
    def service(service_name:str, text:str, show = False):
        switch = show or VERBOSE
        text = Fore.YELLOW + f"[{service_name}]....." + Style.RESET_ALL + text
        switch and print(text)

    @staticmethod
    def event(text:str, show = False):
        switch = show or VERBOSE
        text = Fore.CYAN + "[EVENT]....." + Style.RESET_ALL + text
        switch and print(text)

if __name__ == "__main__":
    Log.ok("Todo ok")
    Log.error("Todo falló")
    Log.service("ServicioPrueba", "Completado")
    Log.event("Iniciando evento 1")