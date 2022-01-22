#!/usr/local/bin/python3
# # Extract change authors from SVN and resolve users full names and emails from LDAP directory 
# create users.txt / authors.txt
# Use file with "git svn clone http://... --authors-file=users.txt" when doing svn-to-git migrations
# 
# 
# ## Python LDAP modules
# pip3 install python-ldap <= Complex (not chosen for task, requires compilations with brew)
# pip3 install ldap3  <= Pure python(3) - Good, works great
# 
# ## Notes for Mac
# - Mac Catalina is a mess with broken (xcode/ apple) svn, make (xcrun wrapper ...). Reinstall XCode
# - https://apple.stackexchange.com/questions/382357/invalid-active-developer-path-when-attempting-to-use-pip3-after-upgrading-to-m
#  - sudo xcode-select --reset
#  - xcode-select --install
# 
# ## Ubuntu (18.04)
# - sudo apt-get install python3-ldap OR ...
# - python3-ldap3 (Pure Python LDAP client library)
#
# ## References
# pip install beautifulsoup4
# https://www.crummy.com/software/BeautifulSoup/
# https://stackoverflow.com/questions/6927749/is-there-a-python-equivalent-to-perls-xmlsimple
# https://luisartola.com/easy-xml-in-python/
# https://git-scm.com/book/en/v2/Git-and-Other-Systems-Migrating-to-Git
# 
# ## TODO
# - Provide example (JSON) LDAP config, document it - OK
# - Allow config from more configurable location - OK
# - Make messages got to STDERR to avoid interfereing with real output
#  - sys.stderr.write(msg) or print(msg, file=sys.stderr)
#  - for print() option Need (in python3): from __future__ import print_function
# - Fix (default) authors file name: users.txt - OK
# - Provide attr config for OpenLDAP style directory
# - Use dispatch table for subcommand ops - OK
# - Support larger/ more organized variety of CL opts (import argparse) - OK
#   - Esp formats options for "resolve"
# - Allow the set of attributes to be configurable (in config file), esp for JSON output
import os
import sys
import time
import json
import ldap3
import subprocess
# import bs4
import xml.etree

from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from xml.etree.ElementTree import SubElement
import argparse

authorsfn = "./users.txt" # authors.txt / users.txt

def loadcfg():
  fn = ''
  home = os.environ['HOME']
  fnopts = [ home + "/.ldapuidtrans.conf.json", "./.ldapuidtrans.conf.json", home  + "/.linetboot/global.conf.json" ]
  for fnopt in fnopts:
    if os.path.exists(fnopt):
      print("Found: config "+fnopt);
      fn = fnopt;
      break;
  if not fn: print("No Config found !"); return
  fh = open(fn, "r")
  cont = fh.read()
  j = json.loads(cont);
  if j.get('ldap'): ld = j['ldap']
  else: ld = j
  # Validate a few members here ?
  # print(ld);
  return ld

# Create Connection string suitable for pythong ldap or ldap3
def connstr(ld, makeurl):
  portpara = ":389"
  if ld['ssl'] : portpara = ":"+str(636)
  uprefix = "ldap://"
  ldurl = ld['host']+ portpara
  if makeurl:
    if ld['ssl']: uprefix = "ldaps://"
    ldurl = uprefix + ldurl
  return ldurl

# Connect and bind to LDAP
def ldconnect(ld):
  # print(ld);
  ldurl = connstr(ld, 1)
  print("Connect to: "+ldurl);
  server = ldap3.Server(ldurl) # ld['host']
  # print(server);
  # conn = ldap3.Connection(server, user=ld['binddn'], password=ld['bindpass'])
  conn = ldap3.Connection(server, ld['binddn'], ld['bindpass'])
  # if conn: print("Got connected: "+ str(conn));
  if not conn: return None
  # print("Bind (may take a moment)...");
  bindok = conn.bind()
  # print("Bound okay: " + str(bindok));
  if not bindok: return None
  return conn

# Resolve users from LDAP to finally generate authors.txt in format:
#  loginname = Joe User <user@example.com>
# Generate username to LDAP entry mapping here (for fast lookup by caller)
def ldap_resolve(conn, ld, users):
  # TODO: allow config
  attrs = ["displayName", "sAMAccountName", "mail"] # givenName, mobile, telephoneNumber
  uents = [];
  uinfomap = {}
  #def setkey(k):
  # Init to falsy value
  for k in users: uinfomap[k] = False
  # map(setkey, users) # map does NOT work
  # print(json.dumps(uinfomap));
  for un in users:
    conn.search(ld['userbase'], '(&(objectclass=person)(samaccountname='+un+'))', attributes = attrs)
    for entry in conn.response:
      adict = entry['attributes'];
      # print("Setting INFO for "+un)
      e = { 'uname': un, 'email': adict['mail'], 'fullname': adict['displayName']}
      uinfomap[un] = e;
      #uents.append(e)
  return uinfomap
  # return uents

