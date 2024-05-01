import asyncio
import importlib
import logging
from datetime import timedelta, datetime
import time
from croniter import croniter

from asgiref.server import StatelessServer

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from . import __version__

logger = logging.getLogger('taskserver')

TASK_MODULE = getattr(settings, 'TASK_MODULE', None)

# minimal time to sleep until next run
# in the case when elapsed time is greater than timedelta
MINIMAL_SLEEP_TIME = getattr(settings, 'MINIMAL_SLEEP_TIME', 0.1)


class TaskServer(StatelessServer):

    version = __version__

    def __init__(self, application, config, max_applications=1000):
        super().__init__(application, max_applications)
        # self.channel_layer = channel_layer
        # if self.channel_layer is None:
        #     raise ValueError("Channel layer is not valid")
        self._config = config

        if TASK_MODULE is None:
            raise ImproperlyConfigured('You must specify a TASK_MODULE variable in the settings')

        # процедура динамического импорта модулей с инициализацией клиента в модуле задач
        # тоже нельзя назвать асинхронной, поэтому лучше делать это в конструкторе,
        # т.к. расписание считывается один раз при старте сервера
        self._tasks = []
        for task_name, value in self._config.items():
            task_fn = None
            try:
                task_fn = getattr(importlib.import_module(f'{TASK_MODULE}.{task_name}'), 'task')
            except ModuleNotFoundError:
                logger.error(f'Module {TASK_MODULE} not found or can not be imported')
            except Exception as e:
                logger.error(f'Exception {e} while importing module {TASK_MODULE}.{task_name}')

            if not task_fn:
                raise ImproperlyConfigured(f'{task_name} not found in {TASK_MODULE} module or module import error')

            if isinstance(value, (list, tuple)):
                for v in value:
                    self._tasks.append(self.runner(task_fn, v))
            else:
                self._tasks.append(self.runner(task_fn, value))

    async def handle(self):
        """
        Runs all the provided tasks and handles the messages.
        """
        # For each channel, launch its own listening coroutine
        # listeners = []
        # for key in self.beat_config.keys():
        #     listeners.append(asyncio.ensure_future(self.listener(key)))

        # For each task configuration, launch its own run pattern

        # Wait for them all to exit
        # await asyncio.wait(tasks)
        # task_results = await asyncio.gather(*tasks, return_exceptions=True)
        # for t in task_results:
        #     print(f'TASK {t} was finished with result {t.result()}')

        for coroutine in asyncio.as_completed(self._tasks):
            try:
                await coroutine
            except Exception as e:
                logger.error('Got an exception:', e)
            else:
                logger.info('Success')

        # await asyncio.wait(listeners)

    async def runner(self, task_fn, value: dict):
        """
        Single task runner
        """
        logger.info(f'{value["type"]}: STARTED')
        while True:
            schedule = value["schedule"]
            task_kwargs = {}
            if 'params' in value.keys():
                task_kwargs = value.get('params')
            logger.debug(f'{value["type"]}: Task args: {task_kwargs}')
            if isinstance(schedule, timedelta):
                sleep_seconds = schedule.total_seconds()
            else:
                sleep_seconds = croniter(schedule).next() - time.time()
            logger.info(f'{value["type"]} next run in {sleep_seconds}s')
            task_kwargs['sleep_time'] = sleep_seconds

            t_start = time.perf_counter()

            try:
                await task_fn(value["type"], **task_kwargs)
            except Exception as e:
                # raise Exception(f'Error occurred while running {value["type"]}. Error was {e}')
                logger.error(f'Error occurred while running {value["type"]}. Error was: {e}')
            finally:
                t_end = time.perf_counter()
                time_elapsed = round((t_end - t_start) * 1000) / 1000

            next_run = max(sleep_seconds - time_elapsed, MINIMAL_SLEEP_TIME)
            logger.info(f"{value['type']} COMPLETED in: {time_elapsed} c. Next run in {next_run} s")
            # await self.channel_layer.send(
            #     key, {"type": value["type"], "message": value["message"]}
            # )

            await asyncio.sleep(next_run)
