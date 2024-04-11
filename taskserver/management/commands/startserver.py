import logging

from django.core.management import BaseCommand, CommandError
from django.conf import settings
# from channels import DEFAULT_CHANNEL_LAYER
# from channels.layers import get_channel_layer
from channels.routing import get_default_application
# from channels.worker import Worker
from taskserver.server import TaskServer

logger = logging.getLogger("taskserver")


class Command(BaseCommand):

    leave_locale_alone = True
    worker_class = TaskServer

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        # parser.add_argument(
        #     "--layer",
        #     action="store",
        #     dest="layer",
        #     default=DEFAULT_CHANNEL_LAYER,
        #     help="Channel layer alias to use, if not the default.",
        # )
        # parser.add_argument("channels", nargs="+", help="Channels to listen on.")

    def handle(self, *args, **options):
        # Get the backend to use
        self.verbosity = options.get("verbosity", 1)
        # Get the channel layer they asked for (or see if one isn't configured)
        # if "layer" in options:
        #     self.channel_layer = get_channel_layer(options["layer"])
        # else:
        #     self.channel_layer = get_channel_layer()
        # if self.channel_layer is None:
        #     raise CommandError("You do not have any CHANNEL_LAYERS configured.")

        config = getattr(settings, 'TASK_SCHEDULE', None)
        if config is None:
            raise CommandError("You do not have any TASK_SCHEDULE configured.")
        # Run the worker

        logger.info("Start TaskServer %s with conf %s", self.worker_class.version, config)
        worker = self.worker_class(
            application=get_default_application(),
            config=config,
            # channels=options["channels"],
            # channel_layer=self.channel_layer,
        )
        worker.run()
