from django.core.management.base import BaseCommand

from apps.orders.services.order_service import expire_unpaid_orders, get_expirable_unpaid_orders


class Command(BaseCommand):
    help = "Cancel expired unpaid orders and release reserved stock."

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=None,
            help="Expire awaiting-payment orders older than this many minutes.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many orders would expire without changing data.",
        )

    def handle(self, *args, **options):
        minutes = options.get("minutes")
        if minutes is not None and minutes <= 0:
            self.stderr.write(self.style.ERROR("--minutes must be greater than zero."))
            return

        if options["dry_run"]:
            count = get_expirable_unpaid_orders(older_than_minutes=minutes).count()
            self.stdout.write(f"{count} unpaid order(s) would expire.")
            return

        count = expire_unpaid_orders(older_than_minutes=minutes)
        self.stdout.write(self.style.SUCCESS(f"Expired {count} unpaid order(s)."))
