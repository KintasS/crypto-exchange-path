import time
import datetime
from crypto_exchange_path import db
from crypto_exchange_path.models import Task
from crypto_exchange_path.utils import set_logger
from crypto_exchange_path.info_fetcher import update_prices

# Start logging
logger = set_logger('Daemon', 'INFO')


def run_task(task):
    """Runs tasks in background.
    """
    # Change Status
    init_time = datetime.datetime.now()
    task.status = 'Running'
    task.start_time = init_time
    db.session.commit()
    # Run process
    ret = None
    if task.name == 'update_prices':
        # Set next update task for 1 hour latter
        next_run = datetime.datetime.now() + datetime.timedelta(hours=1)
        add_task('update_prices', None, next_run)
        # Run 'update_prices' task
        ret = update_prices(logger)
    # Change task status and exit
    task.status = 'OK'
    task.finish_time = datetime.datetime.now()
    task.return_info = ret
    db.session.commit()
    return


def add_task(name, user_id=None, not_before_time=None):
    """Add tasks to the queue of tasks to be executed by the daemon in
    background.
    """
    # Only add task if it is not already queued
    add_task = False
    db_task = Task.query.filter_by(name=name,
                                   status='Pending',
                                   user_id=user_id).first()
    if db_task:
        if not_before_time is None:
            db_task.status = 'Overtaken'
            add_task = True
        elif ((db_task.not_before_time is not None) and
              (not_before_time < db_task.not_before_time)):
            db_task.status = 'Overtaken'
            add_task = True
        db.session.commit()
    if (db_task is None) or (add_task is True):
        now = datetime.datetime.now()
        task = Task(request_time=now,
                    name=name,
                    status='Pending',
                    not_before_time=not_before_time,
                    start_time=None,
                    finish_time=None,
                    user_id=user_id,
                    return_info=None)
        db.session.add(task)
        db.session.commit()


# Clear pending and running tasks that did not finish
tasks = Task.query.filter_by(status='Pending')
for task in tasks:
    task.status = 'Cancelled'
tasks = Task.query.filter_by(status='Running')
for task in tasks:
    task.status = 'Cancelled'
db.session.commit()

# Add 'update_prices' and start
add_task('update_prices')

# Deamon loop
iteration = 1
while True:
    logger.info("\n\nStarting iteration '{}'".format(iteration))
    now = datetime.datetime.now()
    tasks = Task.query.filter_by(status='Pending')
    idle_daemon = True
    for task in tasks:
        if (task.not_before_time is None) or (now > task.not_before_time):
            logger.info("daemon: Starting task: '{}''".format(task))
            run_task(task)
            logger.info("daemon: Finished task: '{}''".format(task))
            idle_daemon = False
    if idle_daemon:
        logger.info("No tasks to run. Going back to sleep...")
    else:
        logger.info("No more tasks to run. Going back to sleep...")
    iteration += 1
    time.sleep(900)
