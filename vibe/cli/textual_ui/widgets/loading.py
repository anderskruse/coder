from __future__ import annotations

from datetime import datetime
import random
from time import time
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from vibe.cli.textual_ui.widgets.no_markup_static import NoMarkupStatic
from vibe.cli.textual_ui.widgets.spinner import SpinnerMixin, SpinnerType


class LoadingWidget(SpinnerMixin, Static):
    TARGET_COLORS = ("#87CEEB", "#5DADE2", "#3498DB", "#2874A6", "#1B4F72")
    SPINNER_TYPE = SpinnerType.BRAILLE

    # --- GENERELLE KØBENHAVNER-EGGS ---
    EASTER_EGGS: ClassVar[list[str]] = [
        # Mad & Drikke
        "Spiser en onsdagssnegl",
        "Betaler 60kr for en havre-latte",
        "Kompilerer smørrebrød",
        "Drikker en flat white på Vesterbro",
        "Rød grød med fløøøde",
        "Laver Koldskålssuppe",

        # Transport & Byen
        "Cykler over Dronning Louises Bro",
        "Venter på Metroringen",
        "Leder efter et ledigt skrivebord på fuglebakken",
        "Leder efter P-plads på Østerbro",
        "Sidder fast bag en ladcykel",
        "count() turister i Nyhavn",
        "Deployer til Rundetårn",

        # Tech & Kultur
        "Reflekterer over Rejsekortet",
        "Læser Kierkegaard i regnvejr",
        "Træner Den Lille Havfrue",  # (AI weights)
        "Hygger max",
        "Sender god karma via 5G",
        "Klapper kontorhunden",
        "Git push --force til Folketinget",
        "Debugger i Kødbyen",
        "In denmark, we actually get paid to study",
    ]

    # --- HALLOWEEN (31. OKT) ---
    EASTER_EGGS_HALLOWEEN: ClassVar[list[str]] = [
        "Rasler på Rådhuspladsen",
        "Udhuler græskar i Tivoli",
        "Kalder på ånderne i serverrummet",
        "Brygger potions af Gammel Dansk",
        "Spøger i terminalen",
        "Leder efter bugs på Assistens Kirkegård",
    ]

    # --- JUL (DECEMBER) ---
    EASTER_EGGS_DECEMBER: ClassVar[list[str]] = [
        "Pakker gaver ind i spaghetti-kode",
        "Pynter træet med RGB-lys",
        "Drikker gløgg i Torvehallerne",
        "Bygger snemænd af pixels",
        "Skriver julekort i Markdown",
        "Venter på S-toget i snevejr",
        "Spiser æbleskiver med source code",
    ]

    # --- FORÅR (MARTS - MAJ) ---
    EASTER_EGGS_SPRING: ClassVar[list[str]] = [
        "Kigger på kirsebærtræer på Bispebjerg", # Klassisk Insta-moment
        "Drikker den første ude-øl",
        "Sender gækkebrev til IT-support",
        "Nyder solen i Kongens Have",
    ]

    # --- SOMMER (JUNI - AUGUST) ---
    EASTER_EGGS_SUMMER: ClassVar[list[str]] = [
        "Hopper i Havnebadet",
        "Spiser koldskål med kammerjunkere",
        "Sveder over tastaturet",
        "Står i kø til Roskilde Festival",
        "Spiser is på Islands Brygge",
        "Griller i Fælledparken",
    ]

    # --- FREDAG (SPECIFIK UGEDAG) ---
    EASTER_EGGS_FRIDAY: ClassVar[list[str]] = [
        "Deployer til prod (på en fredag?!)",
        "Åbner fredagsbaren",
        "Skåler i Netto-bajer",
        "Committer før weekenden",
        "Spiller bordfodbold",
    ]

    def __init__(self, status: str | None = None) -> None:
        super().__init__(classes="loading-widget")
        self.init_spinner()
        self.status = status or self._get_default_status()
        self.current_color_index = 0
        self.transition_progress = 0
        self._status_widget: Static | None = None
        self.hint_widget: Static | None = None
        self.start_time: float | None = None
        self._last_elapsed: int = -1

    def _get_easter_egg(self) -> str | None:
        EASTER_EGG_PROBABILITY = 0.15  # Lidt højere chance nu hvor der er flere sjove!

        if random.random() < EASTER_EGG_PROBABILITY:
            available_eggs = list(self.EASTER_EGGS)

            now = datetime.now()

            # Måneder
            MARCH, APRIL, MAY = 3, 4, 5
            JUNE, JULY, AUGUST = 6, 7, 8
            OCTOBER = 10
            DECEMBER = 12

            # Specifikke dage
            HALLOWEEN_DAY = 31
            FRIDAY = 4  # Monday is 0, Sunday is 6

            # Sæson logic
            if now.month in (MARCH, APRIL, MAY):
                available_eggs.extend(self.EASTER_EGGS_SPRING)

            elif now.month in (JUNE, JULY, AUGUST):
                available_eggs.extend(self.EASTER_EGGS_SUMMER)

            elif now.month == OCTOBER and now.day == HALLOWEEN_DAY:
                available_eggs.extend(self.EASTER_EGGS_HALLOWEEN)

            elif now.month == DECEMBER:
                available_eggs.extend(self.EASTER_EGGS_DECEMBER)

            # Ugedags logic (Kan kombineres med sæsoner)
            if now.weekday() == FRIDAY:
                available_eggs.extend(self.EASTER_EGGS_FRIDAY)

            return random.choice(available_eggs)
        return None

    def _get_default_status(self) -> str:
        return self._get_easter_egg() or "Generating"

    def _apply_easter_egg(self, status: str) -> str:
        return self._get_easter_egg() or status

    def set_status(self, status: str) -> None:
        self.status = self._apply_easter_egg(status)
        self._update_animation()

    def compose(self) -> ComposeResult:
        with Horizontal(classes="loading-container"):
            self._indicator_widget = Static(
                self._spinner.current_frame(), classes="loading-indicator"
            )
            yield self._indicator_widget

            self._status_widget = Static("", classes="loading-status")
            yield self._status_widget

            self.hint_widget = NoMarkupStatic(
                "(0s esc to interrupt)", classes="loading-hint"
            )
            yield self.hint_widget

    def on_mount(self) -> None:
        self.start_time = time()
        self._update_animation()
        self.start_spinner_timer()

    def on_resize(self) -> None:
        self.refresh_spinner()

    def _update_spinner_frame(self) -> None:
        if not self._is_spinning:
            return
        self._update_animation()

    def _get_color_for_position(self, position: int) -> str:
        current_color = self.TARGET_COLORS[self.current_color_index]
        next_color = self.TARGET_COLORS[
            (self.current_color_index + 1) % len(self.TARGET_COLORS)
        ]
        if position < self.transition_progress:
            return next_color
        return current_color

    def _build_status_text(self) -> str:
        parts = []
        for i, char in enumerate(self.status):
            color = self._get_color_for_position(1 + i)
            parts.append(f"[{color}]{char}[/]")
        ellipsis_start = 1 + len(self.status)
        color_ellipsis = self._get_color_for_position(ellipsis_start)
        parts.append(f"[{color_ellipsis}]… [/]")
        return "".join(parts)

    def _update_animation(self) -> None:
        total_elements = 1 + len(self.status) + 1

        if self._indicator_widget:
            spinner_char = self._spinner.next_frame()
            color = self._get_color_for_position(0)
            self._indicator_widget.update(f"[{color}]{spinner_char}[/]")

        if self._status_widget:
            self._status_widget.update(self._build_status_text())

        self.transition_progress += 1
        if self.transition_progress > total_elements:
            self.current_color_index = (self.current_color_index + 1) % len(
                self.TARGET_COLORS
            )
            self.transition_progress = 0

        if self.hint_widget and self.start_time is not None:
            elapsed = int(time() - self.start_time)
            if elapsed != self._last_elapsed:
                self._last_elapsed = elapsed
                self.hint_widget.update(f"({elapsed}s esc to interrupt)")
