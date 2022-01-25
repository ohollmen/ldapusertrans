# ldapusertrans - Translate Bare Usernames to more substantial LDAP user information

LDAP User translator implements following features:
- Translating a user list stored in simple ascii file (username per line)
  to "more rich" LDAP userinformation, such as full name and email address.
- Retrieve all usernames from the commit history (log) of SVN project workarea

This comination makes ldapusertrans an obvious tool for creating
a "users.txt" fir for SVN to Git migration, where SVN change author names
need to be translated to Git-preferred "Full Name + email address" form.

However ldapusertrans also works well for small applicatiosn where a limited
set of users (usernames) are dealt with and their information needs to be
cached (e.g. in JSON format).

## TODO

- Usage
- Full example use-case(s) (Both SVN-to-Git migr. and Userinfo caching)


