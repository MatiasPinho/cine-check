#!/usr/bin/env python3
"""Crea un aviso de GitHub solo para funciones nuevas."""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from monitor import CINEMA_NAME, MOVIE_NAME, SOURCE_PAGE, TIME_PATTERN


WEEKDAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def display_date(day: str) -> str:
    parsed = date.fromisoformat(day)
    return f"{WEEKDAYS[parsed.weekday()]} {parsed:%d/%m/%Y}"


def issue_content(showings: list[dict[str, str]]) -> tuple[str, str]:
    if not showings:
        raise ValueError("No hay funciones nuevas para notificar")
    if len(showings) == 1:
        showing = showings[0]
        title = f"🎬 Nueva función IMAX Norcenter: {display_date(showing['date'])} {showing['time']}"
    else:
        title = f"🎬 {len(showings)} nuevas funciones IMAX Norcenter"

    lines = [
        f"## {MOVIE_NAME} · {CINEMA_NAME}",
        "",
        f"Se {'publicó' if len(showings) == 1 else 'publicaron'} {len(showings)} "
        f"{'función nueva' if len(showings) == 1 else 'funciones nuevas'}:",
        "",
        "| Fecha | Hora | Formato |",
        "| --- | --- | --- |",
    ]
    for showing in showings:
        if set(showing) != {"date", "time", "format"}:
            raise ValueError(f"Función inválida: {showing!r}")
        if not TIME_PATTERN.fullmatch(showing["time"]):
            raise ValueError(f"Horario inválido: {showing['time']!r}")
        movie_format = showing["format"].replace("|", "\\|")
        lines.append(f"| {display_date(showing['date'])} | {showing['time']} | {movie_format} |")
    lines.extend(["", f"[Ver funciones y comprar entradas en Showcase]({SOURCE_PAGE})", ""])
    return title, "\n".join(lines)


def create_issue(title: str, body: str) -> str:
    repository = os.environ["GITHUB_REPOSITORY"]
    owner = os.environ["GITHUB_REPOSITORY_OWNER"]
    token = os.environ["GITHUB_TOKEN"]
    request = Request(
        f"https://api.github.com/repos/{repository}/issues",
        data=json.dumps({"title": title, "body": body, "assignees": [owner]}).encode("utf-8"),
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "showcase-imax-monitor/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        issue = json.load(response)
    url = issue.get("html_url")
    if not isinstance(url, str):
        raise ValueError("GitHub no devolvió la URL de la notificación")
    print(f"Notificación creada y asignada a {owner}: {url}")
    return url


def notify(path: Path) -> str | None:
    with path.open(encoding="utf-8") as file:
        showings = json.load(file)
    if not isinstance(showings, list):
        raise ValueError("El archivo de novedades no es una lista")
    if not showings:
        print("No hay funciones nuevas; no se envía ninguna notificación.")
        return None

    title, body = issue_content(showings)
    return create_issue(title, body)


def send_test() -> str:
    return create_issue(
        "🧪 PRUEBA: notificación IMAX Norcenter",
        "## Prueba de notificación al celular\n\n"
        "Este aviso se envió para comprobar las notificaciones de GitHub Mobile. "
        "No se publicó ninguna función nueva y el estado del monitor no se modificó.\n\n"
        f"[Ver la página de Showcase]({SOURCE_PAGE})\n",
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python notify_github.py ARCHIVO_DE_NOVEDADES.json|--test", file=sys.stderr)
        return 2
    try:
        if sys.argv[1] == "--test":
            send_test()
        else:
            notify(Path(sys.argv[1]))
    except (ValueError, OSError, HTTPError, URLError, KeyError, TypeError) as exc:
        print(f"ERROR al enviar la notificación: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
