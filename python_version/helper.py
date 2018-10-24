import mechanicalsoup
import getpass
from urllib.parse import urljoin

def login(url, username, password):
    browser = mechanicalsoup.Browser()
    page = browser.get(url)
    clickthrough_links = page.soup.select('.loginpanel a:nth-of-type(1)')
    clickthrough_forms = page.soup.select('.loginpanel form:nth-of-type(1)')
    if len(clickthrough_links) != 0:
        link = clickthrough_links[0].attrs['href']
        print("link",link)
        login_page = browser.get(link)
    elif len(clickthrough_forms) != 0:
        link = clickthrough_links[0].attrs['action']
        print("link",link)
        login_page = browser.get(link)
    else:
        login_page = page
    print("login_page.url",login_page.url)
    form = login_page.soup.select('form#fm1, form#login')[0]
    submit_url = urljoin(login_page.url, form.attrs['action'])
    print("submit_url",submit_url)
    print("form action",form.attrs['action'])
    form.select('#username')[0].attrs['value'] = username
    form.select('#password')[0].attrs['value'] = password
    page = browser.submit(form, submit_url)
    return browser

def get_credentials():
    CREDENTIALS_FILE = 'user.txt'
    def get_by_file():
        with open(CREDENTIALS_FILE, 'r') as f:
            contents = [x.strip() for x in f.readlines() if x.strip() != '']
            if len(contents) != 2:
                raise Exception('Error retrieving username/password: File {} does not have two lines. Content: "{}"'.format(CREDENTIALS_FILE, '\n'.join(contents)))
            return contents

    def ask_user():
        username = None
        password = None
        while username is None:
            username = input('TUID: ')
        while password is None:
            password = getpass.getpass('Password: ')
        return username, password

    # First try to get the user credentials by file, afterwards by programm arguments
    try:
        return get_by_file()
    except:
        pass

    try:
        return ask_user()
    except:
        pass
    raise(Exception('Could not retreive username/password. Are you doing this on purpose?'))
