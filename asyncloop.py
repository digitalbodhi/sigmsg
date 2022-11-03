import asyncio
import logging
from logging.handlers import RotatingFileHandler
import signal
import sys
import traceback

class AsyncLoop:
    LVL_STR = {
        logging.DEBUG: 'DBG',
        logging.INFO: 'INFO',
        logging.WARNING: 'WARN',
        logging.ERROR: 'ERR',
        logging.CRITICAL: 'CRIT',
        }

    def __init__(self, id='asyncloop', log_levels=[logging.NOTSET]):
        self.id = id
        self.lgr = logging.getLogger(id)
        # by default log everything
        if(log_levels[0] == logging.NOTSET):
            self.lgr.setLevel(logging.DEBUG)
        for log_level in log_levels:
            self.setup_logger(log_level)
        self.loop = asyncio.get_event_loop()
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            self.loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(self.shutdown(s)))

        self.loop.set_exception_handler(self.custom_exception_handler)
        self.tasks = []

    def setup_logger(self, log_level, mb_limit=10, log_limit=10):
        log_format = "%(asctime)s %(levelname)s [%(name)s.%(funcName)s()] %(message)s [%(filename)s:%(lineno)d]"
        formatter = logging.Formatter(log_format)

        if(log_level == logging.NOTSET):
            # outputs err to stdout
            handler = logging.StreamHandler(sys.stdout)
            log_level = logging.DEBUG
        else:
            path = self.id+'_'+self.LVL_STR[log_level]+'.log'

            handler = RotatingFileHandler(
                path,
                maxBytes=mb_limit*1024*1024,
                backupCount=log_limit)

        handler.setLevel(log_level)
        handler.setFormatter(formatter)
        self.lgr.addHandler(handler)

    async def shutdown(self, signal=None):
        sig_name = 'request to shutdown'
        if(signal):
            sig_name = signal.name
        self.lgr.debug(f"Received {sig_name}, attempting to exit gracefullly")

        tasks = [t for t in asyncio.all_tasks() if t is not
                 asyncio.current_task() and not t.done() and not t.cancelled()]

        [task.cancel() for task in tasks]

        self.lgr.debug(f"Cancelling {len(tasks)} outstanding tasks")
        await asyncio.gather(*tasks, return_exceptions=True)
        self.loop.stop()

    def custom_exception_handler(self, loop, context):

        exception = context.get("exception", context["message"])
        loop.default_exception_handler(context)

        self.lgr.error(f'unhandled exception: {type(exception).__name__}: {exception}')
        if isinstance(exception, ConnectionError):
            self.lgr.error('connection error, shutting down')
            asyncio.create_task(self.shutdown())
        elif isinstance(exception, asyncio.InvalidStateError):
            self.lgr.error('invalid state, shutting down')
            asyncio.create_task(self.shutdown())
        else:
            self.lgr.error(f'unhandled exception: {exception} {traceback.format_exc()}')

    def run_loop(self):
        try:
            for task in self.tasks:
                if(type(task) == dict):
                    self.loop.create_task(task['func'](*task['args']))
                else:
                    self.loop.create_task(task())
            self.loop.run_forever()
        finally:
            self.loop.close()

# async def testfunc(cls, a, b, c):
#     while True:
#         cls.lgr.debug(a)
#         await asyncio.sleep(1);
#         cls.lgr.info(b)
#         await asyncio.sleep(1);
#         cls.lgr.error(c)
#         await asyncio.sleep(1);

# def main():
#     al = AsyncLoop('test_module')
#     tasks = [{'func':testfunc, 'args':[al, 1, 2, 3]}]
#     al.run_forever(tasks)

# if __name__ == '__main__':
#     main()
