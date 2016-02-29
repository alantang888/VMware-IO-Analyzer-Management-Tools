#!/opt/ActivePython-2.7/bin/python

import os
import re
import sys
import logging
import time
import json
import requests
import shutil
from collections import namedtuple
from requests.exceptions import ConnectionError

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s')

# ----- Need change for deploy -----
UPLOAD_JSON_RESULT_URL="http://192.168.153.181:8000/result_upload/"
# -----

RESULT_BASE_DIRECTORY="/var/www/expts"

GUEST_VM_PATTERN = """^TimeStamp=(?P<report_time>.*)$
^GuestName=(?P<guestVmName>.*)$
^AccessSpec=(?P<test_spec>.*)$
^IOps=(?P<total_iops>.*)$
^ReadIOps=(?P<read_iops>.*)$
^WriteIOps=(?P<write_iops>.*)$"""

REPORT_DATETIME_PATTERN="(?P<report_time>\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})$"

LATENCY_DATA_PATTERN = "\d+\s+(?P<readLantency>\d+(?:\.\d+)?)\s+(?P<writeLantency>\d+(?:\.\d+)?)"

LAST_PROCESS_TIME_RECORD_FILE = "/root/lastProcessTime.txt"

guestVmPatternRegex = re.compile(GUEST_VM_PATTERN, re.M)
reportDatetimeRegex = re.compile(REPORT_DATETIME_PATTERN)
latencyDataRegex = re.compile(LATENCY_DATA_PATTERN)

def checkFileReadable(file):
    return os.path.isfile(file) and os.access(file, os.R_OK)

def readResultFromFolder(targetFolderName):
    # var declaration
    iopsResultFile = None
    iopsRawData = None
    latencyResultFile = None
    layencyRawData = None
    readLatency = []
    writeLatency = []
    
    # set test profile folder
    targetFolder=os.path.join(RESULT_BASE_DIRECTORY,targetFolderName)
    logging.info("Start process {!r}.".format(targetFolder))
    
    # set and check IOPS result file is exist and readable
    itemFullPath = os.path.join(targetFolder,"guestSummary.txt")
    if checkFileReadable(itemFullPath):
        iopsResultFile = itemFullPath
    else:
        logging.error("No IOPS results file found in {!r} directory. Or file not readable.".format(targetFolder))
        return None
    
    # read IOPS result
    try:
        with open(iopsResultFile,"r") as iopsReader:
            iopsRawData = iopsReader.read(-1)
    except Exception as e:
        logging.error("Read data file {!r} got error, error message: {!r}".format(iopsResultFile, e.message))
        sys.exit(2)
    
    # parse IOPS result by regex
    guestVmRegexResult = guestVmPatternRegex.search(iopsRawData)
    if guestVmRegexResult is None:
        logging.error("{!r} can't match IOPS result pattern.".format(iopsResultFile))
        return None
    
    total_iops = float(guestVmRegexResult.group("total_iops"))
    read_iops = float(guestVmRegexResult.group("read_iops"))
    write_iops = float(guestVmRegexResult.group("write_iops"))
    test_vm = guestVmRegexResult.group("guestVmName")
    #report_time = guestVmRegexResult.group("report_time")
    test_spec = guestVmRegexResult.group("test_spec")
    
    reportDatetimeResult = reportDatetimeRegex.search(os.path.basename(targetFolder))
    report_time = reportDatetimeResult.group("report_time")
    
    #convert report time to timestamp (Because the server's clock not using UTC+8, so just grep the printed time and convert to timestamp is easier to get the correct time.)
    report_time = time.mktime(time.strptime(report_time, "%Y-%m-%d_%H-%M-%S"))
    
    # set latency result folder and seek for latency result file
    targetFolder = os.path.join(targetFolder,"timeseries")
    for item in os.listdir(targetFolder):
        if item.startswith("timeseries-vm-") and item.endswith("{}-rwlatency".format(test_vm)):
            itemFullPath = os.path.join(targetFolder, item)
            if checkFileReadable(itemFullPath):
                latencyResultFile = itemFullPath
                break
            else:
                logging.error("{!r} file not readable.".format(latencyResultFile))
                sys.exit(2)
    if latencyResultFile is None:
        logging.error("No IOPS results file found in {!r} directory.".format(targetFolder))
        return None
    
    # read latency result
    try:
        with open(latencyResultFile, "r") as latencyReader:
            layencyRawData = latencyReader.read(-1)
    except Exception as e:
        logging.error("Read data file {!r} got error, error message: {!r}".format(latencyReader, e.message))
        sys.exit(2)
    
    # parse latency result by regex and parse to float.
    latencyRegexResult = latencyDataRegex.finditer(layencyRawData)
    for latency in latencyRegexResult:
        try:
            readLatency.append(float(latency.group("readLantency")))
            writeLatency.append(float(latency.group("writeLantency")))
        except ValueError as e:
            logging.error("Latency value can't convert to float, error message: {!r}".format(e.message))
            sys.exit(2)
    
    # check is regex success parse latency data
    if len(readLatency) == 0:
        logging.error("{!r} can't match latency result pattern.".format(latencyResultFile))
        sys.exit(2)
        
    min_read_latency = min(readLatency)
    max_read_latency = max(readLatency)
    avg_read_latency = sum(readLatency)/len(readLatency)
    
    min_write_latency = min(writeLatency)
    max_write_latency = max(writeLatency)
    avg_write_latency = sum(writeLatency)/len(writeLatency)
    
    result = {}
    for i in ("report_time", "test_vm", "test_spec", "total_iops", "read_iops", "write_iops", "min_read_latency", "max_read_latency", "avg_read_latency", "min_write_latency", "max_write_latency", "avg_write_latency"):
        result[i] = locals()[i]
    
    logging.debug("Report timestamp: {report_time}, VM: {test_vm}, testing spec: {test_spec}, total IOPS: {total_iops}, read IOPS: {read_iops}, write IOPS: {write_iops}, minRL: {min_read_latency}, maxRL: {max_read_latency}, avgRL: {avg_read_latency}, minWL: {min_write_latency}, maxWL: {max_write_latency}, avgWL: {avg_write_latency}".format(**locals()))
    
    return result

