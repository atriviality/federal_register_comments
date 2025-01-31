# coding: utf8
"""
This (software/technical data) was produced for the U. S. Government under 
Contract Number 1331L523D130S0003, and is subject to Federal Acquisition 
Regulation Clause 52.227-14, Rights in Data—General, Alt. II, III and IV 
(DEC 2007) [Reference 27.409(a)].

No other use other than that granted to the U. S. Government, or to those 
acting on behalf of the U. S. Government under that Clause is authorized 
without the express written permission of The MITRE Corporation.

For further information, please contact The MITRE Corporation, Contracts 
Management Office, 7515 Colshire Drive, McLean, VA  22102-7539, (703) 983-6000.
"""

"""
Consolidates the comments for a specific document from  the Federal Register. It
requires an API key, which can be obtained from https://open.gsa.gov/api/regulationsgov/.

The post process adds a title page with a word cloud and bookmarks so the respondents can
easily be identified.

atrivedi@mitre.org
"""
import argparse
from datetime import datetime
import requests
import json
import re
import pprint
import uuid
import time
import io
import os
import sys
import pypdf
from html import unescape
from bs4 import BeautifulSoup
from wordcloud import WordCloud
from pdfrw import PdfWriter, PdfReader, PdfDict, PdfName
from fpdf import FPDF 

# Not the best security practice
# Shouldn't be necessary for non SSL inspect networks
VERIFY = True

def get_document(_id, key):
    document_url = f"https://api.regulations.gov/v4/documents/{_id}"
    resp = requests.get(document_url, headers={"X-Api-Key": key}, verify=VERIFY)
    if resp.status_code != 200:
        raise RuntimeError("API Comms Failed")
    return resp.json()["data"]["attributes"]["objectId"]

def get_comments(oid, key, page):
    comments_url = f"https://api.regulations.gov/v4/comments?filter[commentOnId]={oid}&page[size]=250&page[number]={page}"
    #comments_url = f"https://api.regulations.gov/v4/comments?filter[commentOnId]={oid}&page[size]=10&page[number]={page}"
    resp = requests.get(comments_url, headers={"X-Api-Key": key}, verify=VERIFY)
    if resp.status_code != 200:
        raise RuntimeError("API Comms Failed")

    return resp.json()

def clean_author(doc):
   return doc["attributes"]["title"].replace("Comment from the", "").replace("Comment from", "").strip()

def process_comments(comments, key):
    for f in comments:
        resp = requests.get(comments[f]['url'], headers={"X-Api-Key": key}, verify=VERIFY).json()
        attachments = resp["data"]["relationships"]["attachments"]["links"]["related"]
        attach_resp = requests.get(attachments, headers={"X-Api-Key": key}, verify=VERIFY).json()
        comments[f]["modified"] = resp["data"]["attributes"]["modifyDate"]
        comments[f]["text"] = resp["data"]["attributes"]["comment"]
        comments[f]["attachment"] = []
        if attach_resp["data"]:
            fils = attach_resp["data"][0]["attributes"]["fileFormats"]
            for g in fils:
                if g["format"] != "pdf":
                    print("Cannot Handle Non-PDF")
                    continue
                else:
                    comments[f]["attachment"].append(g["fileUrl"])
    return comments
        
def merge_comments(comments, _id, key):
    merger = PdfWriter()

    prev = None
    for f in comments:
        if comments[f]["attachment"]:
            comments[f]["file"] = f'/tmp/{str(uuid.uuid4())}.pdf'
            response = requests.get(comments[f]["attachment"][0], headers={"X-Api-Key": key}, verify=VERIFY)
            with open(comments[f]["file"], 'wb') as f:
                f.write(response.content)
    for f in comments:
        if comments[f]["attachment"]:
            pdf = PdfReader(comments[f]["file"])
        
            comments[f]["pages"] = len(pdf.pages)
            merger.addpages(pdf.pages)

        else: 
            x = FPDF(unit="pt")
            x.set_auto_page_break(0)
            x.add_page()
            x.set_font('Arial', style='B', size=20)
            x.cell(40, 10, f + '\n')
            x.ln(30)
            x.set_font('Arial', size=12)
            soup = BeautifulSoup(comments[f]["text"], 'html.parser')
            text = unescape(soup.get_text())
            x.multi_cell(0, 15, text.encode("latin-1", "ignore").decode(errors="ignore"))
            comments[f]["file"] = f'/tmp/{str(uuid.uuid4())}.pdf'
            x.output(name = comments[f]["file"], dest='F')
            reader = PdfReader(comments[f]["file"])
            comments[f]["pages"] = len(reader.pages)
            merger.addpages(reader.pages)

    for f in comments:
        os.remove(comments[f]["file"])

    with open(f"{_id}.pdf", "wb") as output:
        merger.write(output)

    return comments


# Manually add bookmarks
# Add word cloud and title page
# TODO refactor to be better
def post_process(doc, comments):
    x = FPDF(unit="pt")
    x.add_page()
    x.set_font('Arial', style='B', size=40)
    x.multi_cell(550, 100, doc, align='C')
    fil  = f'/tmp/{str(uuid.uuid4())}.pdf'

    with open(f"{doc}.pdf", "rb") as pdf_file:
        reader = pypdf.PdfReader(pdf_file)
        writer = pypdf.PdfWriter()
        text = ""
        page_no = 1
        for page in reader.pages:
            #writer.add_page(page)
            try:
                t = page.extract_text()
                if isinstance(t, pypdf.generic.IndirectObject):
                    continue
                else:
                    text += t 
            except Exception as e:
                print(e)

        wordcloud = WordCloud().generate(text)
        wordcloud.to_file('test.png')
        x.image('test.png', x=100, y=150)
        x.ln(300)
        x.multi_cell(550, 50, f"{len(comments.keys())}\nComments", align='C')
        x.output(name = fil, dest='F')
        input1 = open(fil, "rb")
        writer.append(input1)

        for page in reader.pages:
            writer.add_page(page)

        for f in comments:
            writer.add_outline_item(f, page_no)
            page_no += comments[f]["pages"] 
        
        os.remove(f"{doc}.pdf")
        with open(f"{doc}.pdf", "wb") as output_file:
            writer.write(output_file) 
    input1.close()
    os.remove(fil)

if __name__=="__main__":
    parser = argparse.ArgumentParser(
            prog='retrieve_regulation_comments',
            description='Retrieves comments from the ')
    parser.add_argument('document_id') 
    parser.add_argument('api_key') 
    parser.add_argument('--post-process', action='store_true') 
    parser.add_argument('--no-verify', action='store_false') 
    args = parser.parse_args()
    VERIFY = args.no_verify
    hasNextPage = True
    comments = {} 
    page = 1
    if not args.post_process:
        try:
            while hasNextPage:
                oid = get_document(args.document_id, args.api_key)
                resp = get_comments(oid, args.api_key, page)
                page = page + 1
                hasNextPage = resp["meta"]["hasNextPage"]
                for f in resp["data"]: 
                    author = clean_author(f)
                    if author not in comments:
                        comments[author] = { "count" : 0 }
                    else:
                        comments[author]["count"] += 1
                        author = f"{author} {comments[author]['count']}"
                        comments[author] = {}
                    comments[author]["url"] = f["links"]["self"]

        except RuntimeError:
            print("Couldn't communicate with regulations.gov API")
            sys.exit(-1)

        comments = merge_comments(process_comments(comments, args.api_key), args.document_id, args.api_key)
    post_process(args.document_id, comments)
