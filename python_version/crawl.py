#!/usr/bin/env python3

import helper
import argparse
import operator
import functools
import os, time
import re, json
from urllib.parse import urlparse

# These are the icons of the links that get downloaded!
# You can get the name of such an icon from the moodle course site.
# The last part of the image src can be added here
ICON_WHITELIST = ['pdf-24', 'archive-24', 'sourcecode-24', 'mpeg-24', 'powerpoint-24', 'spreadsheet-24']


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
    sections = page.soup.select('body li.section')
    assets = []

    folder_name = out_folder + '/' + title
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)

    old_toc = {}
    try:
        with open(folder_name + '/toc.txt', 'r') as toc:
            for line in toc:
                item = json.loads(line)
                if 'id' in item: old_toc[item['id']] = item
    except Exception as ex:
        print("Failed to read toc", ex)
        pass
    
    toc = open(folder_name + '/toc_neu.txt', 'w')
    toc.write(json.dumps({'toc_version': '1.0', 'url': url, 'title': page.soup.find('title').text, 'date': time.strftime("%Y-%m-%d %H:%M:%S")}) + "\n")
    for section in sections:
        activities = section.select('.activity')
        i = 0
        for activity in activities:
            for link in activity.select('.activityinstance a'):
                i += 1
                should_download, icon_name = filter_element(link)
                modtype = re.search('modtype_([a-z]+)', str(activity.attrs['class']))
                asset_info = {
                    'href': link.attrs['href'], 
                    'text': link.text, 
                    'icon': icon_name, 
                    'should_download': 'X' if should_download else '',
                    'modtype': modtype.group(1) if modtype else '',
                    'id': int(activity.attrs['id'].split('-')[1]),
                    'section': int(section.attrs['id'].split('-')[1]),
                }
                if 'url/view.php?' in asset_info['href']: asset_info['href'] += '&redirect=1' # foo
                head = browser.session.head(asset_info['href'], allow_redirects=True)
                asset_info['href_resolved'] = head.url
                asset_info['encoding'] = head.encoding
                try:
                    asset_info['resolved_filename'] = urlparse(head.url).path.split('/')[-1]
                    asset_info['filename'] = asset_info['resolved_filename']
                except:
                    asset_info['resolved_filename'] = ''
                try:
                    asset_info['disposition_filename'] = head.headers['Content-Disposition'].split('"')[-2]
                    asset_info['filename'] = asset_info['disposition_filename']
                    should_download = True
                    asset_info['should_download'] = 'X'
                except:
                    asset_info['disposition_filename'] = ''
                if should_download:
                    asset_info['target_filename'] = "%s/%02d_%03d_%06d__%s__%s"%(folder_name, asset_info['section'], i, asset_info['id'], sanitize_title(asset_info['text'].replace('Datei', '')), asset_info['filename'])
                asset_info['headers'] = dict(head.headers)
                if 'etag' in head.headers or 'last_modified' in head.headers:
                    asset_info['cache_tag'] = asset_info['should_download'] + '|' + str(head.headers.get('etag')) + '|' + str(head.headers.get('last-modified'))
                
                
                # caching
                if asset_info['id'] in old_toc:
                    old_asset = old_toc[asset_info['id']]
                    if 'target_filename' in old_asset and os.path.isfile(old_asset['target_filename']):
                        print("old cache_tag = " , old_asset.get('cache_tag'))
                        print("new cache_tag = " , asset_info.get('cache_tag'))
                        if 'cache_tag' in old_asset and 'cache_tag' in asset_info and old_asset['cache_tag'] == asset_info['cache_tag']:
                            if old_asset['target_filename'] != asset_info['target_filename']:
                                print("Cached rename %s to %s" % (old_asset['target_filename'], asset_info['target_filename']))
                                os.rename(old_asset['target_filename'], asset_info['target_filename'])
                            print("Nothing to do for %s" % (asset_info['target_filename']))
                            should_download=False
                            asset_info['should_download'] = 'C'
                        else:
                            print("Delete outdated %s" % (old_asset['target_filename']))
                            os.unlink(old_asset['target_filename'])
                            asset_info['should_download'] = 'U'
                
                print("\t".join(str(asset_info[k]) for k in ('should_download', 'section', 'id', 'icon', 'modtype', 'text', 'href_resolved', 'encoding')))
                toc.write(json.dumps(asset_info) + "\n")
                if should_download:
                    assets.append(asset_info)
    toc.close()
    os.rename(folder_name + '/toc_neu.txt', folder_name + '/toc.txt')

    print('Starting download')
    for asset_info in assets:
        link = asset_info['href']
        print('\tDownloading: "{}"'.format(asset_info['text']))
        download_file(browser, link, asset_info['target_filename'])
    
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
    
    folder_name = out_folder + '/' + maintitle
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    folder_name += '/' + title
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
    print('Starting download')
    for asset_info in asset_links_filtered:
        link = asset_info['href']
        print('\tDownloading: "{}"'.format(asset_info['text']))
        download_file(browser, link, asset_info['target_filename'])
        
def filter_element(link):
    gets_downloaded = False
    if "resource/view.php" in link.attrs['href']: gets_downloaded = True
    try:
        icon_name = link.select('img')[0].attrs['src'].split('/')[-1]
    except:
        icon_name = None
    gets_downloaded = gets_downloaded or icon_name in ICON_WHITELIST
    return gets_downloaded, icon_name
    
def filter_directory(link):
    try:
        icon_name = link.select('img')[0].attrs['src'].split('/')[-1]
        print("got icon in filter_dir")
    except:
        return False
    print("icon name: " + icon_name)
    gets_downloaded = icon_name == "icon"
    return gets_downloaded


def download_file(browser, url, filename):
    page = browser.session.get(url)
    with open(filename, 'wb') as f:
        f.write(page.content)


def sanitize_title(title):
    return title.strip().replace(' ', '_').replace('/', '-').replace(':', '-').replace('-', '_').strip()


if __name__ == '__main__':
    main()
