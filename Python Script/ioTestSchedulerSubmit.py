#!/opt/ActivePython-2.7/bin/python

import time
import requests
import logging
import json
from concurrent import futures
from io import StringIO

# ----- Need change for deploy -----
SERVER_PROFILE_REQUEST_LINK = "http://192.168.153.181:8000/server_profile/"
# -----

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s');

class Server():
    """
    Server data class
    """
    
    def __init__(self, serverName, url, headers, profile={}, jobsInterval = 180):
        """Init.
        serverName: For loggin use.
        url: For HTTP call to VMware IO Analyzer.
        profile: For store each saved test profile, use on HTTP call, and need put {} at timestamp for further process.
        jobsInterval: Interval for each profile insert to VMware IO Analyzer. (default: 180 sec)
        
        """
        self.serverName = serverName
        self.url = url
        self.profile = profile
        self.jobsInterval = jobsInterval
        self.headers = headers
    
    def __str__(self):
        return "Server: {!r}, URL: {!r}, number of profiles: {!r}".format(self.serverName, self.url, len(self.profile))
        
    def __repr__(self):
        return str(self)
    
    # Copy from http://stackoverflow.com/questions/561486/how-to-convert-an-integer-to-the-shortest-url-safe-string-in-python then modify "BASE66_ALPHABET" -> "BASE64_ALPHABET" and value.
    def _hexahexacontadecimal_encode_int(self, n):
        """Convert Int to HEX. Hardcoded list of VMware IO Analyzer using char. Normally use for generate time
        n: Int to convert.
        
        """
        BASE64_ALPHABET = u"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789$_"
        BASE = len(BASE64_ALPHABET)
        if n == 0:
            return BASE64_ALPHABET[0].encode('ascii')
    
        r = StringIO()
        while n:
            n, t = divmod(n, BASE)
            r.write(BASE64_ALPHABET[t])
        return r.getvalue().encode('ascii')[::-1]
    
    def submitAllTestSchedule(self):
        """All test profile to VMware IO Analyzer scheduler.
        
        """
        nextRunTime = int(time.time()+60)
        
        for profileName, profileValue in self.profile.items():
            nextRunTimeCode = self._hexahexacontadecimal_encode_int(nextRunTime*1000)
            payload = profileValue.format(nextRunTimeCode)
            
            r=requests.post(self.url,data=payload, headers=self.headers)
            if r.content.startswith("//OK"):
                logging.info("Server {!r}, profile {!r}, submit OK.".format(self.serverName, profileName))
            else:
                logging.error("Server {!r}, profile {!r}, submit not success.".format(self.serverName, profileName))
                
            nextRunTime += self.jobsInterval

def getTestServersAndProfiles(serverProfileUrl):
    result = requests.get(serverProfileUrl)
    return json.loads(result.content)

if __name__ == '__main__':
    logging.info("Process start.")
    serverLists = []
    testServersConfig = getTestServersAndProfiles(SERVER_PROFILE_REQUEST_LINK)
    for server in testServersConfig:
        temp = Server(**server)
        serverLists.append(temp)
    
    logging.info("{} server(s) will process.".format(len(serverLists)))
    logging.debug("Server(s) info: {}".format("; ".join(map(str, serverLists))))
        
    with futures.ThreadPoolExecutor(max_workers=20) as executor:
        for server in serverLists:
            executor.submit(server.submitAllTestSchedule)
        
    logging.info("Process finished.")
    