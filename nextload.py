import os
import base64
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from tqdm import tqdm
import click
import fnmatch

# Configuration - these will be provided via command line arguments
NEXTCLOUD_SHARE_URL = "" # TO BE PROVIDED IN ARGUMENT
NEXTCLOUD_SHARE_PASSWORD = "" # TO BE PROVIDED IN ARGUMENT IF NECESSARY
LOCAL_DIR = "."  # Dossier local de destination
VERBOSE = False

# ANSI color codes
COLORS = {
    'ERROR': '\033[91m',
    'INFO': '\033[94m',
    'SUCCESS': '\033[92m',
    'WARNING': '\033[93m',
    'ENDC': '\033[0m',
}


def print_color(message, color):
    """Prints a message with the specified color."""
    print(f"{COLORS[color]}{message}{COLORS['ENDC']}")

def format_file_size(size_bytes):
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024
        i += 1
    
    return f"{size:.2f} {size_names[i]}"

def parse_nextcloud_share_url(share_url):
    """Extrait les informations du lien partagé Nextcloud."""
    if not share_url.startswith("http"):
        raise ValueError(f"'{share_url}' n'est pas une URL valide.")

    # Extraction du token et du sous-dossier
    if "/s/" not in share_url:
        raise ValueError(f"'{share_url}' n'est pas un lien partagé Nextcloud valide.")

    # Extraction de l'URL de base et du token
    host_url = share_url.split("/s/")[0]
    share_token = share_url.split("/s/")[1].split("?")[0].split("/")[0]

    # Extraction du sous-dossier (si présent)
    share_subdir = ""
    if "?path=" in share_url:
        share_subdir = share_url.split("?path=")[1]

    host_url = host_url.split("/index.php")[0]

    return host_url, share_token, share_subdir

def list_content(webdav_url, share_token, share_password, share_subdir=""):
    """Liste le contenu d'un dossier WebDAV Nextcloud."""
    with requests.Session() as session:
      headers = {"X-Requested-With": "XMLHttpRequest"}
      #auth_string = f"{share_token}:{share_password}"
      #auth_header = "Basic " + base64.b64encode(auth_string.encode()).decode()
      auth = (share_token, share_password)
  
      headers = {
          "X-Requested-With": "XMLHttpRequest",
          #"Authorization": auth_header,
          "Depth": "1"
      }
  
      req_url = f"{webdav_url}/public.php/webdav/{share_subdir}"
  #    req_url = f"{webdav_url}/public.php/dav/files/{share_token}{share_subdir}"
      print_color(f"Listing {req_url}", 'INFO')
      # Requête PROPFIND pour lister les fichiers/dossiers
      response = session.request(
          "PROPFIND",
          req_url,
          headers=headers,
          auth=auth,
          data='''<?xml version="1.0" encoding="UTF-8"?>
              <d:propfind xmlns:d="DAV:">
                  <d:prop xmlns:oc="http://owncloud.org/ns">
                      <d:getlastmodified/>
                      <d:getcontentlength/>
                      <d:getcontenttype/>
                  </d:prop>
              </d:propfind>''',
      )
      print(response)
  
      if response.status_code != 207:
          print_color(f"Failed to list content: {response.status_code}", 'ERROR')
          raise Exception(f"Échec de la requête PROPFIND: {response.status_code}")
  
      # Analyse du XML pour extraire les fichiers/dossiers
      soup = BeautifulSoup(response.content, "xml")
      files = []
      folders = []
  
      for response_tag in soup.find_all("d:response"):
          href = response_tag.find("d:href").text
          print(href)
          if not href.startswith("/public.php/webdav/"):
             continue
          href = href.split("/public.php/webdav/")[1]
  #        if not href.startswith("/public.php/dav/files/" + share_token):
  #           continue
  #        href = href.split("/public.php/dav/files/" + share_token + "/")[1]
          print(f"'{href}'")
          if len(href) == 0:
             continue
          if href.endswith("/"):
              folders.append(href)
          else:
              files.append(href)
  
      return files, folders

