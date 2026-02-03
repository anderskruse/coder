from __future__ import annotations

import os
from typing import ClassVar

from dotenv import set_key
from textual.app import ComposeResult
from textual.binding import Binding, BindingType
from textual.containers import Center, Horizontal, Vertical
from textual.events import MouseUp
#### KK-code altercation BEGIN ####
from textual.validation import Length, URL
from textual.widgets import Input, Static
#### KK-code altercation END ####

from vibe.cli.clipboard import copy_selection_to_clipboard
from vibe.cli.textual_ui.widgets.no_markup_static import NoMarkupStatic
from vibe.core.config import VibeConfig
from vibe.core.paths.global_paths import GLOBAL_ENV_FILE
from vibe.setup.onboarding.base import OnboardingScreen


#### KK-code altercation BEGIN ####
def _save_to_config_and_env(api_base: str, api_key: str) -> None:
    """Save both API base URL and API key to config file and env file."""
    # Save API key to .env file
    GLOBAL_ENV_FILE.path.parent.mkdir(parents=True, exist_ok=True)
    set_key(GLOBAL_ENV_FILE.path, "SCALEWAY_API_KEY", api_key)

    # Save API base to config.toml
    config_updates = {
        "providers": [
            {
                "name": "scaleway",
                "api_base": api_base,
                "api_key_env_var": "SCALEWAY_API_KEY",
                "backend": "generic",
            }
        ]
    }
    VibeConfig.save_updates(config_updates)
#### KK-code altercation END ####


class ApiKeyScreen(OnboardingScreen):
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("ctrl+c", "cancel", "Cancel", show=False),
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    NEXT_SCREEN = None

    def __init__(self) -> None:
        super().__init__()
        self.current_step = "url"  # Start with URL input  #### KK-code altercation

    def compose(self) -> ComposeResult:
        #### KK-code altercation BEGIN ####
        self.url_input = Input(
            id="api-url",
            placeholder="https://api.scaleway.ai/YOUR-PROJECT-ID/v1",
            validators=[
                Length(minimum=1, failure_description="API URL cannot be empty."),
                URL(failure_description="Please enter a valid URL."),
            ],
        )

        self.key_input = Input(
            password=True,
            id="api-key",
            placeholder="Indsæt din API nøgle her",
            validators=[Length(minimum=1, failure_description="API key cannot be empty.")],
        #### KK-code altercation END ####
        )

        with Vertical(id="api-key-outer"):
            yield Static("", classes="spacer")
            yield Center(Static("Konfigurer Scaleway AI", id="api-key-title"))  #### KK-code altercation
            with Center():
                with Vertical(id="api-key-content"):
                    #### KK-code altercation BEGIN ####
                    # URL Section
                    yield Static(
                        "Først, indsæt din Scaleway API endpoint URL:",
                        id="url-hint"
                    )
                    yield Static(
                        "[dim]Find det i Scaleway Console → AI → Generative APIs[/]",
                        id="url-help"
                    )
                    yield Center(Horizontal(self.url_input, id="url-input-box"))
                    yield Static("", id="url-feedback")

                    # Key Section (hidden initially)
                    yield Static(
                        "Nu, indsæt din API nøgle:",
                        id="key-hint",
                        classes="hidden"
                    )
                    yield Static(
                        "[dim]Find den i Scaleway Console → IAM → API Keys[/]",
                        id="key-help",
                        classes="hidden"
                    )
                    yield Center(Horizontal(self.key_input, id="key-input-box", classes="hidden"))
                    yield Static("", id="key-feedback")
                    #### KK-code altercation END ####
            yield Static("", classes="spacer")

    def on_mount(self) -> None:
        self.url_input.focus()  #### KK-code altercation

    def on_input_changed(self, event: Input.Changed) -> None:
        #### KK-code altercation BEGIN ####
        if event.input.id == "api-url":
            feedback = self.query_one("#url-feedback", Static)
            input_box = self.query_one("#url-input-box")
        else:
            feedback = self.query_one("#key-feedback", Static)
            input_box = self.query_one("#key-input-box")
        #### KK-code altercation END ####

        if event.validation_result is None:
            return

        input_box.remove_class("valid", "invalid")
        feedback.remove_class("error", "success")

        if event.validation_result.is_valid:
            feedback.update("Tryk Enter for at fortsætte ↵")  #### KK-code altercation
            feedback.add_class("success")
            input_box.add_class("valid")
            return

        descriptions = event.validation_result.failure_descriptions
        feedback.update(descriptions[0] if descriptions else "Invalid input")  #### KK-code altercation
        feedback.add_class("error")
        input_box.add_class("invalid")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        #### KK-code altercation BEGIN ####
        if not event.validation_result or not event.validation_result.is_valid:
            return

        if event.input.id == "api-url":
            # URL submitted, now show API key input
            self.current_step = "key"
            self.stored_url = event.value

            # Hide URL section, show key section
            self.query_one("#url-hint").add_class("hidden")
            self.query_one("#url-help").add_class("hidden")
            self.query_one("#url-input-box").add_class("hidden")
            self.query_one("#url-feedback").add_class("hidden")

            self.query_one("#key-hint").remove_class("hidden")
            self.query_one("#key-help").remove_class("hidden")
            self.query_one("#key-input-box").remove_class("hidden")

            self.key_input.focus()
        else:
            # API key submitted, save everything
            self._save_and_finish(self.stored_url, event.value)

    def _save_and_finish(self, api_base: str, api_key: str) -> None:
        # Set environment variable for this session
        os.environ["SCALEWAY_API_KEY"] = api_key
        #### KK-code altercation END ####

        try:
            _save_to_config_and_env(api_base, api_key)  #### KK-code altercation
        except OSError as err:
            self.app.exit(f"save_error:{err}")
            return
        self.app.exit("completed")

    def on_mouse_up(self, event: MouseUp) -> None:
        copy_selection_to_clipboard(self.app)
