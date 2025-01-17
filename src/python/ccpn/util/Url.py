"""Utilities for Url handling
"""
#=========================================================================================
# Licence, Reference and Credits
#=========================================================================================
__copyright__ = "Copyright (C) CCPN project (http://www.ccpn.ac.uk) 2014 - 2020"
__credits__ = ("Ed Brooksbank, Luca Mureddu, Timothy J Ragan & Geerten W Vuister")
__licence__ = ("CCPN licence. See http://www.ccpn.ac.uk/v3-software/downloads/license")
__reference__ = ("Skinner, S.P., Fogh, R.H., Boucher, W., Ragan, T.J., Mureddu, L.G., & Vuister, G.W.",
                 "CcpNmr AnalysisAssign: a flexible platform for integrated NMR analysis",
                 "J.Biomol.Nmr (2016), 66, 111-124, http://doi.org/10.1007/s10858-016-0060-y")
#=========================================================================================
# Last code modification
#=========================================================================================
__modifiedBy__ = "$modifiedBy: Ed Brooksbank $"
__dateModified__ = "$dateModified: 2020-01-13 10:38:51 +0000 (Mon, January 13, 2020) $"
__version__ = "$Revision: 3.0.0 $"
#=========================================================================================
# Created
#=========================================================================================
__author__ = "$Author: CCPN $"
__date__ = "$Date: 2017-04-07 10:28:41 +0000 (Fri, April 07, 2017) $"
#=========================================================================================
# Start of code
#=========================================================================================

BAD_DOWNLOAD = 'Exception: '


def fetchHttpResponse(method, url, data=None, headers=None, proxySettings=None):
    """Generate an http, and return the response
    """
    import os
    import ssl
    import certifi
    import urllib
    from urllib.request import getproxies
    import urllib3.contrib.pyopenssl
    from urllib.parse import urlencode, quote

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    if not headers:
        headers = {'Content-type': 'application/x-www-form-urlencoded;charset=UTF-8'}
    body = urlencode(data, quote_via=quote).encode('utf-8') if data else None

    urllib3.contrib.pyopenssl.inject_into_urllib3()

    # create the options list for creating an http connection
    options = {'cert_reqs': 'CERT_REQUIRED',
               'ca_certs' : certifi.where(),
               'timeout'  : urllib3.Timeout(connect=3.0, read=3.0),
               'retries'  : urllib3.Retry(1, redirect=False)
               }

    # check whether a proxy is required
    from ccpn.util.UserPreferences import UserPreferences, USEPROXY, USEPROXYPASSWORD, PROXYADDRESS, \
        PROXYPORT, PROXYUSERNAME, PROXYPASSWORD, USESYSTEMPROXY

    def _getProxyIn(proxyDict):
        """Get the first occurrence of a proxy type in the supplied dict
        """
        # define a list of proxy identifiers
        proxyCheckList = ['HTTPS_PROXY', 'https', 'HTTP_PROXY', 'http']
        for pCheck in proxyCheckList:
            proxyUrl = proxyDict.get(pCheck, None)
            if proxyUrl:
                return proxyUrl

    if proxySettings and proxySettings.get(USEPROXY):

        # Use the user settings if set
        useProxyPassword = proxySettings.get(USEPROXYPASSWORD)
        proxyAddress = proxySettings.get(PROXYADDRESS)
        proxyPort = proxySettings.get(PROXYPORT)
        proxyUsername = proxySettings.get(PROXYUSERNAME)
        proxyPassword = proxySettings.get(PROXYPASSWORD)

        if useProxyPassword:
            # grab the decode from the userPreferences
            _userPreferences = UserPreferences(readPreferences=False)

            options.update({'headers': urllib3.make_headers(proxy_basic_auth='%s:%s' %
                                                                             (proxyUsername,
                                                                              _userPreferences.decodeValue(proxyPassword)))})

        proxyUrl = "http://%s:%s/" % (str(proxyAddress), str(proxyPort)) if proxyAddress else None

    else:
        # read the environment/system proxies if exist
        proxyUrl = _getProxyIn(os.environ) or _getProxyIn(urllib.request.getproxies())

        # ED: issues - @"HTTPProxyAuthenticated" key on system?. If it exists, the value is a boolean (NSNumber) indicating whether or not the proxy is authentified,
        # get the username if the proxy is authenticated: check @"HTTPProxyUsername"

    # proxy may still not be defined
    if proxyUrl:
        http = urllib3.ProxyManager(proxyUrl, **options)
    else:
        http = urllib3.PoolManager(**options)

    # generate an http request
    response = http.request(method, url,
                            headers=headers,
                            body=body,
                            preload_content=False)

    # return the http response
    return response


def fetchUrl(url, data=None, headers=None, timeout=2.0, proxySettings=None, decodeResponse=True):
    """Fetch url request from the server
    """
    import logging

    urllib3_logger = logging.getLogger('urllib3')
    urllib3_logger.setLevel(logging.CRITICAL)

    if not proxySettings:

        # read the proxySettings from the preferences
        from ccpn.util.UserPreferences import UserPreferences

        _userPreferences = UserPreferences(readPreferences=True)
        if _userPreferences.proxyDefined:
            proxyNames = ['useProxy', 'proxyAddress', 'proxyPort', 'useProxyPassword',
                          'proxyUsername', 'proxyPassword']
            proxySettings = {}
            for name in proxyNames:
                proxySettings[name] = _userPreferences._getPreferencesParameter(name)

    response = fetchHttpResponse('POST', url, data=data, headers=headers, proxySettings=proxySettings)

    # if response:
    #     ll = len(response.data)
    #     print('>>>>>>responseUrl', proxySettings, response.data[0:min(ll, 20)])

    return response.data.decode('utf-8') if decodeResponse else response


def uploadFile(url, fileName, data=None):
    import os

    if not data:
        data = {}

    with open(fileName, 'rb') as fp:
        fileData = fp.read()

    data['fileName'] = os.path.basename(fileName)
    data['fileData'] = fileData

    try:
        return fetchUrl(url, data)
    except:
        return None


def checkInternetConnection():
    """Check whether an internet conection is available by testing the CCPN weblink
    """
    from ccpn.framework.PathsAndUrls import ccpnUrl

    try:
        fetchUrl('/'.join([ccpnUrl, 'cgi-bin/checkInternet']))
        return True

    except Exception as es:
        return False
