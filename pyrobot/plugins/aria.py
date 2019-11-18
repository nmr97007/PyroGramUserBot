#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# (c) Shrimadhav U K

# the logging things
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
LOGGER = logging.getLogger(__name__)

import os
import asyncio
import aria2p
from pyrogram import Client, Filters
from pyrobot import COMMAND_HAND_LER, TMP_DOWNLOAD_DIRECTORY


@Client.on_message(Filters.command("leech", COMMAND_HAND_LER)  & Filters.me)
async def incoming_message_f(client, message):
    """leech"""
    i_m_sefg = await message.edit_text("processing")
    # get link from the incoming message
    dl_url, cf_name = extract_link(message.reply_to_message)
    LOGGER.info(dl_url)
    LOGGER.info(cf_name)
    if dl_url is not None:
        await client.delete_messages(
                   chat_id=message.chat.id,
                   message_ids=message.reply_to_message.message_id,
                   revoke=True
         )
        await i_m_sefg.edit_text("extracting links")
        # start the aria2c daemon
        aria_i_p = await aria_start()
        LOGGER.info(aria_i_p)
        # create an unique directory
        new_download_location = os.path.join(
            TMP_DOWNLOAD_DIRECTORY
        )
        # create download directory, if not exist
        if not os.path.isdir(new_download_location):
            os.makedirs(new_download_location)
        await i_m_sefg.edit_text("trying to download")
        # try to download the "link"
        sagtus, err_message = await call_apropriate_function(
            aria_i_p,
            dl_url,
            new_download_location,
            i_m_sefg
        )
        if not sagtus:
            # if FAILED, display the error message
            await i_m_sefg.edit_text(err_message)
    else:
        await i_m_sefg.edit_text("Process Failed !")
        
        
#extrac_link
                
def extract_link(message):
    custom_file_name = None
    url = None
    if message is None:
        url = None
        custom_file_name = None
    elif "|" in message.text:
        url, custom_file_name = message.text.split("|")
        url = url.strip()
        custom_file_name = custom_file_name.strip()
    elif message.entities is not None:
        url = message.text
    return url, custom_file_name
   
#ariastart

async def aria_start():
    aria2_daemon_start_cmd = []
    # start the daemon, aria2c command
    aria2_daemon_start_cmd.append("aria2c")
    # aria2_daemon_start_cmd.append("--allow-overwrite=true")
    aria2_daemon_start_cmd.append("--daemon=true")
    # aria2_daemon_start_cmd.append(f"--dir={DOWNLOAD_LOCATION}")
    # TODO: this does not work, need to investigate this.
    # but for now, https://t.me/TrollVoiceBot?start=858
    aria2_daemon_start_cmd.append("--enable-rpc")
    aria2_daemon_start_cmd.append("--follow-torrent=mem")
    aria2_daemon_start_cmd.append("--max-connection-per-server=10")
    aria2_daemon_start_cmd.append("--min-split-size=10M")
    aria2_daemon_start_cmd.append("--rpc-listen-all=false")
    aria2_daemon_start_cmd.append(f"--rpc-listen-port=6800")
    aria2_daemon_start_cmd.append("--rpc-max-request-size=1024M")
    aria2_daemon_start_cmd.append("--seed-ratio=0.0")
    aria2_daemon_start_cmd.append("--seed-time=1")
    aria2_daemon_start_cmd.append("--split=10")
    aria2_daemon_start_cmd.append(f"--bt-stop-timeout=600")
    #
    LOGGER.info(aria2_daemon_start_cmd)
    #
    aria2_is_running = os.system(aria2_daemon_start_cmd)
    aria2 = aria2p.API(
        aria2p.Client(
            host="http://localhost",
            port="6800",
            secret=""
        )
    )
    return aria2  
   
#call_apropriate_function

