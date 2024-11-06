import shutup
shutup.please()
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Button, Static
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
import json
from pprint import pprint
import json
import requests
import time
import lingua 
import ast
from ml_things import clean_text
from lingua import Language, LanguageDetectorBuilder
from emotionextractor.emotionextractor import EmotionExtractor
from googletrans import Translator
import logging
import subprocess

from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Input, Button, Static
from textual.reactive import reactive
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Button, Static

from playwright.sync_api import sync_playwright
from mpire import WorkerPool
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

from playwright.sync_api import sync_playwright
import warnings
warnings.filterwarnings("ignore")


def get_description_from_url(url: str):
    description = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Go to the target URL
            page.goto(url, wait_until="domcontentloaded", timeout=2000)
            
            # Attempt to retrieve the meta description content
            description_element = page.locator("meta[name='description']")
            if description_element.count() > 0:
                description = description_element.get_attribute("content")
            else:
                # If no meta description, try getting the first paragraph as a fallback
                paragraph_element = page.locator("p")
                if paragraph_element.count() > 0:
                    description = paragraph_element.first.text_content()
        
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            browser.close()
    
    return description

def getAllLanguages(sentence):
    ee = EmotionExtractor()
    translator = Translator()
    detector =  LanguageDetectorBuilder.from_all_languages().build()
    
    confidence_values = detector.compute_language_confidence_values(sentence)
    # print(dir(detector))
    confidence_map = {}
    for confidence in confidence_values:
        confidence_map[confidence.language.name] =confidence.value
    
    rv = []
    english_sentence = ""
    queries = []
    for result in detector.detect_multiple_languages_of(sentence):
        sent = clean_text(sentence[result.start_index:result.end_index],full_clean=True)
        translation = translator.translate(sent)
        translation_text = translation.text
        english_sentence += f" {translation_text}"
        queries.append(translation_text)
        rv.append({result.language.name:{"score":confidence_map[result.language.name],'sentence':sent,'translation_sentence':translation_text,'emotion':ee.extract_emotion(translation_text,clean_stopwords=False,strict_mode=False)}})
    return {"out":rv,'completely_translated_sentence':" ".join(queries)}


def second_level_search(list_of_urls):
    with ThreadPoolExecutor(max_workers=15) as executor:
        # Fetch descriptions concurrently
        descriptions = list(executor.map(get_description_from_url, list_of_urls))

        # Extract information from each description concurrently
        # results = list(executor.map(extract__one_url_sync, descriptions))
        results = list(executor.map(lambda url_desc: extract__all_url_sync(url_desc[0], url_desc[1]),
                                     zip(list_of_urls, descriptions)))
    return results[0]

# Define the synchronous Playwright function
def extract__all_url_sync(curr_url: str,query: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        urls = []
        try:
            page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=2000)

            # Accept cookies if present
            if page.locator("button:has-text('I agree')").count() > 0:
                page.locator("button:has-text('I agree')").click()

            # Fill in the search query
            search_input = page.locator("textarea[name='q']")
            search_input.fill(query)
            search_input.press("Enter")

            # Wait for search results to load
            page.wait_for_selector("a:has(h3)", timeout=2000)

            # Extract URLs from search results
            for element in page.locator("a:has(h3)").all():
                url = element.get_attribute("href")
                if url and url!=curr_url:
                    urls.append(url)
                    

        except Exception as e:
            return f"An error occurred: {e}"
        finally:
            browser.close()
    return urls
    

# Define the synchronous Playwright function
def extract_single_url_sync(query: str):
    urls = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            page.goto("https://www.google.com", wait_until="domcontentloaded", timeout=2000)

            # Accept cookies if present
            if page.locator("button:has-text('I agree')").count() > 0:
                page.locator("button:has-text('I agree')").click()

            # Fill in the search query
            search_input = page.locator("textarea[name='q']")
            search_input.fill(query)
            search_input.press("Enter")

            # Wait for search results to load
            page.wait_for_selector("a:has(h3)", timeout=2000)

            # Get only the first URL in the search results
            first_result = page.locator("a:has(h3)").first
            first_url = first_result.get_attribute("href")
            if first_url:
                urls.append(first_url)

        except Exception as e:
            urls.append(f"An error occurred: {e}")
        finally:
            browser.close()

    # Get the emotion analysis and prepare output
    out_Dict = {
        "emotion_detector": getAllLanguages(query),
        "first_level_search": urls,  # Only one URL
        "second_level_search": second_level_search(urls)  # Pass first level URL to fetch related URLs
    }
    return out_Dict

# Second level search remains unchanged, as it is already set up to fetch all URLs



# Define the Textual app
class SearchApp(App):
    def __init__(self):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=1)  # Thread pool for running Playwright
    
    def compose(self) -> ComposeResult:
        yield VerticalScroll(
            Input(placeholder="Type your query here...", id="input_field"),
            Button("Search", id="search_button"),
            # Button("Close App", id="close_button"),
            Static("", id="results_display", expand=True),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search_button":
            input_field = self.query_one("#input_field", Input)
            query = input_field.value.strip()

            if query:
                # Run the synchronous Playwright function in a separate thread
                future = self.executor.submit(extract_single_url_sync, query)
                future.add_done_callback(self.display_results)
        elif event.button.id == "close_button":
            self.exit() 
        

    def display_results(self, future):
        results = future.result()
        display_widget = self.query_one("#results_display", Static)
        pretty_json = json.dumps(results, indent=4)
        display_widget.update(pretty_json)

    def on_exit(self) -> None:
        self.executor.shutdown(wait=True)

if __name__ == "__main__":

    app = SearchApp()
    app.run()