# Extract SVN log (XML) output from current workarea
def svnlog_xml():
  # cmd = "svn log -q --xml"
  cmdarr = ["svn", "log", "-q", "--xml"]
  print("Run: "+" ".join(cmdarr));
  call = subprocess.run(cmdarr, stdout=subprocess.PIPE, text=True, ) # input="Hello from the other side"
  out = call.stdout
  rc  = call.returncode
  #print("Got rc = "+str(rc));
  if rc: return None
  return out

# Beautiful soap (_bs) version of XML extraction
# Not used.
def findauthors_bs(out):
  soup = bs4.BeautifulSoup(out, 'html.parser')
  # print(out); print("SOUP:"+str(soup));
  authors = soup.find_all('author')
  # print(authors); print(json.dumps(authors));
  for  a in authors:
    print(a); # Would need to get rid of wrapping elem, get value (elem content / text) only.

# Find authors using the python core module (xml.etree)
def findauthors(fname):
  document = xml.etree.ElementTree.parse(fname) # 'log.xml'
  #document = xml.etree.ElementTree.parse(out)
  authors = document.findall('logentry/author') # OK
  uas = {} # Unique Authors
  for u in authors:
    # print(u.text);
    if not uas.get(u.text): uas[u.text] = 1
    else : uas[u.text] += 1
  # print(uas); # Stats per author
  return uas.keys()
  # users = document.findall('author') # NOT

def logauthors():
  log = svnlog_xml()
  # Cycle content into a temp file as xml.etree.ElementTree.parse(...)
  # does not seem to be able to parse raw XML (string) content, needs a filename.
  tmpname = "/tmp/svnlog_"+ str(os.getpid()) +"_"+ str(time.time())
  tfh = open(tmpname, "w");
  tfh.write(log)
  tfh.close()
  authors = findauthors(tmpname);
  # Store authors (but do not owerwrite existing authrs file)  
  if os.path.exists(authorsfn): raise BaseException(authorsfn+" already Exists !")
  fh = open(authorsfn, "w");
  fh.write("\n".join(authors)+"\n")
  fh.close()
  print("Wrote "+authorsfn);

# Load users from single-column usernames list file and
# resolve them from LDAP directory.
def users_resolve():
  fh = open(authorsfn, "r");
  cont = fh.read()
  fh.close()
  # print(cont)
  cont = cont.strip()
  authors = cont.split("\n")
  # TODO: authors.filter() # Filter comments, empty lines ...
  ld = loadcfg()
  conn = ldconnect(ld)
  # print("Resolve: ", authors);
  uents = ldap_resolve(conn, ld, authors)
  # TODO: Allow multiple different formats:
  # - txt - The SVN-to-Git migration supported username to Name, Email format
  # - json - usernames mapped to whole LDAP entry (?)
  # print(json.dumps(uents, indent = 2));
  #### Format authors into users.txt format
  # Unresolved authors must be resolved manually (if usernames were shuffled in organization,
  # often the same person is in by 2 (or more) usernames, last one resolvable, earlier ones needing
  # detective work.
  def authorvalue(anode):
    if not anode: return ""
    return anode['fullname'] + " <"+anode['email']+">"
  # Output in authors.txt format
  if args.get('fmt') == 'txt':
    for an in authors:
      print(an + " = " +authorvalue(uents[an])+"");
  elif args.get('fmt') == 'json':
    # Print mapping directly as JSON
    print(json.dumps(uents, indent=2))
        

def usage(msg):
  if msg: print(msg);
  print("Try ops: "+", ".join(ops.keys()));
  sys.exit(1);
# Workaround for Python inflexibility with args
# (Cannot use usage directly via dispatch table because of:
# usage() missing 1 required positional argument: 'msg')
def usage_help():
  usage('')
# subcommand Dispatch table
ops = {
  "resolve": users_resolve,
  "logauthors": logauthors,
  "help": usage_help
}

if __name__ == '__main__':
  # print(sys.argv);
  sys.argv = sys.argv[1:]
  if not len(sys.argv): usage("No submommand/op given");
  op = sys.argv.pop(0); # x = x[1:]
  if not op: usage("No submommand/op given");
  if not ops.get(op): usage("No subcommand "+op+" available");
  parser = argparse.ArgumentParser(description='LDAP User(name) translator')
  parser.add_argument('fmt',  default="txt", help='Format for resolved LDAP info output') # type=ascii
  global args
  args = vars(parser.parse_args())
  print(args);
  #if op == 'resolve':
  #  users_resolve()
  #elif op == 'logauthors':
  #  logauthors()
  #elif op == 'help':
  #  usage("")
  ops[op]()
  sys.exit(0)
