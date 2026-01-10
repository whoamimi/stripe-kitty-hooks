# app/utils/setup.py
# Setup utilities for the Stripe Payment application

import os
import sys
import yaml
from pathlib import Path
from typing import Any, Literal
from dotenv import load_dotenv
from dataclasses import dataclass, field

# DEFAULT LOCAL DEV PATHS
DEFAULT_APP_ROOT_PATH = "stripe-payment"
DEFAULT_REL_FILE_PATH = f"{DEFAULT_APP_ROOT_PATH}/app/utils/setup.py"
DEFAULT_APP_HANDLER = "app"

# CURRENT WORKSPACE
REL_FILE_PATH = Path(__file__).resolve()
APP_ROOT_PATH = REL_FILE_PATH.parent.parent.parent if REL_FILE_PATH.as_posix().endswith(DEFAULT_REL_FILE_PATH) else REL_FILE_PATH.parent.parent
APP_PATH = APP_ROOT_PATH / DEFAULT_APP_HANDLER

if APP_ROOT_PATH.stem == DEFAULT_APP_ROOT_PATH:
    # local development environment
    if (APP_ROOT_PATH / ".env").exists():
        from dotenv import load_dotenv
        load_dotenv(".env")
        DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
    else:
        raise EnvironmentError(".env file not found in development environment. Current root directory: " + str(APP_ROOT_PATH))
else:
    print(f"Production environment detected. Using system environment variables. {APP_ROOT_PATH}. FILE CALLED FROM {REL_FILE_PATH}")
    DEV_MODE = False

DEV_ORIGINS = [
    "https://df4nm1m4-4000.aue.devtunnels.ms",
    "https://localhost:5173",
]

PROD_ORIGINS = [
    "https://tarot.mimeus.com",
    "https://tarotarot-ai.web.app",
]

@dataclass
class FirebaseConfig:
    url: str
    _service_account_path: Path

    def __post_init__(self):
        if not self._service_account_path.exists():
            raise ValueError(f"Firebase service account file not found at {self._service_account_path}")

@dataclass(frozen=True)
class StripeAccountConfig:
    api_key: str
    secret_key: str
    restricted_key: str
    webhook_secret: str | None = None
    publishable_key: str | None = None

@dataclass(frozen=True)
class StripeProductConfig:
    name: str
    product_id: str
    price: float
    price_id: str | None = None
    lookup_key: str | None = None
    add_count: int | None = None
    type: Literal["tokens", "saas"] = "tokens"

@dataclass(frozen=True)
class StripeAppConfig:
    apps: dict[str, Any]
    workspace: dict[str, Path]
    account: StripeAccountConfig
    database: FirebaseConfig
    cors: list[str] = field(default_factory=lambda: DEV_ORIGINS if DEV_MODE else PROD_ORIGINS)

def setup_directory(base_path: Path = APP_PATH, root_base_path: Path = APP_ROOT_PATH) -> dict:
    """Setup and return important file paths."""

    config = {}
    config["root_app_path"] = root_base_path
    config["app_path"] = base_path
    config["config_path"] = base_path / "config" / "prod" if not DEV_MODE else base_path / "config" / "dev"
    config["src_path"] = base_path / "src"
    config["api_path"] = base_path / "api"
    config["utils_path"] = base_path / "utils"

    for key, path in config.items():

        if path not in sys.path:
            print(f"Warning: Expected sub-path to exist in sys.path for {key}: {path}")
            sys.path.insert(0, str(path))

    return config

def setup_stripe_account() -> StripeAccountConfig:
    """Setup Stripe account configuration from environment variables."""

    secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    api_key = os.getenv("STRIPE_API_KEY", "")
    restricted_key = os.getenv("STRIPE_RESTRICTED_KEY", "")
    publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    if not all([secret_key, restricted_key]):
        raise RuntimeError(
            "Missing required Stripe configuration in environment variables. "
            "Please set STRIPE_SECRET_KEY and STRIPE_RESTRICTED_KEY. "
            f"Current values: STRIPE_SECRET_KEY={'set' if secret_key else 'MISSING'}, "
            f"STRIPE_RESTRICTED_KEY={'set' if restricted_key else 'MISSING'}"
        )

    return StripeAccountConfig(
        secret_key=secret_key,
        api_key=api_key,
        restricted_key=restricted_key,
        publishable_key=publishable_key,
        webhook_secret=webhook_secret,
    )


def setup_workspace():
    """Setup Stripe products configuration."""

    try:
        dir_path = setup_directory()
        apps = {}
        for file in dir_path["config_path"].glob("*.yml"):
            app_name = str(file.stem)

            apps[app_name] = {}
            with open(file, "r") as f:
                data = yaml.safe_load(f)
                if isinstance(data, list):
                    for idx, item in enumerate(data):
                        item_name = item.get("name", "unknown_product")
                        apps[app_name][item_name] = StripeProductConfig(
                            name=item_name,
                            product_id=item.get("product_id", ""),
                            price=item.get("price", 0.0),
                        )
                    print(f"Loading {idx + 1} Products for App: {app_name}")
                else:
                    raise ValueError(f"Invalid data format in {file}: expected a list of products.")

        acc = setup_stripe_account()
        fb = FirebaseConfig(
            url=os.getenv("GCP_FIREBASE_DATABASE_URL", ""),
            _service_account_path=dir_path["app_path"] / "config" / "_secrets" / "serviceAccount.json"
        )
        return StripeAppConfig(apps=apps, workspace=dir_path, account=acc, database=fb)

    except Exception as e:
        raise RuntimeError(f"Error Setting up workspace: Stripe products configuration: {e}")


print(f"SCRIPT CALLED FROM FILE: {REL_FILE_PATH}")
print(f"APP ROOT PATH: {APP_ROOT_PATH}\nAPP PATH: {APP_PATH}")
platform = setup_workspace()
