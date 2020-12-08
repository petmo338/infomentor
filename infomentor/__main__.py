import infomentor.flock as flock
import logging
import argparse
import datetime
import sys
import os
import requests
from infomentor import db, model, connector, informer, config

logformat = (
    "{asctime} - {name:25s}[{filename:20s}:{lineno:3d}] - {levelname:8s} - {message}"
)


def logtofile():
    from logging.handlers import RotatingFileHandler

    handler = RotatingFileHandler("log.txt", maxBytes=1024 * 1024, backupCount=10)
    logging.basicConfig(
        level=logging.INFO, format=logformat, handlers=[handler], style="{"
    )


def logtoconsole():
    logging.basicConfig(level=logging.DEBUG, format=logformat, style="{")


def parse_args(arglist):
    parser = argparse.ArgumentParser(description="Infomentor Grabber and Notifier")
    parser.add_argument(
        "--nolog", action="store_true", help="print log instead of logging to file"
    )
    parser.add_argument("--username", type=str, nargs="?", help="infomentor username")
    parser.add_argument("--password", type=str, nargs="?", help="infomentor password")
    parser.add_argument("--fake", action="store_true", help="add fake")
    parser.add_argument("--notifyerrors", action="store_true", help="add fake")
    parser.add_argument("--pushover", type=str, nargs="?", help="pushover user id")
    parser.add_argument("--mail", type=str, nargs="?", help="e-mail for notification")
    parser.add_argument(
        "--iclouduser", type=str, nargs="?", help="icloud calendar user"
    )
    parser.add_argument(
        "--icloudpwd", type=str, nargs="?", help="icloud calendar password"
    )
    parser.add_argument(
        "--icloudcalendar", type=str, nargs="?", help="icloud calendar calendar"
    )
    parser.add_argument(
        "--invitationmail", type=str, nargs="?", help="e-mail for notification"
    )
    args = parser.parse_args(arglist)
    return args


def perform_user_update(args):
    logger = logging.getLogger(__name__)
    username = args.username
    session = db.get_db()
    existing_user = (
        session.query(model.User).filter(model.User.name == username).one_or_none()
    )
    if existing_user is not None:
        logger.info("Updating user " + username)
    else:
        logger.info("Creating User user " + username)

    if args.password is None:
        logger.info("No password provided, asking for it")
        import getpass
        password = getpass.getpass(prompt="Password: ")
    else:
        password = args.password

    if existing_user is not None:
        user = existing_user
        user.password = password
    else:
        user = model.User(name=username, password=password)
        session.add(user)

    if args.notifyerrors:
        user.wantstatus = True
    else:
        user.wantstatus = False

    if args.pushover is not None:
        logger.info("Adding pushover notification")
        user.notification = model.Notification(
            ntype=model.Notification.Types.PUSHOVER, info=args.pushover
        )
    elif args.mail:
        logger.info("Adding email notification")
        user.notification = model.Notification(
            ntype=model.Notification.Types.EMAIL, info=args.mail
        )
    elif args.fake:
        logger.info("Adding fake notification")
        user.notification = model.Notification(
            ntype=model.Notification.Types.FAKE, info=""
        )

    if (
        args.iclouduser is not None
        and args.icloudpwd is not None
        and args.icloudcalendar is not None
    ):
        logger.info("Adding icloud calendar")
        user.icalendar = model.ICloudCalendar(
            icloud_user=args.iclouduser,
            password=args.icloudpwd,
            calendarname=args.icloudcalendar,
        )

    if args.invitationmail:
        logger.info("Activating sending of calendar entries per mail")
        user.invitation = model.Invitation(email=mail)

    session.commit()


def notify_users():
    logger = logging.getLogger(__name__)
    session = db.get_db()
    cfg = config.load()
    if cfg["healthcheck"]["url"] != "":
        logger.info("Triggering Healthcheck Start")
        requests.get(cfg["healthcheck"]["url"] + "/start")

    for user in session.query(model.User):
        logger.info("==== USER: %s =====", user.name)
        if user.password == "":
            logger.warning("User %s not enabled", user.name)
            continue
        now = datetime.datetime.now()
        im = connector.Infomentor(user.name)
        im.login(user.password)
        logger.info("User loggedin")
        statusinfo = {"datetime": now, "ok": False, "info": "", "degraded_count": 0}
        if user.apistatus is None:
            user.apistatus = model.ApiStatus(**statusinfo)
        logger.info("Former API status: %s", user.apistatus)
        try:
            i = informer.Informer(user, im, logger=logger)
            i.update_news()
            i.update_homework()
            i.update_calendar()
            statusinfo["ok"] = True
            statusinfo["degraded"] = False
        except Exception as e:
            inforstr = "Exception occured:\n{}:{}\n".format(type(e).__name__, e)
            statusinfo["ok"] = False
            statusinfo["info"] = inforstr
            logger.exception("Something went wrong")
        finally:
            if user.apistatus.ok == True and statusinfo["ok"] == False:
                logger.error("Switching to degraded state %s", user.name)
                statusinfo["degraded_count"] = 1
            if user.apistatus.ok == False and statusinfo["ok"] == False:
                if user.apistatus.degraded_count == 1 and user.wantstatus:
                    im.send_status_update(statusinfo["info"])
                try:
                    statusinfo["degraded_count"] = user.apistatus["degraded_count"] + 1
                except Exception as e:
                    statusinfo["degraded_count"] = 1
            if user.apistatus.ok == False and statusinfo["ok"] == True:
                statusinfo["info"] = "Works as expected, failed {} times".format(
                    user.apistatus.degraded_count
                )
                statusinfo["degraded_count"] = 0
                if user.wantstatus:
                    im.send_status_update(statusinfo["info"])
            user.apistatus.updateobj(statusinfo)
        logger.info("New API status: %s", user.apistatus)
        session.commit()

    if cfg["healthcheck"]["url"] != "":
        logger.info("Triggering Healthcheck Stop")
        requests.get(cfg["healthcheck"]["url"])


def main():
    # sys.argv.append('--username')
    # sys.argv.append('petmo338')
    
    args = parse_args(sys.argv[1:])
    if True:
        logtoconsole()
    else:
        logtofile()
    logger = logging.getLogger("Infomentor Notifier")
    logger.info("STARTING-------------------- %s", os.getpid())
    try:
        lock = flock.flock()
        if not lock.aquire():
            logger.info("EXITING - PREVIOUS IS STILL RUNNING")
            raise Exception()
        if args.username:
            perform_user_update(args)
        else:
            notify_users()
    except Exception as e:
        logger.info("Exceptional exit")
        logger.exception("Info")
    finally:
        logger.info("EXITING--------------------- %s", os.getpid())


if __name__ == "__main__":
    main()
