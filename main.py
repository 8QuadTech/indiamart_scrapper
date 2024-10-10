from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
import random
import pandas as pd
import os

def random_delay(min_delay=1, max_delay=5):
    return random.uniform(min_delay, max_delay)

def human_like_scroll(driver):
    total_height = driver.execute_script("return document.body.scrollHeight")
    viewport_height = driver.execute_script("return window.innerHeight")
    current_position = 0
    while current_position < total_height:
        scroll_step = random.randint(100, 800)
        current_position += scroll_step
        driver.execute_script(f"window.scrollTo(0, {current_position});")
        time.sleep(random_delay(0.1, 0.3))

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36"
    ]
    return random.choice(user_agents)

chrome_options = Options()
# chrome_options.add_argument("--remote-debugging-port=9222")
chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
chrome_options.add_argument(f"user-agent={get_random_user_agent()}")
chrome_options.add_argument("referer=https://www.google.com/")

chrome_driver_path = r'C:\Users\pgawa\OneDrive\Desktop\DoveTailLabs\MVP\sarvesh\distributor\apollo\universal_scrapper\backend\chromedriver.exe'
service = Service(chrome_driver_path)

def is_element_in_viewport(driver, element):
    return driver.execute_script("""
        var elem = arguments[0];
        var rect = elem.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    """, element)

def click_button_safely(driver, button):
    try:
        button.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", button)

def exponential_backoff(attempt, max_attempts=3, base_delay=1):
    if attempt >= max_attempts:
        return False
    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
    time.sleep(delay)
    return True

def scroll_to_button(driver, button):
    driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", button)
    time.sleep(random_delay(0.5, 1.5))


def get_category_sellers(category_name, category_url):
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(category_url)
    time.sleep(random_delay())
    try:
        attempt = 0
        while True:
            try:
                # Look for the "Show more results" button
                show_more_button = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Show more results')]"))
                )            
                # Scroll to the button
                scroll_to_button(driver, show_more_button)            
                # Check if the button is clickable
                show_more_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Show more results')]"))
                )            
                click_button_safely(driver, show_more_button)
                # print("Clicked 'Show more results' button")            
                time.sleep(random_delay(2, 4))
                attempt = 0        
            except (TimeoutException, NoSuchElementException):
                if not exponential_backoff(attempt):
                    # print("'Show more results' button not found. All results may be loaded.")
                    break
                attempt += 1        
            except Exception as e:
                print(f"An error occurred: {e}")
                if not exponential_backoff(attempt):
                    break
                attempt += 1
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    page_content = driver.page_source
    soup = BeautifulSoup(page_content, 'html.parser')
    soup_filtered = soup.find_all('div', class_='card brs5')
    with open('data/html/'+category_name+'.html', 'w', encoding='utf-8') as file:
        for item in soup_filtered:
            file.write(item.prettify())
            file.write('\n')  # Add a newline between each item for better readability
    driver.quit()
    return soup_filtered

def get_category_csv(category_name, category_url):
    soup_filtered = get_category_sellers(category_name, category_url)
    df = pd.DataFrame(columns=['product_title', 'product_link', 'company_name', 'company_link', 'is_verified_exporter', 'city_region', 'city', 'address_details', 'phone_number', 'phone_number_extension'])
    for item in soup_filtered:
        product_info = item.find('div', class_='producttitle')
        product_link = product_info.find('a', class_='cardlinks')['href'] if product_info.find('a', class_='cardlinks') and 'href' in product_info.find('a', class_='cardlinks').attrs else None
        product_title = product_info.text.strip() if product_info else None
        company_info = item.find('div', class_='companyname')
        company_link = company_info.find('a', class_='cardlinks')['href'] if company_info.find('a', class_='cardlinks') and 'href' in company_info.find('a', class_='cardlinks').attrs else None
        company_name = company_info.text.strip() if company_info else None
        is_verified_exporter = True if 'IndiaMART Verified Exporter' in company_name else False
        company_name = company_name.replace('IndiaMART Verified Exporter', '').strip() if is_verified_exporter else company_name
        address_info = item.find('div', class_='newLocationUi')
        #<div class="newLocationUi fs11 clr7 lh12 flx100 pr db-trgt tac dib"><div class="dib pr to-txt-gn"><span class="elps elps1">Goregaon West, <!-- -->Mumbai<!-- --> </span><span class="to-txtnw db-src lft" id="citytt1"><span class="db to-txt-area lh16 tal"><p class="tac wpw">904 A Wing,9 Th Floor,Triple S Heights,Jakeria Road, Goregaon West, Mumbai - 400064, Dist.Mumbai, Maharashtra</p></span></span></div></div>
        locality = address_info.find('span', class_='elps elps1').text.strip() if address_info.find('span', class_='elps elps1') else None
        if len(locality.split(',')) == 2:
            locality_region = locality.split(',')[0].strip()
            city = locality.split(',')[1].strip()
        else:
            locality_region = None
            city = locality
        address_details = address_info.find('span', class_='db to-txt-area lh16 tal').text.strip() if address_info.find('span', class_='db to-txt-area lh16 tal') else None
        phone_info = item.find('p', class_='contactnumber')
        phone_number = phone_info.find('span', class_='pns_h duet fwb').text.strip() if phone_info and phone_info.find('span', class_='pns_h duet fwb') else None
        phone_number_extension = phone_number.split(',')[1].strip() if phone_number and len(phone_number.split(',')) > 1 else None
        phone_number = phone_number.split(',')[0].strip() if phone_number else None
        df_temp = pd.DataFrame({
            'product_title': [product_title],
            'product_link': [product_link],
            'company_name': [company_name],
            'company_link': [company_link],
            'is_verified_exporter': [is_verified_exporter],
            'city_region': [locality_region],
            'city': [city],
            'address_details': [address_details],
            'phone_number': [phone_number],
            'phone_number_extension': [phone_number_extension]
        })
        df = pd.concat([df, df_temp], ignore_index=True)
    df.to_csv('data/csv/'+category_name+'.csv', index=False)

#"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:/chrome_dev"


# get all category data
url = 'https://dir.indiamart.com/indianexporters/baby.html'
def get_all_category_names(url):
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)
    time.sleep(random_delay())
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    soup_filtered = soup.find_all('div', class_='prow showp-new isbd5 pr')
    soup_filtered_mod = []
    for item in soup_filtered:
        soup_filtered_mod += [x.text.strip() for x in item.find_all('a', class_='slink')]
    return soup_filtered_mod

category_ls = [{'name': name, 'url': 'https://dir.indiamart.com/search.mp?ss='+name.replace(' ', '+')} for name in get_all_category_names(url)]


for category in category_ls:
    already_saved = [x.split('.')[0] for x in os.listdir('data/csv/')]
    if category['name'] not in already_saved:
        print(category['name'], 'started')
        get_category_csv(category_url=category['url'], category_name=category['name'])
        print(category['name'], 'completed')

