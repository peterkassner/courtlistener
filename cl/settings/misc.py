import os
from datetime import date

import environ

from .django import INSTALL_ROOT

env = environ.FileAwareEnv()
DEVELOPMENT = env.bool("DEVELOPMENT", default=True)

# Plausible Analytics token (used for reporting API)
PLAUSIBLE_API_URL = "https://plausible.io/api/v1/stats/breakdown"
PLAUSIBLE_API_TOKEN = env("PLAUSIBLE_API_TOKEN", default="")


###################
#     Private     #
###################
# PACER
PACER_USERNAME = env("PACER_USERNAME", default="")
PACER_PASSWORD = env("PACER_PASSWORD", default="")

# Internet Archive
# See: https://archive.org/details/uscourtsoralargumentsdev
IA_ACCESS_KEY = env("IA_ACCESS_KEY", default="")
IA_SECRET_KEY = env("IA_SECRET_KEY", default="")
IA_COLLECTIONS: list[str] = env(
    "IA_COLLECTIONS",
    default=["usfederalcourtsdev"],
)
IA_OA_COLLECTIONS: list[str] = env(
    "IA_OA_COLLECTIONS",
    default=["uscourtsoralargumentsdev"],
)

# LASC
LASC_USERNAME = env("LASC_USERNAME", default="")
LASC_PASSWORD = env("LASC_PASSWORD", default="")

# Google auth
here = os.path.dirname(os.path.realpath(__file__))
GOOGLE_AUTH = {
    "PATH": os.path.join(here, "google_auth.json"),
    "PROJECT": "courtlistener-development",
}


##############
# Super Misc #
##############
FUNDRAISING_MODE = env("FUNDRAISING_MODE", default=False)

# Key for Follow the Money API
FTM_KEY = env("FTM_KEY", default="")
FTM_LAST_UPDATED = env("FTM_LAST_UPDATED", default=date.today())

#####################
# Research sync     #
#####################
# Personal sync layer (`cl.research_sync`): calls remote CourtListener API.
RESEARCH_SYNC = {
    "REMOTE_API_BASE_URL": env(
        "RESEARCH_SYNC_REMOTE_API_BASE_URL",
        default="https://www.courtlistener.com",
    ),
    "REMOTE_API_TOKEN": env("RESEARCH_SYNC_REMOTE_API_TOKEN", default=""),
    "REMOTE_API_TIMEOUT": env.int("RESEARCH_SYNC_REMOTE_API_TIMEOUT", default=60),
    "REMOTE_STORAGE_URL_PREFIX": env(
        "RESEARCH_SYNC_REMOTE_STORAGE_URL_PREFIX",
        default="https://storage.courtlistener.com/",
    ),
}