def list_content_with_sizes(webdav_url, share_token, share_password, share_subdir=""):
    """Liste le contenu d'un dossier WebDAV Nextcloud avec les tailles de fichiers."""
    with requests.Session() as session:
      headers = {"X-Requested-With": "XMLHttpRequest"}
      auth = (share_token, share_password)
  
      headers = {
          "X-Requested-With": "XMLHttpRequest",
          "Depth": "1"
      }
  
      req_url = f"{webdav_url}/public.php/webdav/{share_subdir}"
      if VERBOSE:
          print_color(f"Listing {req_url}", 'INFO')
      
      # Requête PROPFIND pour lister les fichiers/dossiers avec leurs propriétés
      response = session.request(
          "PROPFIND",
          req_url,
          headers=headers,
          auth=auth,
          data='''<?xml version="1.0" encoding="UTF-8"?>
              <d:propfind xmlns:d="DAV:">
                  <d:prop xmlns:oc="http://owncloud.org/ns">
                      <d:getlastmodified/>
                      <d:getcontentlength/>
                      <d:getcontenttype/>
                  </d:prop>
              </d:propfind>''',
      )
  
      if response.status_code != 207:
          print_color(f"Failed to list content: {response.status_code}", 'ERROR')
          raise Exception(f"Échec de la requête PROPFIND: {response.status_code}")
  
      # Analyse du XML pour extraire les fichiers/dossiers avec leurs tailles
      soup = BeautifulSoup(response.content, "xml")
      files = []  # Liste de tuples (nom, taille)
      folders = []
  
      for response_tag in soup.find_all("d:response"):
          href = response_tag.find("d:href").text
          if not href.startswith("/public.php/webdav/"):
             continue
          href = href.split("/public.php/webdav" + share_subdir)
          if len(href) == 1 or len(href[1]) == 0:
             continue
          href = href[1]

          if href.endswith("/"):
              folders.append(href)
          else:
              # Extraire la taille du fichier
              content_length_tag = response_tag.find("d:getcontentlength")
              file_size = int(content_length_tag.text) if content_length_tag and content_length_tag.text else 0
              files.append((href, file_size))
  
      return files, folders

def download_file(webdav_url, share_token, share_password, remote_path, local_path):
    """Télécharge un fichier depuis Nextcloud."""
    headers = {"X-Requested-With": "XMLHttpRequest"}
    auth = (share_token, share_password)

    # Check if file exists and get its size
    file_exists = os.path.exists(local_path)
    local_size = os.path.getsize(local_path) if file_exists else 0

    with requests.Session() as session:
      # Get remote file size
      response = session.head(
          f"{webdav_url}/public.php/webdav{remote_path}",
          headers=headers,
          auth=auth,
      )
      remote_size = int(response.headers.get('Content-Length', 0))

      # Resume download if local file is smaller than remote
      if file_exists and local_size >= remote_size:
          print_color(f"File already exists and is up-to-date: {local_path}", 'SUCCESS')
          return

      headers['Range'] = f'bytes={local_size}-' if file_exists else None

      print_color(f"Attempting download: remote={remote_path} to local={local_path}, resuming at {local_size}", 'INFO')

    with requests.Session() as session:
      response = session.get(
          f"{webdav_url}/public.php/webdav{remote_path}",
          headers=headers,
          auth=auth,
          stream=True,
      )

      if response.status_code == 200:
          os.makedirs(os.path.dirname(local_path), exist_ok=True)
          mode = 'ab' if file_exists else 'wb'
          with open(local_path, mode) as f, tqdm(
              desc=local_path,
              total=remote_size,
              initial=local_size,
              unit='iB',
              unit_scale=True,
              unit_divisor=1024,
          ) as bar:
              for chunk in response.iter_content(chunk_size=8192):
                  if chunk:
                      f.write(chunk)
                      bar.update(len(chunk))
          print_color(f"Downloaded: {local_path}", 'SUCCESS')
      else:
          print_color(f"Download failed: {remote_path}", 'ERROR')

def should_download_file(filename, include_patterns, exclude_patterns):
    """Determine if a file should be downloaded based on include/exclude patterns."""
    # If no patterns specified, download everything
    if not include_patterns and not exclude_patterns:
        return True
    
    # Check exclude patterns first (they take precedence)
    if exclude_patterns:
        for pattern in exclude_patterns:
            if fnmatch.fnmatch(filename, pattern):
                print_color(f"Excluding file '{filename}' (matches exclude pattern '{pattern}')", 'WARNING')
                return False
    
    # Check include patterns
    if include_patterns:
        for pattern in include_patterns:
            if fnmatch.fnmatch(filename, pattern):
                return True
        # If include patterns are specified but no match, exclude the file
        print_color(f"Excluding file '{filename}' (doesn't match any include pattern)", 'WARNING')
        return False
    
    # If only exclude patterns are specified and no match, include the file
    return True

def crawl_and_list(webdav_url, share_token, share_password, share_subdir, current_folder, include_patterns=None, exclude_patterns=None, indent=""):
    """Parcourt et liste récursivement les fichiers/dossiers avec leurs tailles."""
    files, folders = list_content_with_sizes(webdav_url, share_token, share_password, share_subdir + current_folder)

    for file, file_size in files:
        if should_download_file(file, include_patterns, exclude_patterns):
            formatted_size = format_file_size(file_size)
            print_color(f"{indent}📄 {file} ({formatted_size})", 'INFO')

    for folder in folders:
        print_color(f"{indent}📁 {folder}", 'INFO')
        remote_folder = f"{current_folder}{folder}"
        crawl_and_list(webdav_url, share_token, share_password, share_subdir, remote_folder, include_patterns, exclude_patterns, indent + "  ")

