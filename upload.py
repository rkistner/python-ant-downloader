#!/usr/bin/env python2

import cookielib,glob,json,mimetypes,mimetools,\
    re,os,os.path,sys,urllib,urllib2,webbrowser

class GarminError(Exception): pass

class GarminUploader(object):

    LOGIN_URL="https://connect.garmin.com/signin"
    UPLOAD_URL="http://connect.garmin.com/proxy/upload-service-1.1/json/upload/.fit"
    ACTIVITY_URL="http://connect.garmin.com/activity/%d"

    def __init__(self,debug=False):
        self.cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPHandler(debuglevel=debug),
            urllib2.HTTPCookieProcessor(self.cj))

    def login(self,username,password):
        login_page = self.opener.open(self.LOGIN_URL).read()
        action,form = extract_forms(login_page)['login']
        form['login:loginUsernameField'] = username
        form['login:password'] = password
        data = urllib.urlencode(form)
        response = self.opener.open(self.LOGIN_URL,data)
        if response.url == self.LOGIN_URL:
            raise GarminError("Login Error")
        else:
            self.loggedIn = True
            self.dashboardURL = response.url

    def upload(self,name,data):
        if not self.loggedIn:
            raise GarminError("Not Logged In")
        fields = (('responseContentType','text/html'),)
        files = (('data',name,data),)
        content_type,body = encode_multipart_formdata(fields,files,"image/x-fits")
        r = urllib2.Request(self.UPLOAD_URL,body)
        r.add_unredirected_header('Content-Type', content_type)
        r.add_unredirected_header('Content-Length', str(len(body)))
        response = self.opener.open(r)
        result = json.loads(response.read())[u'detailedImportResult']
        if len(result[u'successes']) == 1:
            return self.ACTIVITY_URL % result[u'successes'][0][u'internalId']
        elif len(result[u'failures']) == 1:
            code = result[u'failures'][0][u'messages'][0][u'code']
            msg = result[u'failures'][0][u'messages'][0][u'content']
            if code == 202:
                url = self.ACTIVITY_URL % result[u'failures'][0][u'internalId']
                raise GarminError("Upload Error: %s (%s)" % (msg,url))
            else:
                raise GarminError("Upload Error: %s (%d)" % (msg,code))
        else:
            raise GarminError("Unknown Upload Error: " + str(result))

    def upload_file(self,fname):
        data = open(fname).read()
        return self.upload(os.path.basename(fname),data)

def extract_forms(s):
    forms = {}
    for (tag,type) in re.findall('(<(form|input) .*?>)',s,flags=re.DOTALL):
        if type == 'form':
            id = re.findall('id="(.*?)"',tag,flags=re.DOTALL)[0].strip('/')
            action = re.findall('action="(.*?)"',tag,flags=re.DOTALL)[0].strip('/')
            forms[id] = (action,{})
        else:
            name = re.findall('name="(.*?)"',tag,flags=re.DOTALL)
            value = re.findall('value="(.*?)"',tag,flags=re.DOTALL)
            if name:
                forms[id][1][name[0]] = value[0] if value else None
    return forms

def encode_multipart_formdata(fields,files,mimetype=None):
    """
    Derived from - http://code.activestate.com/recipes/146306/

    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files

    Returns (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = mimetools.choose_boundary()
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        L.append('Content-Type: %s' % (mimetype or
                                       mimetypes.guess_type(filename)[0] or
                                       'application/octet-stream'))
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(map(bytes,L))
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

if __name__ == '__main__':
    import optparse,getpass
    parser = optparse.OptionParser(usage="Usage: %prog [options] <file(s)>")
    parser.add_option("--username",help="Garmin username (required)")
    parser.add_option("--password",help="Garmin password")
    parser.add_option("--device",action="store_true",help="Grab files from device")
    parser.add_option("--open",action="store_true",help="Open URL after upload")
    parser.add_option("--unlink",action="store_true",help="Unlink file after upload")
    options,args = parser.parse_args()
    if options.username is None:
        parser.print_help()
        sys.exit()
    if options.password is None:
        options.password = getpass.getpass("Garmin Password: ")
    g = GarminUploader()
    g.login(options.username,options.password)
    if options.device:
        if sys.platform == 'darwin':
            args = glob.glob('/Volumes/GARMIN/Garmin/Activities/*')
        else:
            print "ERROR: --device only supported on Mac OS-X"
            parser.print_help()
            sys.exit()
    for f in args:
        try:
            url = g.upload_file(f)
            print "File Uploaded: %s" % url
            if options.open:
                webbrowser.open(url)
            if options.unlink:
                os.unlink(f)
        except GarminError, e:
            print e
