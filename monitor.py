#!/usr/bin/env python3
"""Monitor de funciones de Avengers Endgame: Bonus en IMAX Norcenter."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


FILM_ID = 6017
HOUSE_ID = 3250
MOVIE_NAME = "Avengers Endgame: Bonus"
CINEMA_NAME = "IMAX Theatre (Norcenter)"
SOURCE_PAGE = (
    "https://entradas.todoshowcase.com/showcase/pelicula"
    f"?filmid={FILM_ID}&house_id={HOUSE_ID}"
)
# Esta es la API JSON que usa el JavaScript de SOURCE_PAGE para mostrar las funciones.
API_URL = f"https://api.voyalcine.net/films/{FILM_ID}/tree/{HOUSE_ID}"
DEFAULT_STATE = Path(__file__).resolve().parent / "state" / "showings.json"
TIME_PATTERN = re.compile(r"^(?:N )?(?:[01]?\d|2[0-3]):[0-5]\d$")


def fetch_data() -> dict:
    request = Request(
        API_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "showcase-imax-monitor/1.0",
        },
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=20) as response:
                data = json.load(response)
            if not isinstance(data, dict):
                raise ValueError("La API no devolvió un objeto JSON")
            return data
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            if attempt == 2:
                raise RuntimeError(f"No se pudo consultar la API después de 3 intentos: {exc}") from exc
            time.sleep(2 ** attempt)
    raise AssertionError("Bucle de reintentos incompleto")


def extract_showings(data: dict) -> list[dict[str, str]]:
    if data.get("id") != FILM_ID:
        raise ValueError(f"La API devolvió otra película: id={data.get('id')!r}")
    days = data.get("days")
    if not isinstance(days, dict):
        raise ValueError("Falta el objeto 'days' en la respuesta de la API")

    showings: set[tuple[str, str, str]] = set()
    saw_other_cinema = False
    saw_target_cinema = False

    for day, cinemas in days.items():
        try:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Fecha inválida en la API: {day!r}") from exc
        if not isinstance(cinemas, list):
            raise ValueError(f"Lista de cines inválida para {day}")

        for cinema in cinemas:
            if not isinstance(cinema, dict):
                raise ValueError(f"Datos de cine inválidos para {day}")
            name = cinema.get("name")
            if not isinstance(name, str):
                raise ValueError(f"Cine sin nombre para {day}")
            normalized_name = name.casefold()
            if "imax" not in normalized_name or "norcenter" not in normalized_name:
                saw_other_cinema = True
                continue
            saw_target_cinema = True
            formats = cinema.get("formats")
            if not isinstance(formats, list):
                raise ValueError(f"Faltan los formatos de {CINEMA_NAME} para {day}")
            for movie_format in formats:
                if not isinstance(movie_format, dict):
                    raise ValueError(f"Formato inválido para {day}")
                description = movie_format.get("formatDescription")
                performances = movie_format.get("performances")
                if not isinstance(description, str) or not description.strip():
                    raise ValueError(f"Formato sin descripción para {day}")
                if not isinstance(performances, list):
                    raise ValueError(f"Faltan las funciones de {day}, {description}")
                for performance in performances:
                    if not isinstance(performance, dict):
                        raise ValueError(f"Función inválida para {day}")
                    raw_time = performance.get("showTime")
                    if not isinstance(raw_time, str):
                        raise ValueError(f"Función sin horario para {day}")
                    show_time = " ".join(raw_time.split())
                    if not TIME_PATTERN.fullmatch(show_time):
                        raise ValueError(f"Horario inválido para {day}: {raw_time!r}")
                    showings.add((day, show_time, description.strip()))

    if saw_other_cinema and not saw_target_cinema:
        raise ValueError(f"La API tiene cines, pero no aparece {CINEMA_NAME}")

    return [
        {"date": day, "time": show_time, "format": movie_format}
        for day, show_time, movie_format in sorted(showings)
    ]


def validate_showings(showings: object, path: Path) -> list[dict[str, str]]:
    if not isinstance(showings, list) or any(
        not isinstance(show, dict)
        or set(show) != {"date", "time", "format"}
        or any(not isinstance(value, str) for value in show.values())
        for show in showings
    ):
        raise ValueError(f"Funciones inválidas en el estado: {path}")
    return showings


def load_state(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as file:
        state = json.load(file)
    if not isinstance(state, dict) or state.get("version") not in (1, 2):
        raise ValueError(f"Estado inválido: {path}")
    current = validate_showings(state.get("showings"), path)
    seen = validate_showings(state.get("seen", current), path)
    return {"showings": current, "seen": seen}


def save_state(
    path: Path,
    showings: list[dict[str, str]],
    seen: list[dict[str, str]] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(
        {"version": 2, "showings": showings, "seen": seen if seen is not None else showings},
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def showing_key(showing: dict[str, str]) -> tuple[str, str, str]:
    return showing["date"], showing["time"], showing["format"]


def describe(showing: dict[str, str]) -> str:
    return f"{showing['date']} {showing['time']} — {showing['format']}"


def run(state_path: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    current = extract_showings(fetch_data())
    previous_state = load_state(state_path)
    new_showings = []

    print(f"Película: {MOVIE_NAME}")
    print(f"Cine: {CINEMA_NAME}")
    print(f"Página: {SOURCE_PAGE}")
    print(f"Funciones disponibles: {len(current)}")
    for showing in current:
        print(f"  • {describe(showing)}")

    if previous_state is None:
        print("Primera ejecución: se guarda el estado inicial, sin alertas de funciones nuevas.")
        seen = current
    else:
        previous_seen = previous_state["seen"]
        seen_keys = {showing_key(showing) for showing in previous_seen}
        new_showings = [showing for showing in current if showing_key(showing) not in seen_keys]
        seen_by_key = {showing_key(showing): showing for showing in previous_seen + current}
        seen = [seen_by_key[key] for key in sorted(seen_by_key)]
        if new_showings:
            print(f"\n¡NUEVAS FUNCIONES DETECTADAS! ({len(new_showings)})")
            for showing in new_showings:
                print(f"NUEVA FUNCIÓN: {describe(showing)}")
        else:
            print("Sin funciones nuevas desde la ejecución anterior.")

    save_state(state_path, current, seen)
    print(f"Estado guardado en {state_path}")
    return current, new_showings


def write_actions_summary(current: list[dict[str, str]], new_showings: list[dict[str, str]]) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    if new_showings:
        status = f"### 🎬 {len(new_showings)} función(es) nueva(s) en IMAX Norcenter\n\n"
        rows = new_showings
    else:
        status = "### Sin funciones nuevas en IMAX Norcenter\n\n"
        rows = current
    lines = [
        status,
        f"**Avengers Endgame: Bonus** · {len(current)} funciones disponibles.\n\n",
        "| Fecha | Hora | Formato |\n",
        "| --- | --- | --- |\n",
    ]
    for showing in rows:
        values = [showing[field].replace("|", "\\|") for field in ("date", "time", "format")]
        lines.append(f"| {' | '.join(values)} |\n")
    lines.append(f"\n[Ver funciones en Showcase]({SOURCE_PAGE})\n")
    with open(summary_path, "a", encoding="utf-8") as summary:
        summary.writelines(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_STATE,
        help=f"Archivo de estado (por defecto: {DEFAULT_STATE})",
    )
    parser.add_argument(
        "--changes",
        type=Path,
        help="Guardar las funciones nuevas en JSON para el paso de notificación",
    )
    args = parser.parse_args()
    try:
        current, new_showings = run(args.state)
        if args.changes:
            args.changes.write_text(
                json.dumps(new_showings, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        output_path = os.environ.get("GITHUB_OUTPUT")
        if output_path:
            with open(output_path, "a", encoding="utf-8") as output:
                output.write(f"new_count={len(new_showings)}\n")
        write_actions_summary(current, new_showings)
    except (ValueError, OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}. El estado anterior se conserva.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
