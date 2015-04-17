
# This file is part of gwip.
#
# This work is licensed under the Creative Commons Attribution-NonCommercial
# 4.0 International License. To view a copy of this license, visit
# http://creativecommons.org/licenses/by-nc/4.0/ or send a letter to Creative
# Commons, PO Box 1866, Mountain View, CA 94042, USA.


import os
import logging
import sqlite3
from datetime import datetime


__author__ = "Louis-Philippe Lemieux Perreault"
__copyright__ = "Copyright 2014, Beaulieu-Saucier Pharmacogenomics Centre"
__license__ = "Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)"


__all__ = ["create_task_db", "check_task_completion", "create_task_entry",
           "mark_task_completed", "mark_task_incomplete", "get_task_runtime",
           "get_all_runtimes", "mark_drmaa_task_completed"]


def create_task_db(out_dir):
    """Creates a task DB.

    :param out_dir: the directory where the DB will be saved
    :type out_dir: str

    :returns: the name of the file containing the DB
    :rtype: str

    A SQLITE database will be created in the ``out_dir`` directory (with the
    name ``tasks.db``. The ``gwip_task`` table is automatically created.

    """
    # The name
    db_name = os.path.join(out_dir, "tasks.db")
    logging.info("Connecting to DB '{}'".format(db_name))

    # The DB
    conn, c = _create_db_connection(db_name)

    # Creating the table if it doesn't exists
    c.execute("""CREATE TABLE IF NOT EXISTS gwip_task (
                    name TEXT PRIMARY KEY,
                    launch TIMESTAMP,
                    start TIMESTAMP,
                    end TIMESTAMP,
                    completed INT)""")

    # Committing the changes
    conn.commit()
    conn.close()

    return db_name


def _create_db_connection(db_name):
    """Creates a DB connection.

    :param db_name: the name of the database (usually a file)
    :type db_name: str

    :returns: a tuple containing the connection object and a cursor to that
              object
    :rtype: tuple

    """
    conn = sqlite3.connect(
        db_name,
        timeout=360,
        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
    )
    c = conn.cursor()

    return conn, c


def check_task_completion(task_id, db_name):
    """Checks if the task exists and if it's completed.

    :param task_id: the ID of the task
    :param db_name: the name of the database (usually a file)

    :type task_id: str
    :param db_name: str

    :returns: ``True`` if the task exists **and** is completed, ``False``
              otherwise
    :rtype: boolean

    .. note::

        A task is completed if the column ``completed`` equals 1. It is not
        completed otherwise.

    """
    conn, c = _create_db_connection(db_name)

    # Retrieving the task information
    c.execute("SELECT completed FROM gwip_task WHERE name=?", (task_id, ))
    r = c.fetchone()

    conn.close()

    if r is None:
        # There is not entry with this task ID
        logging.debug("'{}' no entry".format(task_id))
        return False

    if r[0] is None or r[0] != 1:
        # There is an entry, but it wasn't completed
        logging.debug("'{}' not completed ({})".format(task_id, r[0]))
        return False

    return True


def create_task_entry(task_id, db_name):
    """Creates (or updates) a task.

    :param task_id: the ID of the task
    :param db_name: the name of the database (usually a file)

    :type task_id: str
    :type db_name: str

    If the task ID doesn't exist in the DB, a new one will be created with the
    current time as launch and start time.

    If the task ID already exist, it is presumed that the task will be
    relaunched, hence the database entry is updated to the current time (for
    launch and start time) and ``completed`` is set to ``0``.

    """
    conn, c = _create_db_connection(db_name)

    # Checking if the entry already exists
    c.execute("SELECT name FROM gwip_task WHERE name=?", (task_id, ))
    r = c.fetchone()

    # The time of launch
    time = datetime.now()

    if r is None:
        # This is the first time we see this task, so we create an new entry
        c.execute("INSERT INTO gwip_task (name, launch, start) "
                  "VALUES (?, ?, ?)",
                  (task_id, time, time))

    else:
        # We saw this task, but we need to relaunch it (setting completed=0)
        c.execute("UPDATE gwip_task "
                  "SET launch=?, start=?, completed=0 WHERE name=?",
                  (time, time, task_id))

    conn.commit()
    conn.close()