def getUnprocessedDir(lastProcessDirTime):
    # create data container class
    DirInfo = namedtuple("DirInfo", "name,ctime,mtime")
    
    # map dir info to data container class, and build a list
    baseDirItems = map(DirInfo._make,[(dir,os.stat(os.path.join(RESULT_BASE_DIRECTORY,dir)).st_ctime,os.stat(os.path.join(RESULT_BASE_DIRECTORY,dir)).st_mtime) for dir in os.listdir(RESULT_BASE_DIRECTORY) if os.path.isdir(os.path.join(RESULT_BASE_DIRECTORY,dir))])
    
    # sort dir info list by ctime
    baseDirItems.sort(key=lambda x:x.ctime)
    
    # get short list which after last run
    for i in xrange(len(baseDirItems)):
        if baseDirItems[i].ctime > lastProcessDirTime:
            baseDirItems = baseDirItems[i:]
            break
    # if no newer file found, return empty list
    else:
        return []
    
    return baseDirItems

def readLastProcessTimestamp():
    if not checkFileReadable(LAST_PROCESS_TIME_RECORD_FILE):
        logging.warning("Last process time record file {!r} not found or not readable, will process all.".format(LAST_PROCESS_TIME_RECORD_FILE))
        return 0
    
    try:
        with file(LAST_PROCESS_TIME_RECORD_FILE, "r") as timestampReader:
            rawText = timestampReader.readline()
        return float(rawText)
    except ValueError as e:
        logging.error("Last process time record file value can't convert to float, error message: {!r}".format(e.message))
        sys.exit(2)
    except Exception as e:
        logging.error("Read last process time record file {!r} got error, error message: {!r}".format(LAST_PROCESS_TIME_RECORD_FILE, e.message))
        sys.exit(2)

def writeLastProcessTimestamp(lastProcessDirTime):
    try:
        with file(LAST_PROCESS_TIME_RECORD_FILE, "w") as timestampWriter:
            timestampWriter.write("{}".format(lastProcessDirTime))
    except Exception as e:
        logging.error("Write last process time record to file {!r} got error, error message: {!r}".format(LAST_PROCESS_TIME_RECORD_FILE, e.message))
        sys.exit(2)

if __name__ == "__main__":
    logging.info("Program start")
    
    # get last process result timestamp, to filter out those result, which already processed.
    lastProcessDirTime = readLastProcessTimestamp()
    logging.debug("Last processed result time is {}".format(lastProcessDirTime))
    baseDirItems = getUnprocessedDir(lastProcessDirTime)
    
    # check if no folder need to processs, exit normally
    if len(baseDirItems) < 1:
        logging.info("No result directory need to process, program exit.")
        sys.exit(0)
    
    logging.info("Have {} result directory(s) will be process.".format(len(baseDirItems)))
    for dir in baseDirItems:
        # if directory create time less then current 1 min, wait until 1 min, prevent the result write not finished.
        while time.time() - dir.ctime < 60:
            logging.debug("Directory {} ctime less then current 60 seconds, sleep for 10 seconds.".format(dir.name))
            time.sleep(10)
        
        logging.debug("Will process result directory {}, which ctime is {}.".format(dir.name, dir.ctime))
        result = readResultFromFolder(dir.name)
        if result is None:
            shutil.rmtree(os.path.join(RESULT_BASE_DIRECTORY, dir.name))
            continue
        
        # upload result to server by json
        logging.info("Will upload result json to {}.".format(UPLOAD_JSON_RESULT_URL))
        logging.debug("Result json content: {!r}".format(result))
        upload_result = None
        try:
            upload_result = requests.post(UPLOAD_JSON_RESULT_URL, data=json.dumps(result))
        except ConnectionError as e:
            logging.error("Can't connect to server, program exit.")
            sys.exit(3)
        logging.debug("Upload result content: {!r}".format(upload_result.content))
        
        # if upload not success
        if not upload_result.ok and not upload_result.content == "OK":
            logging.error("Upload not success, program exit.")
            sys.exit(3)
            
        # if upload success, remove result directory
        shutil.rmtree(os.path.join(RESULT_BASE_DIRECTORY, dir.name))
        lastProcessDirTime = dir.ctime
    
    logging.info("Processed {} directory(s), last processed timestamp is {}.".format(len(baseDirItems),lastProcessDirTime))
    writeLastProcessTimestamp(lastProcessDirTime)