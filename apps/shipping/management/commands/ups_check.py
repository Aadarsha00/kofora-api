from django.conf import settings
from django.core.management.base import BaseCommand

from apps.shipping.services.ups_client import UPSError, get_access_token, is_sandbox, ups_request

# A token proves the app exists; it does not prove any API product is attached.
# Tracking is non-billable in both environments, so it is a safe entitlement probe.
PROBE_PATH = "/api/track/v1/details/1Z5338FF0107346023"
NOT_ENTITLED_CODE = "250002"


class Command(BaseCommand):
    help = "Verify UPS credentials, environment, and API product entitlement."

    def handle(self, *args, **options):
        self.stdout.write(f"UPS_MODE     : {settings.UPS_MODE}")
        self.stdout.write(f"UPS_BASE_URL : {settings.UPS_BASE_URL}")

        if is_sandbox():
            self.stdout.write(self.style.SUCCESS("environment  : SANDBOX (never billable)"))
        else:
            self.stdout.write(self.style.WARNING("environment  : PRODUCTION (shipments are billable)"))

        client_id = settings.UPS_CLIENT_ID
        self.stdout.write(f"client id    : {'set (%d chars)' % len(client_id) if client_id else 'MISSING'}")
        self.stdout.write(
            f"account no.  : {settings.UPS_ACCOUNT_NUMBER or 'not set (published rates only)'}"
        )

        try:
            token = get_access_token(force_refresh=True)
        except UPSError as exc:
            self.stdout.write(self.style.ERROR(f"auth         : FAILED - {exc}"))
            return

        self.stdout.write(self.style.SUCCESS(f"auth         : OK (token {token[:8]}...)"))

        try:
            ups_request("GET", PROBE_PATH, params={"locale": "en_US"})
        except UPSError as exc:
            if NOT_ENTITLED_CODE in str(exc):
                self.stdout.write(
                    self.style.ERROR(
                        "entitlement  : FAILED - the app authenticates but no API product is "
                        "attached. Add Rating, Tracking and Address Validation to the app at "
                        "developer.ups.com."
                    )
                )
                return
            # Any other error means the product answered, which is what we are testing.
            self.stdout.write(self.style.SUCCESS(f"entitlement  : OK (probe returned: {exc})"))
            return

        self.stdout.write(self.style.SUCCESS("entitlement  : OK"))
