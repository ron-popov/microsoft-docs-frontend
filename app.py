from flask import Flask, send_file, url_for, request

import subprocess
import json
import os

app = Flask(__name__)

ROOT_ABSOLUTE_PATH = r"D:\MSDN-Scrape\httrack\MSND-PSAPI"
SEARCH_DIR_PATH = r"D:\MSDN-Scrape\httrack\MSND-PSAPI\docs.microsoft.com"

def return_page_not_found():
	return send_file('404-page.html'), 404

### Handlers
@app.errorhandler(404)
def page_not_found(error):
   return return_page_not_found()

@app.route("/")
def index_page():
	return send_file(os.path.join(ROOT_ABSOLUTE_PATH, "index.html"))

@app.route("/<path:subpath>")
def default_html_page(subpath):
	try:
		return send_file(os.path.join(ROOT_ABSOLUTE_PATH, subpath))
	except:
		return return_page_not_found()

# Search route
@app.route("/en-us/search/index")
def index_search():
	return send_file("search-page.html")


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
	json_dict = {
		"facets": {
			"products":[],
			"category":[]
		},
		"results": []
	}

	# Run the search
	# search_output = subprocess.check_output("grep -c -i -R {text} {search_dir}".format(text=search_string, search_dir=SEARCH_DIR_PATH))
	# print(len(search_output))

	json_dict["results"].append(create_search_result("Popov rules", "/", "https://fake-url.com", "this is how i am awesome"))
	json_dict["results"].append(create_search_result("Another seach result", "/", "https://fake-url.com", "this is how i am awesome"))

	return json.dumps(json_dict)