async def call_apropriate_function(
    aria_instance,
    incoming_link,
    c_file_name,
    previous_message
):
    if incoming_link.startswith("magnet:"):
        sagtus, err_message = add_magnet(aria_instance, incoming_link, c_file_name)
    else:
        sagtus, err_message = add_url(aria_instance, incoming_link, c_file_name)
    if not sagtus:
        return sagtus, err_message
    LOGGER.info(err_message)
    # https://stackoverflow.com/a/58213653/4723940
    await check_progress_for_dl(
        aria_instance,
        err_message,
        sent_message_to_update_tg_p,
        None
    )
    if incoming_link.startswith("magnet:") or incoming_link.lower().endswith(".torrent"):
        #
        err_message = await check_metadata(aria_instance, err_message)
        #
        await asyncio.sleep(1)
        if err_message is not None:
            await check_progress_for_dl(
                aria_instance,
                err_message,
                sent_message_to_update_tg_p,
                None
            )
        else:
            return False, "can't get metadata \n\n#stopped"
    
    
#add_magnet

def add_magnet(aria_instance, magnetic_link, c_file_name):
    options = None
    # if c_file_name is not None:
    #     options = {
    #         "dir": c_file_name
    #     }
    try:
        download = aria_instance.add_magnet(
            magnetic_link,
            options=options
        )
    except Exception as e:
        return False, "**FAILED** \n" + str(e) + " \nPlease do not send SLOW links. Read /help"
    else:
        return True, "" + download.gid + ""

#addurl

def add_url(aria_instance, text_url, c_file_name):
    options = None
    # if c_file_name is not None:
    #     options = {
    #         "dir": c_file_name
    #     }
    uris = [text_url]
    # Add URL Into Queue
    try:
        download = aria_instance.add_uris(
            uris,
            options=options
        )
    except Exception as e:
        return False, "**FAILED** \n" + str(e) + " \nPlease do not send SLOW links. Read /help"
    else:
        return True, "" + download.gid + ""
        
#check_progress

async def check_progress_for_dl(aria2, gid, event, previous_message):
    try:
        file = aria2.get_download(gid)
        complete = file.is_complete
        if not complete:
            if not file.error_message:
                msg = ""
                # sometimes, this weird https://t.me/c/1220993104/392975
                # error creeps up
                # TODO: temporary workaround
                downloading_dir_name = "N/A"
                try:
                    downloading_dir_name = str(download.name)
                except:
                    pass
                #
                msg = f"\nDownloading File: `{downloading_dir_name}`"
                msg += f"\nSpeed: {file.download_speed_string()} 🔽 / {file.upload_speed_string()} 🔼"
                msg += f"\nProgress: {file.progress_string()}"
                msg += f"\nTotal Size: {file.total_length_string()}"
                # msg += f"\nStatus: {file.status}"
                msg += f"\nETA: {file.eta_string()}"
                # LOGGER.info(msg)
                if msg != previous_message:
                    await event.edit(msg)
                    previous_message = msg
            else:
                msg = file.error_message
                await event.edit(f"`{msg}`")
                return False
            await asyncio.sleep(6)
            await check_progress_for_dl(aria2, gid, event, previous_message)
        else:
            await event.edit(f"File Downloaded Successfully: `{file.name}`")
            return True
    except Exception as e:
        LOGGER.info(str(e))
        if " not found" in str(e) or "'file'" in str(e):
            await event.edit("Download Canceled :\n`{}`".format(file.name))
            return False
        elif " depth exceeded" in str(e):
            file.remove(force=True)
            await event.edit("Download Auto Canceled :\n`{}`\nYour Torrent/Link is Dead.".format(file.name))
            return False
        else:
            LOGGER.info(str(e))
            await event.edit("<u>error</u> :\n`{}` \n\n#error".format(str(e)))
            return                
                                
#checkmetadata

async def check_metadata(aria2, gid):
    file = aria2.get_download(gid)
    LOGGER.info(file)
    if not file.followed_by_ids:
        # https://t.me/c/1213160642/496
        return None
    new_gid = file.followed_by_ids[0]
    LOGGER.info("Changing GID " + gid + " to " + new_gid)
    return new_gid                                                                                                
