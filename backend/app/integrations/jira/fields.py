"""Константы полей Jira (проект BASE) и порядок отображения в UI."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

FieldGroup = Literal["profile", "people", "dates", "other"]

# Custom fields из issue BASE-4 (expand=names)
CF_TELEGRAM = "customfield_10402"
CF_CITY = "customfield_10408"
CF_BIRTHDATE = "customfield_10400"
CF_CONTACTS = "customfield_10410"
CF_DIRECTION = "customfield_10405"
CF_GROUP = "customfield_10407"
CF_TRAINING_TYPE = "customfield_10413"
CF_HIRING_STAGE = "customfield_10903"
CF_DOCUMENTS = "customfield_10500"
CF_CV = "customfield_10908"
CF_CV_AU = "customfield_10904"
CF_LEGEND = "customfield_10800"
CF_AI_LEGEND = "customfield_10603"
CF_POSITION = "customfield_10801"
CF_BENCH = "customfield_10605"
CF_OUTSTAFF = "customfield_10909"
CF_REDFLAG = "customfield_10902"
CF_HR = "customfield_10404"
CF_HIRING_HR = "customfield_10901"
CF_MANAGER_AU = "customfield_10906"
CF_MANAGER_TS = "customfield_10900"
CF_KP = "customfield_10907"
CF_ON_PROJECT_SINCE = "customfield_10502"
CF_SIGN_DATE = "customfield_10412"
CF_OS_TRAINING_DATE = "customfield_10704"
CF_FINAL_RUN = "customfield_10501"
CF_ONE_ON_ONE = "customfield_10503"
CF_RESPONSES_YEAR = "customfield_10700"
CF_REJECTION_STAGE = "customfield_10701"
CF_OS_TRAINING = "customfield_10606"
CF_OS_TECH_LEGEND = "customfield_10602"
CF_OS_LEGEND = "customfield_10604"
CF_EXP_WORK_YEAR = "customfield_10702"
CF_EXP_RESPONSES = "customfield_10411"
CF_REG_TYPE_YEAR = "customfield_10703"
CF_INTERVIEW_INFO = "customfield_10409"

# Ссылки для upsert в portal_specialist_link
JIRA_LINK_FIELDS: dict[str, str] = {
    CF_CV: "CV",
    CF_CV_AU: "CV(ау)",
    CF_INTERVIEW_INFO: "Информация с собеседования",
}

# Поля, отображаемые в нативных модулях Cosmolet (не дублировать в секции Jira)
JIRA_NATIVE_UI_FIELD_IDS: frozenset[str] = frozenset(
    {
        CF_DIRECTION,
        CF_CITY,
        CF_TELEGRAM,
        *JIRA_LINK_FIELDS.keys(),
    },
)


def issue_key_regex(project_key: str) -> str:
    """Regex ключа issue для проекта (``BASE-123`` / настраиваемый ``jira_project_key``)."""
    key = (project_key or "BASE").strip().upper() or "BASE"
    return rf"^{re.escape(key)}-\d+$"


# Дефолт для проекта специалистов; валидация в сервисах — через ``issue_key_regex(settings)``.
ISSUE_KEY_RE = issue_key_regex("BASE")


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
    JiraFieldSpec(CF_CV_AU, "CV(ау)", "profile"),
    JiraFieldSpec("status", "Статус", "profile"),
    JiraFieldSpec(CF_REDFLAG, "РедФлаг", "profile"),
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
    JiraFieldSpec(CF_MANAGER_TS, "Менеджер ТС", "people"),
    JiraFieldSpec(CF_LEGEND, "Легенда", "profile"),
    JiraFieldSpec("fixVersions", "Исправить в версиях", "other"),
    JiraFieldSpec(CF_INTERVIEW_INFO, "Информация с собеседования", "other"),
    JiraFieldSpec(CF_AI_LEGEND, "ИИ-легенда", "other"),
    JiraFieldSpec(CF_POSITION, "Должность", "other"),
    JiraFieldSpec(CF_BENCH, "Бенч", "other"),
    JiraFieldSpec(CF_OUTSTAFF, "Outstaff", "other"),
    JiraFieldSpec(CF_FINAL_RUN, "Финальный прогон", "other"),
    JiraFieldSpec(CF_HR, "Ответственный HR", "people"),
    JiraFieldSpec(CF_HIRING_HR, "Нанимающий HR", "people"),
    JiraFieldSpec(CF_MANAGER_AU, "Менеджер АУ", "people"),
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
