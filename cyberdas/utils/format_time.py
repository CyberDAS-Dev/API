from datetime import datetime


def format_time(time: datetime) -> str:
    'Приводит время к формату HH:MM DD/MM/YYYY'
    return (
        f"{str(time.hour).zfill(2)}:{str(time.minute).zfill(2)}"
        " "
        f"{time.day}/{time.month}/{time.year}"
    )
