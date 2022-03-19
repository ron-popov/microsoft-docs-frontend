from flask import Flask, send_file, request, render_template, Response, redirect

from whoosh import index
from whoosh.fields import Schema, TEXT
from whoosh.qparser import QueryParser

import json
import os
import re
import markdown
import logging

try:
	from BeautifulSoup import BeautifulSoup
except:
	from bs4 import BeautifulSoup

# Consts
ROOT_ABSOLUTE_PATH = r"D:\MSDN-Scrape\docs"
SEARCH_DIR_PATH = r"D:\MSDN-Scrape\docs\psapi"
WHOOSH_INDEX_DIR = r"whoosh-index"
TITLE_IN_MARKDOWN_PAGE_REGEX = r"title: (.*)\n"
DESCRIPTION_IN_MARKDOWN_PAGE_REGEX = r"description: (.*)\n"

CUSTOM_MIME_TYPES = {
	"js": "text/javascript",
	"css": "text/css"
}


app = Flask(__name__)
app.logger.setLevel(logging.DEBUG)

app.ix = None

### Initialize search engine
@app.before_first_request
def init_search_engine():
	schema = Schema(
		title=TEXT(stored=True),
		content=TEXT(stored=True),
		path=TEXT(stored=True),
		description=TEXT(stored=True)
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

		app.logger.info("Started indexing documents")

		failed_titles = 0
		for root, _, files in os.walk(SEARCH_DIR_PATH):
			for name in files:
				md_path = os.path.join(root, name)

				if not md_path.endswith(".md"):
					continue

				try:
					mardown_page_content = open(os.path.join(SEARCH_DIR_PATH, md_path), "r").read()
				except:
					mardown_page_content = ""
				
				# Parse title from md pages
				title = parse_md_title(mardown_page_content)
				if title is None:
					failed_titles += 1
					title = "-Failed Parsing Title-"

				title = title.replace("-", " ")
				title = title.replace("_", " ")

				# Parse description
				description = parse_md_description(mardown_page_content)

				writer.add_document(title=title, content=mardown_page_content, path=os.path.join(SEARCH_DIR_PATH, md_path), description=description)

		app.logger.error("Failed finding title for {} files".format(failed_titles))
		writer.commit()
		app.logger.info("Finished indexing all pages")

		# with app.ix.searcher() as searcher:
		# 	for x in searcher.documents():
		# 		app.logger.debug(x)
	else:
		app.ix = index.open_dir(WHOOSH_INDEX_DIR)
		app.logger.info("Loaded index from existing index")

def parse_md_title(md_content):
	title_result = re.search(TITLE_IN_MARKDOWN_PAGE_REGEX, md_content)
	if title_result is None or len(title_result.groups()) != 1:
		return None

	title = title_result.groups()[0]
	return title

def parse_md_description(md_content):
	description_result = re.search(DESCRIPTION_IN_MARKDOWN_PAGE_REGEX, md_content)
	if description_result is None or len(description_result.groups()) != 1:
		return ""

	description = description_result.groups()[0]
	return description

### Route Handlers
@app.errorhandler(404)
def page_not_found(error):
	return send_file('static/html/404-page.html'), 404

@app.route("/")
def index_page():
	return send_file("static/html/search-page.html")

# @app.route("/en-us/documentation")
# def navbar_documentation():
# 	return redirect("/")

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

def render_content_page(file_path):
	if not file_path.endswith(".md"):
		content = render_content_page(os.path.join(file_path, "index.md"))
		if type(content) != tuple or (type(content) == tuple and content[1] != 404):
			return content
		else:
			file_path = file_path + ".md"

	try:
		markdown_content = open(file_path, "r").read()
	except:
		app.logger.error("Failed opening markdown file {}".format(file_path))
		return send_file('static/html/404-page.html'), 404

	# Remove docs headers from content
	title = parse_md_title(markdown_content)
	headers_end_index = markdown_content.index("---\n\n")
	markdown_content = markdown_content[headers_end_index+5:]

	# Remove annoying dash at the start of title 
	markdown_content = markdown_content.replace("# -", "# ")

	# Make titles smaller
	# markdown_content = markdown_content.replace("\n## ", "\n### ")
	# markdown_content = markdown_content.replace("\n### ", "\n#### ")
	# markdown_content = markdown_content.replace("\n#### ", "\n##### ")
	# markdown_content = markdown_content.replace("\n##### ", "\n###### ")

	html_content = markdown.markdown(markdown_content, extensions=['fenced_code', 'tables'])
	html_content = html_content.replace(u"Â", u" ")

	return render_template("view.html", html_content=html_content, title=title)

@app.route("/<path:subpath>")
def sdk_api_html_page(subpath):
	file_path = os.path.join(ROOT_ABSOLUTE_PATH, subpath)
	return render_content_page(file_path)

@app.route("/windows/win32/<path:subpath>")
def windows_win32(subpath):
	file_path = os.path.join(ROOT_ABSOLUTE_PATH, subpath)
	return render_content_page(file_path)

@app.route("/windows/win32/api/<path:subpath>")
def windows_win32_api(subpath):
	file_path = os.path.join(ROOT_ABSOLUTE_PATH, subpath)
	return render_content_page(file_path)

@app.route("/windows/desktop/api/<path:subpath>")
def windows_desktop_api(subpath):
	file_path = os.path.join(ROOT_ABSOLUTE_PATH, subpath)
	return render_content_page(file_path)

@app.route("/windows/desktop/<path:subpath>")
def windows_desktop(subpath):
	file_path = os.path.join(ROOT_ABSOLUTE_PATH, subpath)
	return render_content_page(file_path)

@app.route("/windows/<path:subpath>")
def windows(subpath):
	file_path = os.path.join(ROOT_ABSOLUTE_PATH, subpath)
	return render_content_page(file_path)

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

	qp = QueryParser("content", schema=app.ix.schema)
	q = qp.parse(search_string)

	with app.ix.searcher() as searcher:
		results = searcher.search(q)

		for result in results:
			target_url = os.path.relpath(result["path"], ROOT_ABSOLUTE_PATH)
			if target_url[0] != "\\":
				target_url = "\\" + target_url

			json_dict["results"].append(
				create_search_result(
					result["title"], 
					target_url,
					target_url[1:],
					"description"
				)
			)

	return json.dumps(json_dict)
