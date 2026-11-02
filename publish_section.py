# -*- coding: utf-8 -*-
"""Обновляет одну секцию data.json в репозитории mini-dash и отправляет на GitHub.

Используется задачами Kimi Work: каждая задача после сбора данных вызывает
publish(...) со своей секцией. Ошибки публикации не должны ронять задачу —
вызывающая сторона оборачивает вызов в try/except.
"""
import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(REPO_DIR, "data.json")
MSK = timezone(timedelta(hours=3))


def _git(*args):
    return subprocess.run(
        ["git", "-C", REPO_DIR] + list(args),
        capture_output=True,
        text=True,
        timeout=120,
    )


def publish(section_key, value, list_key=None, match=None):
    """Обновить секцию data.json и запушить.

    publish("rates", {...})                    — простая секция-объект
    publish(None, {...}, list_key="weather", match="city")  — элемент списка
    """
    last_error = None
    for _ in range(3):
        try:
            _git("pull", "--rebase", "--autostash", "origin", "main")
            try:
                with open(DATA_PATH, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

            if list_key:
                items = data.setdefault(list_key, [])
                for i, item in enumerate(items):
                    if item.get(match) == value.get(match):
                        items[i] = value
                        break
                else:
                    items.append(value)
            else:
                data[section_key] = value

            data["updatedAt"] = datetime.now(MSK).isoformat(timespec="seconds")

            with open(DATA_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            _git("add", "data.json")
            commit = _git("commit", "-m", "Update %s" % (list_key or section_key))
            if commit.returncode != 0:
                # Нечего коммитить — данные не изменились
                return True
            push = _git("push", "origin", "HEAD:main")
            if push.returncode == 0:
                return True
            last_error = push.stderr
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(5)
    raise RuntimeError("publish failed: %s" % last_error)
