"""
(*)~---------------------------------------------------------------------------
Pupil - eye tracking platform
Copyright (C) 2012-2019 Pupil Labs

Distributed under the terms of the GNU
Lesser General Public License (LGPL v3.0).
See COPYING and COPYING.LESSER for license details.
---------------------------------------------------------------------------~(*)
"""
import os
import sys
import getpass
import platform
import logging


logger = logging.getLogger(__name__)


def get_system_info():
    try:
        if platform.system() == "Windows":
            username = os.environ["USERNAME"]
            sysname, nodename, release, version, machine, _ = platform.uname()
        else:
            username = getpass.getuser()
            sysname, nodename, release, version, machine = os.uname()
    except Exception as e:
        logger.error(e)
        username = "unknown"
        sysname, nodename, release, version, machine = (
            sys.platform,
            "unknown",
            "unknown",
            "unknown",
            "unknown",
        )

    info_str = "User: {}, Platform: {}, Machine: {}, Release: {}, Version: {}"

    return info_str.format(username, sysname, nodename, release, version)