def crawl_and_download(webdav_url, share_token, share_password, share_subdir, current_folder, local_base, include_patterns=None, exclude_patterns=None):
    """Parcourt et télécharge récursivement les fichiers/dossiers."""
    files, folders = list_content(webdav_url, share_token, share_password, share_subdir + current_folder)

    for file in files:
        if should_download_file(file, include_patterns, exclude_patterns):
            remote_path = f"/{share_subdir}/{file}" if share_subdir else f"/{file}"
            local_path = os.path.join(local_base, os.path.basename(file))
            download_file(webdav_url, share_token, share_password, remote_path, local_path)

    for folder in folders:
        print_color(f"Entering folder '{folder}'", 'INFO')
        remote_folder = f"{current_folder}{folder}"
        local_folder = os.path.join(local_base, os.path.basename(folder.rstrip("/")))
        crawl_and_download(webdav_url, share_token, share_password, share_subdir, remote_folder, local_folder, include_patterns, exclude_patterns)

@click.group()
def cli():
    """Nextload - Nextcloud Share Downloader"""
    pass

@cli.command()
@click.option('--url', required=True, help='Nextcloud share URL')
@click.option('--password', default='', help='Nextcloud share password (if required)')
@click.option('--output-dir', default='.', help='Local directory to save files')
@click.option('--include', multiple=True, help='File pattern to include (can be used multiple times, e.g., *.hdf5)')
@click.option('--exclude', multiple=True, help='File pattern to exclude (can be used multiple times, e.g., *.txt)')
def download(url, password, output_dir, include, exclude):
    """Download files from a Nextcloud share."""
    global NEXTCLOUD_SHARE_URL, NEXTCLOUD_SHARE_PASSWORD, LOCAL_DIR
    
    NEXTCLOUD_SHARE_URL = url
    NEXTCLOUD_SHARE_PASSWORD = password
    LOCAL_DIR = output_dir
    
    try:
        host_url, share_token, share_subdir = parse_nextcloud_share_url(NEXTCLOUD_SHARE_URL)
        print_color(f"Nextcloud host: {host_url}", 'INFO')
        print_color(f"Share token: {share_token}", 'INFO')
        print_color(f"Share subdirectory: {share_subdir}", 'INFO')
        print_color(f"Output directory: {output_dir}", 'INFO')
        
        if include:
            print_color(f"Include patterns: {', '.join(include)}", 'INFO')
        if exclude:
            print_color(f"Exclude patterns: {', '.join(exclude)}", 'INFO')
        
        crawl_and_download(host_url, share_token, NEXTCLOUD_SHARE_PASSWORD, share_subdir, "/", LOCAL_DIR, include, exclude)
    except Exception as e:
        print_color(f"Error: {e}", 'ERROR')
        raise click.ClickException(str(e))

@cli.command()
@click.option('--url', required=True, help='Nextcloud share URL')
@click.option('--password', default='', help='Nextcloud share password (if required)')
@click.option('--include', multiple=True, help='File pattern to include (can be used multiple times, e.g., *.hdf5)')
@click.option('--exclude', multiple=True, help='File pattern to exclude (can be used multiple times, e.g., *.txt)')
def list(url, password, include, exclude):
    """List files from a Nextcloud share with sizes."""
    global NEXTCLOUD_SHARE_URL, NEXTCLOUD_SHARE_PASSWORD
    
    NEXTCLOUD_SHARE_URL = url
    NEXTCLOUD_SHARE_PASSWORD = password
    
    try:
        host_url, share_token, share_subdir = parse_nextcloud_share_url(NEXTCLOUD_SHARE_URL)
        print_color(f"Nextcloud host: {host_url}", 'INFO')
        print_color(f"Share token: {share_token}", 'INFO')
        print_color(f"Share subdirectory: {share_subdir}", 'INFO')
        print_color("Mode: Listing files with sizes", 'INFO')
        
        if include:
            print_color(f"Include patterns: {', '.join(include)}", 'INFO')
        if exclude:
            print_color(f"Exclude patterns: {', '.join(exclude)}", 'INFO')
        
        crawl_and_list(host_url, share_token, NEXTCLOUD_SHARE_PASSWORD, share_subdir, "/", include, exclude)
    except Exception as e:
        print_color(f"Error: {e}", 'ERROR')
        raise click.ClickException(str(e))

if __name__ == "__main__":
    cli()