def mark_task_completed(task_id, db_name):
    """Marks the task as completed.

    :param task_id: the ID of the task
    :param db_name: the name of the DB (usually a file)

    :type task_id: str
    :type db_name: str

    The task entry is modified so that ``completed=1`` and the end time is
    updated to the current time.

    """
    conn, c = _create_db_connection(db_name)

    # Updating the end time
    c.execute("UPDATE gwip_task SET end=?, completed=1 WHERE name=?",
              (datetime.now(), task_id))

    conn.commit()
    conn.close()


def mark_task_incomplete(task_id, db_name):
    """Marks a task as incomplete.

    :param task_id: the ID of the task
    :param db_name: the name of the DB (usually a file)

    :type task_id: str
    :type db_name: str

    The task entry is set as incomplete by updating the ``completed`` value to
    ``0``.

    """
    conn, c = _create_db_connection(db_name)

    # Setting the completion to 0 for this task
    c.execute("UPDATE gwip_task SET completed=0 WHERE name=?", (task_id, ))

    conn.commit()
    conn.close()


def mark_drmaa_task_completed(task_id, launch_time, start_time, end_time,
                              db_name):
    """Marks a task run by DRMAA as completed (while updating times).

    :param task_id: the ID of the task
    :param launch_time: the launch time (according to DRMAA)
    :param start_time: the start time (according to DRMAA)
    :param end_time: the end time (according to DRMAA)
    :param db_name: the name of the DB (usually a file)

    :type task_id: str
    :type launch_time: float
    :type start_time: float 
    :type end_time: float
    :type db_name: str

    The task entry is updated with the launch, start and end time. Those times
    come from the DRMAA library. The launch time is the time at which the task
    was launched to the scheduler. The start time correspond to the time that
    the scheduler started the job on the cluster. Finally, the end time is the
    time that the job was completed.

    """
    conn, c = _create_db_connection(db_name)

    # The time
    launch_time = datetime.fromtimestamp(launch_time)
    start_time = datetime.fromtimestamp(start_time)
    end_time = datetime.fromtimestamp(end_time)

    # Updating
    c.execute("UPDATE gwip_task SET launch=?, start=?, end=?, completed=1 "
              "WHERE name=?", (launch_time, start_time, end_time, task_id))

    conn.commit()
    conn.close()


def get_task_runtime(task_id, db_name):
    """Gets the task run time.

    :param task_id: the ID of the task
    :param db_name: the name of the DB (usually a file)

    :type task_id: str
    :tupe db_name: str

    :returns: the execution time of the task (in seconds)
    :rtype: int

    """
    conn, c = _create_db_connection(db_name)

    # Getting the start and end time
    c.execute("SELECT start, end FROM gwip_task WHERE name=?", (task_id, ))
    r = c.fetchone()

    conn.close()

    return int(round((r[1] - r[0]).total_seconds(), ndigits=0))


def get_all_runtimes(db_name):
    """Gets all tasks execution time.

    :param db_name: the name of the DB (usually a file)
    :type db_name: str

    :returns: the execution time (seconds) of all the tasks in the database
    :rtype: dict

    This function returns a dictionary of task ID (keys) pointing to execution
    time (in second) (int).

    """
    conn, c = _create_db_connection(db_name)

    # Getting the start and end time
    c.execute("SELECT name, start, end FROM gwip_task")
    r = c.fetchall()

    conn.close()

    # Computing the execution time
    return {
        i[0]: int(round((i[2] - i[1]).total_seconds(), ndigits=0)) for i in r
    }
