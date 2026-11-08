"""Нейтральные id полей Jira и порядок отображения в UI.

Числа не из чужого проекта: свой Jira подставляет свои id в этот модуль.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

FieldGroup = Literal["profile", "people", "dates", "other"]

CF_TELEGRAM = "customfield_10001"
CF_CITY = "customfield_10002"
CF_BIRTHDATE = "customfield_10003"
CF_CONTACTS = "customfield_10004"
CF_DIRECTION = "customfield_10005"
CF_GROUP = "customfield_10006"
CF_TRAINING_TYPE = "customfield_10007"
CF_HIRING_STAGE = "customfield_10008"
CF_DOCUMENTS = "customfield_10009"
CF_CV = "customfield_10010"
CF_CV_AU = "customfield_10011"
CF_LEGEND = "customfield_10012"
CF_AI_LEGEND = "customfield_10013"
CF_POSITION = "customfield_10014"
CF_BENCH = "customfield_10015"
CF_OUTSTAFF = "customfield_10016"
CF_REDFLAG = "customfield_10017"
CF_HR = "customfield_10018"
CF_HIRING_HR = "customfield_10019"
CF_MANAGER_AU = "customfield_10020"
CF_MANAGER_TS = "customfield_10021"
CF_KP = "customfield_10022"
CF_ON_PROJECT_SINCE = "customfield_10023"
CF_SIGN_DATE = "customfield_10024"
CF_OS_TRAINING_DATE = "customfield_10025"
CF_FINAL_RUN = "customfield_10026"
CF_ONE_ON_ONE = "customfield_10027"
CF_RESPONSES_YEAR = "customfield_10028"
CF_REJECTION_STAGE = "customfield_10029"
CF_OS_TRAINING = "customfield_10030"
CF_OS_TECH_LEGEND = "customfield_10031"
CF_OS_LEGEND = "customfield_10032"
CF_EXP_WORK_YEAR = "customfield_10033"
CF_EXP_RESPONSES = "customfield_10034"
CF_REG_TYPE_YEAR = "customfield_10035"
CF_INTERVIEW_INFO = "customfield_10036"

# Ссылки для upsert в portal_specialist_link
JIRA_LINK_FIELDS: dict[str, str] = {
    CF_CV: "CV",
    CF_CV_AU: "CV (дополнительное)",
    CF_INTERVIEW_INFO: "Информация с собеседования",
}

# Поля, отображаемые в нативных модулях Atrium (не дублировать в секции Jira)
JIRA_NATIVE_UI_FIELD_IDS: frozenset[str] = frozenset(
    {
        CF_DIRECTION,
        CF_CITY,
        CF_TELEGRAM,
        *JIRA_LINK_FIELDS.keys(),
    },
)


def issue_key_regex(project_key: str) -> str:
    """Regex ключа issue. Пустой ключ проекта не совпадает ни с одним issue."""
    key = (project_key or "").strip().upper()
    if not key:
        return r"^(?!)$"
    return rf"^{re.escape(key)}-\d+$"


# Пример для тестов и подсказок. Валидация в сервисах — через ``issue_key_regex(settings)``.
ISSUE_KEY_RE = issue_key_regex("PROJ")


@dataclass(frozen=True, slots=True)
class JiraFieldSpec:
    field_id: str
    label: str
    group: FieldGroup


# Порядок полей в UI (как в Jira)
JIRA_FIELD_SPECS: tuple[JiraFieldSpec, ...] = (
    JiraFieldSpec("summary", "ФИО", "profile"),
    JiraFieldSpec(CF_DIRECTION, "Направление", "profile"),
    JiraFieldSpec(CF_HIRING_STAGE, "Стадия найма", "profile"),
    JiraFieldSpec(CF_TELEGRAM, "Telegram", "profile"),
    JiraFieldSpec(CF_CONTACTS, "Доп. контакты", "profile"),
    JiraFieldSpec(CF_CITY, "Город", "profile"),
    JiraFieldSpec(CF_GROUP, "Группа", "profile"),
    JiraFieldSpec(CF_TRAINING_TYPE, "Тип обучения", "profile"),
    JiraFieldSpec(CF_REG_TYPE_YEAR, "Тип оформления за последний год", "profile"),
    JiraFieldSpec("issuetype", "Тип", "profile"),
    JiraFieldSpec(CF_DOCUMENTS, "Документы", "profile"),
    JiraFieldSpec(CF_CV, "CV", "profile"),
    JiraFieldSpec(CF_CV_AU, "CV (дополнительное)", "profile"),
    JiraFieldSpec("status", "Статус", "profile"),
    JiraFieldSpec(CF_REDFLAG, "Флаг", "profile"),
    JiraFieldSpec("priority", "Приоритет", "profile"),
    JiraFieldSpec(CF_RESPONSES_YEAR, "Отклики за последний год", "profile"),
    JiraFieldSpec(CF_REJECTION_STAGE, "Отказ на этапе", "profile"),
    JiraFieldSpec(CF_OS_TRAINING, "ОС с обучения", "profile"),
    JiraFieldSpec(CF_OS_TECH_LEGEND, "ОС по тех. легенде", "profile"),
    JiraFieldSpec(CF_OS_LEGEND, "ОС по легенде", "profile"),
    JiraFieldSpec(CF_EXP_WORK_YEAR, "Опыт работы по направлению за год", "profile"),
    JiraFieldSpec(CF_EXP_RESPONSES, "Опыт откликов", "profile"),
    JiraFieldSpec("environment", "Окружение", "profile"),
    JiraFieldSpec("labels", "Метки", "profile"),
    JiraFieldSpec(CF_MANAGER_TS, "Менеджер сопровождения", "people"),
    JiraFieldSpec(CF_LEGEND, "Легенда", "profile"),
    JiraFieldSpec("fixVersions", "Исправить в версиях", "other"),
    JiraFieldSpec(CF_INTERVIEW_INFO, "Информация с собеседования", "other"),
    JiraFieldSpec(CF_AI_LEGEND, "ИИ-легенда", "other"),
    JiraFieldSpec(CF_POSITION, "Должность", "other"),
    JiraFieldSpec(CF_BENCH, "Бенч", "other"),
    JiraFieldSpec(CF_OUTSTAFF, "Внешний проект", "other"),
    JiraFieldSpec(CF_FINAL_RUN, "Финальный прогон", "other"),
    JiraFieldSpec(CF_HR, "Ответственный HR", "people"),
    JiraFieldSpec(CF_HIRING_HR, "Нанимающий HR", "people"),
    JiraFieldSpec(CF_MANAGER_AU, "Менеджер отдела", "people"),
    JiraFieldSpec(CF_KP, "КП", "people"),
    JiraFieldSpec("assignee", "Исполнитель", "people"),
    JiraFieldSpec("reporter", "Автор", "people"),
    JiraFieldSpec(CF_ON_PROJECT_SINCE, "На проекте с", "dates"),
    JiraFieldSpec(CF_BIRTHDATE, "Дата рождения", "dates"),
    JiraFieldSpec("resolutiondate", "Дата решения", "dates"),
    JiraFieldSpec(CF_SIGN_DATE, "Дата подписи", "dates"),
    JiraFieldSpec(CF_OS_TRAINING_DATE, "Дата ОС с обучения", "dates"),
    JiraFieldSpec("created", "Создано", "dates"),
    JiraFieldSpec("updated", "Обновлено", "dates"),
    JiraFieldSpec("description", "Описание", "other"),
    JiraFieldSpec(CF_ONE_ON_ONE, "1:1", "other"),
)

GROUP_LABELS: dict[FieldGroup, str] = {
    "profile": "Профиль",
    "people": "Люди",
    "dates": "Даты",
    "other": "Прочее",
}

JIRA_FIELD_LABEL_BY_ID: dict[str, str] = {spec.field_id: spec.label for spec in JIRA_FIELD_SPECS}
