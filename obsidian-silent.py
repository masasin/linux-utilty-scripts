#!/usr/bin/env python3
import re
import ssl
import sys
import urllib.parse
import urllib.request
from urllib.error import HTTPError

API_KEY = "5b4292f14d050a0d5c3fbce2a9da3a4d7d1655e8c43ecec35d5d39536cb473ca"
PORT = 27124
USE_HTTPS = True

def get_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

def request(endpoint, method="GET", data=None, headers=None):
    if headers is None:
        headers = {}
    
    protocol = "https" if USE_HTTPS else "http"
    url = f"{protocol}://127.0.0.1:{PORT}{endpoint}"
    
    headers["Authorization"] = f"Bearer {API_KEY}"
    if data is not None:
        headers["Content-Type"] = "text/markdown"
        encoded_data = data.encode('utf-8')
    else:
        encoded_data = None

    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)
    
    with urllib.request.urlopen(req, context=get_ssl_context()) as response:
        return response.read().decode('utf-8')

def insert_data_smart(content, heading, data_line):
    # Locate the target heading (accounting for variable hash levels and whitespace)
    heading_pattern = re.compile(r'(^|\n)(#+)[ \t]+' + re.escape(heading) + r'[ \t]*(\n|$)')
    match = heading_pattern.search(content)
    
    if not match:
        prefix = "\n" if content and not content.endswith("\n") else ""
        return f"{content}{prefix}\n## {heading}\n{data_line}\n"

    start_body = match.end()
    level = len(match.group(2))
    
    # Locate the start of the next section (same level or higher) to define the upper bound
    next_heading_pattern = re.compile(r'(^|\n)#{1,' + str(level) + r'}[ \t]+')
    next_match = next_heading_pattern.search(content, start_body)
    
    if next_match:
        end_body = next_match.start()
    else:
        end_body = len(content)

    section_text = content[start_body:end_body]
    
    # Separate content from trailing empty lines to ensure insertion happens *before* the section break
    trimmed_section = section_text.rstrip()
    trailing_whitespace = section_text[len(trimmed_section):]
    
    separator = "\n" if trimmed_section else ""
    
    # Inject data, preserving the original section spacing
    new_section = f"{trimmed_section}{separator}{data_line}{trailing_whitespace}"
    
    if not trailing_whitespace and end_body != len(content):
        new_section += "\n"

    return content[:start_body] + new_section + content[end_body:]

def main():
    if len(sys.argv) < 2:
        return

    try:
        raw_uri = sys.argv[1]
        parsed = urllib.parse.urlparse(raw_uri)
        params = urllib.parse.parse_qs(parsed.query)

        data = params.get("data", [""])[0]
        heading = params.get("heading", [None])[0]
        is_daily = params.get("daily", ["false"])[0].lower() == "true"
        filepath = params.get("filepath", [""])[0]

        endpoint = ""
        if is_daily:
            endpoint = "/periodic/daily/"
        elif filepath:
            # Urllib requires a strictly encoded path (e.g. %20 for spaces)
            encoded_path = urllib.parse.quote(filepath, safe='/')
            endpoint = f"/vault/{encoded_path}"
        else:
            return

        try:
            current_content = request(endpoint, method="GET")
        except HTTPError as e:
            if e.code == 404:
                current_content = ""
            else:
                raise

        if heading:
            new_content = insert_data_smart(current_content, heading, data)
        else:
            prefix = "\n" if current_content and not current_content.endswith("\n") else ""
            new_content = f"{current_content}{prefix}{data}\n"

        request(endpoint, method="PUT", data=new_content)

    except Exception:
        pass

if __name__ == "__main__":
    main()
