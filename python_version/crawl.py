#!/usr/bin/env python3

import helper
import argparse
import operator
import functools
import os

# These are the icons of the links that get downloaded!
# You can get the name of such an icon from the moodle course site.
# The last part of the image src can be added here
ICON_WHITELIST = ['pdf-24', 'archive-24', 'sourcecode-24', 'mpeg-24', 'powerpoint-24', 'spreadsheet-24']
UNUSED_ICONS = []


def main():
    parser = argparse.ArgumentParser(description="Download moodle assets")
    parser.add_argument('--url', default='https://moodle.informatik.tu-darmstadt.de/course/view.php?id=155')
    args = parser.parse_args()
    user, password = helper.get_credentials()
    browser = setup_connection(args.url, user, password)
    download_assets(args.url, browser)

def setup_connection(url, user, password):
    print('Logging in')
    browser = helper.login(url, user, password)
    return browser
    
def download_assets(url, browser, out_folder='out'):
    
    page = browser.get(url)
    title = sanitize_title(page.soup.find('title').text)
    print('Retrieving links')
    asset_links = page.soup.select('body .activityinstance a')
    asset_links_filtered = []
    for link in asset_links:
        if filter_element(link):
            asset_links_filtered.append(link)
        else:
            print('\tWill not get downloaded: "{}"'.format(link.text))

    print('\n(The following assets with icon-names will not be downloaded: "{}")\n'.format(', '.join(set(UNUSED_ICONS))))

    folder_name = out_folder + '/' + title
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    print('Starting download')
    for asset in asset_links_filtered:
        link = asset.attrs['href']
        print('\tDownloading: "{}"'.format(asset.text))
        download_file(browser, link, folder_name, default_filename = sanitize_title(asset.text.replace('Datei', '')))
    
    directory_links = page.soup.select('.modtype_folder a')
    
    
    for directory in directory_links:
        download_subfolder(browser, directory.attrs['href'], title)

def download_subfolder(browser, url, maintitle, out_folder='out'):
    page = browser.get(url)
    title = sanitize_title(page.soup.find('h2').text)
    asset_links = page.soup.select('#folder_tree0 a')
    asset_links_filtered = []
    for link in asset_links:
        if filter_element(link):
            asset_links_filtered.append(link)
        else:
            print('\tWill not get downloaded: "{}"'.format(link.text))
            
    print('\n(The following assets with icon-names will not be downloaded: "{}")\n'.format(', '.join(set(UNUSED_ICONS))))

    folder_name = out_folder + '/' + maintitle
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    folder_name += '/' + title
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    print('Starting download')
    for asset in asset_links_filtered:
        link = asset.attrs['href']
        print('\tDownloading: "{}"'.format(asset.text))
        download_file(browser, link, folder_name, default_filename = sanitize_title(asset.text.replace('Datei', '')))
        
def filter_element(link):
    try:
        icon_name = link.select('img')[0].attrs['src'].split('/')[-1]
    except:
        return False
    gets_downloaded = icon_name in ICON_WHITELIST
    if not gets_downloaded:
        UNUSED_ICONS.append(icon_name)
    return gets_downloaded
    
def filter_directory(link):
    try:
        icon_name = link.select('img')[0].attrs['src'].split('/')[-1]
        print("got icon in filter_dir")
    except:
        return False
    print("icon name: " + icon_name)
    gets_downloaded = icon_name == "icon"
    return gets_downloaded


def download_file(browser, url, folder, default_filename):
    page = browser.get(url)

    try:
        filename = page.headers['Content-Disposition'].split('"')[-2]
    except:
        filename = default_filename

    with open(folder + '/' + filename, 'wb') as f:
        f.write(page.content)


def sanitize_title(title):
    return title.replace(' ', '_').replace('/', '-').replace(':', '-').replace('-', '_').strip()


if __name__ == '__main__':
    main()
