import os
import re
import json
import arxiv
import yaml
import logging
import argparse
import datetime
import requests
import subprocess
import time

logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)

base_url = "https://arxiv.paperswithcode.com/api/v0/papers/"
github_url = "https://api.github.com/search/repositories"
arxiv_url = "http://arxiv.org/"

def load_config(config_file:str) -> dict:
    def pretty_filters(**config) -> dict:
        keywords = dict()
        def parse_filters(filters:list):
            return ' OR '.join(f'"{f}"' if ' ' in f else f'"{f}"' for f in filters)
        for k,v in config['keywords'].items():
            keywords[k] = parse_filters(v['filters'])
        return keywords

    with open(config_file,'r') as f:
        config = yaml.load(f,Loader=yaml.FullLoader) 
        config['kv'] = pretty_filters(**config)
        logging.info(f'config = {config}')
    return config 

def get_authors(authors, first_author = False):
    return authors[0] if first_author else ", ".join(str(author) for author in authors)

def sort_papers(papers):
    return {k: papers[k] for k in sorted(papers.keys(), reverse=True)}

def get_code_link(qword:str) -> str:
    params = {"q": qword, "sort": "stars", "order": "desc"}
    r = requests.get(github_url, params=params)
    results = r.json()
    return results["items"][0]["html_url"] if results["total_count"] > 0 else None

def get_daily_papers(topic, query="slam", max_results=2):
    content, content_to_web = dict(), dict()

    for retry in range(5):
        try:
            client = arxiv.Client(num_retries=2, delay_seconds=3)
            search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.SubmittedDate)
            for result in client.results(search):
                paper_id = result.get_short_id()
                paper_title = result.title
                paper_url = result.entry_id
                code_url = base_url + paper_id
                paper_abstract = result.summary.replace("\n"," ")
                paper_authors = get_authors(result.authors)
                paper_first_author = get_authors(result.authors,first_author=True)
                publish_time = result.published.date()
                update_time = result.updated.date()

                logging.info(f"Time = {update_time} title = {paper_title} author = {paper_first_author}")

                ver_pos = paper_id.find('v')
                paper_key = paper_id if ver_pos == -1 else paper_id[:ver_pos]    
                paper_url = arxiv_url + 'abs/' + paper_key

                try:
                    r = requests.get(code_url).json()
                    repo_url = r.get("official", {}).get("url")
                except Exception:
                    repo_url = None

                content[paper_key] = f"|**{update_time}**|**{paper_title}**|{paper_first_author} et.al.|[{paper_key}]({paper_url})|{'**[link](' + repo_url + ')**' if repo_url else 'null'}|\n"
                content_to_web[paper_key] = f"- {update_time}, **{paper_title}**, {paper_first_author} et.al., Paper: [{paper_url}]({paper_url})" + (f", Code: **[{repo_url}]({repo_url})**\n" if repo_url else "\n")

            return {topic:content}, {topic:content_to_web}

        except Exception as e:
            logging.warning(f"Retry {retry + 1}/5 for topic {topic} failed: {e}")
            time.sleep(5)

    raise RuntimeError(f"Failed to get papers for topic {topic} after 5 retries.")

# main block remains unchanged
def demo(**config):
    data_collector = []
    data_collector_web = []

    keywords = config['kv']
    max_results = config['max_results']
    publish_readme = config['publish_readme']
    publish_gitpage = config['publish_gitpage']
    publish_wechat = config['publish_wechat']
    show_badge = config['show_badge']

    b_update = config['update_paper_links']
    logging.info(f'Update Paper Link = {b_update}')
    if not b_update:
        logging.info(f"GET daily papers begin")
        for topic, keyword in keywords.items():
            logging.info(f"Keyword: {topic}")
            try:
                data, data_web = get_daily_papers(topic, query=keyword, max_results=max_results)
                data_collector.append(data)
                data_collector_web.append(data_web)
            except Exception as e:
                logging.error(f"Failed to get papers for {topic}: {e}")
            time.sleep(8)  # 防止触发 arXiv 限流
        logging.info(f"GET daily papers end")

    # 以下略，保持原逻辑
    # ...
