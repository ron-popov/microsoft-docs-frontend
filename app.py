from flask import Flask, send_file, request, render_template, Response

from whoosh import index
from whoosh.fields import Schema, TEXT
from whoosh.qparser import QueryParser

import json
import pathlib
import os
import re

try:
	from BeautifulSoup import BeautifulSoup
except:
	from bs4 import BeautifulSoup

# Consts
ROOT_ABSOLUTE_PATH = r"D:\MSDN-Scrape\sdk-api-docs\sdk-api-src\content"
SEARCH_DIR_PATH = r"D:\MSDN-Scrape\httrack\MSND-PSAPI\docs.microsoft.com\en-us\windows\win32\psapi"
SEARCH_DIR_PATH = r"D:\MSDN-Scrape\sdk-api-docs\sdk-api-src\content\psapi"
WHOOSH_INDEX_DIR = r"whoosh-index"
TITLE_IN_MARKDOWN_PAGE_REGEX = r"title: (.*)\n"

CUSTOM_MIME_TYPES = {
	"js": "text/javascript",
	"css": "text/css"
}


app = Flask(__name__)
app.ix = None

### Initialize search engine
@app.before_first_request
def init_search_engine():
	schema = Schema(
		title=TEXT(stored=True),
		content=TEXT(stored=True),
		path=TEXT(stored=True)
	)

	try:
		import shutil
		shutil.rmtree(WHOOSH_INDEX_DIR)
	except:
		pass

	if not os.path.exists(WHOOSH_INDEX_DIR):
		os.mkdir(WHOOSH_INDEX_DIR)
		app.ix = index.create_in(WHOOSH_INDEX_DIR, schema)
		writer = app.ix.writer()

		for root, _, files in os.walk(SEARCH_DIR_PATH):
			for name in files:
				md_path = os.path.join(root, name)

				if not md_path.endswith(".md"):
					continue

				try:
					mardown_page_content = open(os.path.join(SEARCH_DIR_PATH, md_path), "r").read()
				except:
					mardown_page_content = ""
				title, content = parse_md_page(md_path, mardown_page_content)
				writer.add_document(title=title, content=content, path=os.path.join(SEARCH_DIR_PATH, md_path))

		writer.commit()
	else:
		app.ix = index.open_dir(WHOOSH_INDEX_DIR)

def parse_md_page(md_path, md_content):
	title_result = re.search(TITLE_IN_MARKDOWN_PAGE_REGEX, md_content)
	if title_result is None or len(title_result.groups()) != 1:
		app.logger.error("Failed finding title for {}".format(md_path))
		return "", ""

	title = title_result.groups()[0]
	app.logger.info("Found title for {}".format(md_path))
	return title, ""




### General Handlers
@app.errorhandler(404)
def page_not_found(error):
	return send_file('static/html/404-page.html'), 404

@app.route("/")
def index_page():
	return send_file("static/html/search-page.html")

@app.route("/static/styles/<path:subpath>")
def serve_css(subpath):
	try:
		return send_file(os.path.join("static", "styles", subpath), mimetype='text/css')
	except:
		return send_file('static/html/404-page.html'), 404

@app.route("/static/js/<path:subpath>")
def serve_javascript(subpath):
	try:
		return send_file(os.path.join("static", "js", subpath), mimetype='text/javascript')
	except:
		return send_file('static/html/404-page.html'), 404

@app.route("/<path:subpath>")
def default_html_page(subpath):
	return render_template("view.html")



### Search engine routes
@app.route("/en-us/search/index")
def index_search():
	return send_file("static/html/search-page.html")


def create_search_result(title, url, display_url, description):
	return {
			"title":title,
			"url": url,
			"displayUrl":{
				"content":display_url,
				"hitHighlights":[
					
				]
			},
			"description":description,
			"descriptions":[
				{
					"content":description,
					"hitHighlights":[
						{
							"start":0,
							"length":0
						}
					]
				}
			],
			"lastUpdatedDate":"2000-01-01T00:00:00+00:00",
			"breadcrumbs":[
				
			]
		}

@app.route("/api/search")
def api_search_call():
	search_string = request.args.get("search", default=None, type=str)

	if search_string is None or search_string == "":
		return ""

	json_dict = {
		"facets": {
			"products":[],
			"category":[]
		},
		"results": []
	}

	if app.ix is None:
		raise Exception("Index is not initialized")

	qp = QueryParser("title", schema=app.ix.schema)
	q = qp.parse(search_string)

	with app.ix.searcher() as searcher:
		# for x in searcher.documents():
		# 	print(x)

		results = searcher.search(q)

		for result in results:
			web_server_path = os.path.relpath(result["path"], ROOT_ABSOLUTE_PATH)
			json_dict["results"].append(
				create_search_result(
					result["title"], 
					os.path.relpath(result["path"], ROOT_ABSOLUTE_PATH),
					os.path.relpath(result["path"], SEARCH_DIR_PATH), 
					"description"
				)
			)

	return json.dumps(json_dict)
