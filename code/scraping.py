# Load main packages and libraries

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
import time
import os
from selenium.common.exceptions import StaleElementReferenceException,NoSuchElementException
import json
import threading
import pathlib

#Execution Timer
start_time = time.time()
DRIVER_PATH = str(pathlib.Path().resolve()) + '/chromedriver.exe'
PATH = str(pathlib.Path().resolve())
PAGE_DELAY_TIME = 30
RESULTS_FILE = PATH + '/results/' + 'result.json'

#Global JSON where i insert of the values at the end of each task
RESULTS_JSON = {}

#HELPER FUNCTION

def textToMinutes(text):
    duration = 0
    split_text = text.split()
    if len(split_text) == 3:
        hourNumbers = [char for char in list(text.split()[0]) if char.isnumeric()]
        hours = int (''.join(hourNumbers))
        minutes = int(text.split()[1])
        duration = (hours * 60) + minutes
    elif len(split_text) == 2:
        duration = int(text.split()[0])
        
    return duration

def create_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument('log-level=3')
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'
    chrome_options.add_argument(f'user-agent={user_agent}')

    service = Service(DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options = chrome_options)
    return driver
    

def on_demand_movies_task(url):
    driver = create_driver()
    driver.get(url)
    
    #Increase window size to get category tab
    driver.set_window_size(1200, 800)
    button = WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.CLASS_NAME, "iconButton")))   
    try:  
        driver.find_elements(By.CLASS_NAME,'iconButton')[1].click()
    except StaleElementReferenceException:
        button = WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.CLASS_NAME, "iconButton")))
        driver.find_elements(By.CLASS_NAME,'iconButton')[1].click()
            
    content = driver.find_element(By.CLASS_NAME,'mainCategory')
    next_section = content.find_element(By.XPATH,'following-sibling::section')
    section_movie_id = driver.current_url.split('on-demand/')[1].split('?')[0]
    next_section.find_element(By.TAG_NAME, 'a').click()
    
    #Set the window small to list movie categories 
    driver.set_window_size(400, 800)
    
    button = driver.find_element(By.XPATH , "//*[@id='overlay-container']/div/div/div[1]/div/div[1]/button")
    button.click()
    categories = driver.find_element(By.CSS_SELECTOR , "ul[aria-label = 'Jump to a category']")
    movie_category_list = categories.find_elements(By.TAG_NAME , "li")
    
    #Grab the Ids if each movie category
    movies_categories_ids_list = {}
    for element in movie_category_list:
        category_movie_id = element.find_element(By.TAG_NAME, 'div').get_attribute('data-id')
        category_movie_name = element.find_element(By.TAG_NAME, 'div').find_element(By.TAG_NAME, 'span').text
        if category_movie_id not in movies_categories_ids_list:
            movies_categories_ids_list[category_movie_name] = category_movie_id
            
    actions = ActionChains(driver)
    movies_list = []

    #Go through each movie category and grab the movies, with the general id of movie and the specific movie link i can grab each element
    for name, link in movies_categories_ids_list.items():
        path = 'https://pluto.tv/latam/on-demand/' + section_movie_id + '/' + link + '?lang=en'
        driver.get(path)
        WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.CLASS_NAME,'reset-ul')))
        tags = driver.find_element(By.CLASS_NAME, 'custom-scroll').find_elements(By.TAG_NAME,'p')
        #The page displays the amount of titles in each category
        if len(tags) > 1:
            num_movies = int(tags[1].text.split('Titles')[0].strip())
        else:
            WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.CLASS_NAME,'custom-scroll')))
            tags = driver.find_element(By.CLASS_NAME, 'custom-scroll').find_elements(By.TAG_NAME,'p')
            num_movies = int(tags[1].text.split('Titles')[0].strip())
            
        movies = driver.find_element(By.CLASS_NAME,'reset-ul').find_elements(By.TAG_NAME,'li')
        minimun_found = num_movies - 2 # buffer of 2 in case the number of movies found in the page listed doesn't match the real amount of movies foun
        actions.send_keys(Keys.TAB + Keys.TAB + Keys.TAB + Keys.TAB + Keys.TAB + Keys.TAB).perform()
        for _ in range(int(num_movies)):
            actions.send_keys(Keys.PAGE_DOWN + Keys.PAGE_DOWN + Keys.PAGE_DOWN + Keys.PAGE_DOWN).perform()
            movies = driver.find_element(By.CLASS_NAME,'reset-ul').find_elements(By.TAG_NAME,'li')
            
        #I make sure that amount of movies found match is between the buffer and the items found
        assert minimun_found <= len(movies) <= num_movies
        for idx in range(len(movies)):
            movies = driver.find_element(By.CLASS_NAME,'reset-ul').find_elements(By.TAG_NAME,'li')
            movies[idx].find_element(By.TAG_NAME, 'a').click()
            WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.CLASS_NAME,'custom-scroll')))
            movie_link = driver.current_url
            if '/series/' in movie_link:
                # TODO - treat it as a series
                driver.back()
                continue
            movie_id = movie_link.split('/details')[0].split('/movies/')[1]
            movie_data = driver.find_element(By.CLASS_NAME, 'custom-scroll').find_element(By.CLASS_NAME,'inner')
            movie_title = movie_data.find_element(By.XPATH,"//*[@id='overlay-container']/div/div/div/section/div/div[1]").text
            movie_title = movie_title.split('\n')[0]
            movie_summary = movie_data.find_element(By.TAG_NAME, 'p').text
            movie_information = movie_data.find_elements(By.TAG_NAME,"li")
            movie_information = [info for info in movie_information if info.text != '']
            noRatingFlag = False
            movie_rating_check = movie_data.find_elements(By.CLASS_NAME, 'rating')
            if movie_rating_check:
                movie_rating = movie_data.find_element(By.CLASS_NAME, 'rating').text
            else:
                movie_genre = movie_information[0].text
                movie_duration = movie_information[1].text
                noRatingFlag = True
            if noRatingFlag == False:
                movie_genre = movie_information[1].text
                movie_duration = textToMinutes(movie_information[2].text)
            
            movie = {}
            movie['id'] = movie_id
            movie['title'] = movie_title
            movie['link'] = movie_link
            movie['genre'] = movie_genre
            movie['runtime'] = movie_duration
            movie['rating'] = movie_rating
            movie['summary'] = movie_summary
            
            print('MOVIE_TASK: adding movie ' + movie_title)
            movies_list.append(movie)
            driver.back()
        
    RESULTS_JSON['movies'] =  movies_list   
    driver.quit()    
    print('MOVIE_TASK: finished movie task')       
 

def on_demand_series_task(url):
    driver = create_driver()
    driver.get(url)
    
    #Increase window size to get category tab
    driver.set_window_size(1200, 800)
    button = WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.CLASS_NAME, "iconButton")))     
    try:  
        driver.find_elements(By.CLASS_NAME,'iconButton')[2].click()
    except StaleElementReferenceException:
        button = WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.CLASS_NAME, "iconButton")))
        driver.find_elements(By.CLASS_NAME,'iconButton')[2].click()
    
    driver.set_window_size(400, 800)
    content = driver.find_element(By.CLASS_NAME,'mainCategory')
    next_section = content.find_element(By.XPATH,'following-sibling::section')
    try:
        section_series_id = driver.current_url.split('on-demand/')[1].split('?')[0]
        next_section.find_element(By.TAG_NAME, 'a').click()
    except:
        content = driver.find_element(By.CLASS_NAME,'mainCategory')
        next_section = content.find_element(By.XPATH,'following-sibling::section')
        section_series_id = driver.current_url.split('on-demand/')[1].split('?')[0]
        next_section.find_element(By.TAG_NAME, 'a').click()
    
    button = driver.find_element(By.XPATH , "//*[@id='overlay-container']/div/div/div[1]/div/div[1]/button")
    button.click()
    categories = driver.find_element(By.CSS_SELECTOR , "ul[aria-label = 'Jump to a category']")
    series_category_list = categories.find_elements(By.TAG_NAME , "li")
    
    series_categories_ids_list = {}
    for element in series_category_list:
        category_series_id = element.find_element(By.TAG_NAME, 'div').get_attribute('data-id')
        category_series_name = element.find_element(By.TAG_NAME, 'div').find_element(By.TAG_NAME, 'span').text
        if category_series_id not in series_categories_ids_list:
            series_categories_ids_list[category_series_name] = category_series_id
            
    actions = ActionChains(driver)
    series_list = []

    for name, link in series_categories_ids_list.items():
        path = 'https://pluto.tv/on-demand/' + section_series_id + '/' + link + '?lang=en'
        driver.get(path)
        WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.CLASS_NAME,'reset-ul')))
        tags = driver.find_element(By.CLASS_NAME, 'custom-scroll').find_elements(By.TAG_NAME,'p')
        if len(tags) > 1:
            num_series = int(tags[1].text.split('Titles')[0].strip())
        else:
            WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.CLASS_NAME,'custom-scroll')))
            tags = driver.find_element(By.CLASS_NAME, 'custom-scroll').find_elements(By.TAG_NAME,'p')
            num_series = int(tags[1].text.split('Titles')[0].strip())
            
        series_container = driver.find_element(By.CLASS_NAME,'reset-ul').find_elements(By.TAG_NAME,'li')
        minimun_found = num_series - 2
        actions.send_keys(Keys.TAB + Keys.TAB + Keys.TAB + Keys.TAB + Keys.TAB + Keys.TAB).perform()
        for i in range(int(num_series)):
            actions.send_keys(Keys.PAGE_DOWN + Keys.PAGE_DOWN + Keys.PAGE_DOWN + Keys.PAGE_DOWN).perform()
            series_container = driver.find_element(By.CLASS_NAME,'reset-ul').find_elements(By.TAG_NAME,'li')
            
        assert minimun_found <= len(series_container) <= num_series
        for idx in range(len(series_container)):
            series_container = driver.find_element(By.CLASS_NAME,'reset-ul').find_elements(By.TAG_NAME,'li')
            series_container[idx].find_element(By.TAG_NAME, 'a').click()
            WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.CLASS_NAME,'custom-scroll')))
            series_link = driver.current_url
            if '/movies/' in series_link:
                # TODO 
                driver.back()
                continue
            #Lots of try, except, i found the elements got stale very fast
            series_id = series_link.split('/season')[0].split('/series/')[1].split('/details')[0]
            try:
                series_data = driver.find_element(By.CLASS_NAME,'custom-scroll').find_element(By.CLASS_NAME,'inner')
            except StaleElementReferenceException:
                series_data = driver.find_element(By.CLASS_NAME,'custom-scroll').find_element(By.CLASS_NAME,'inner')
            
            try:
                series_title = series_data.find_element(By.XPATH,"//*[@id='overlay-container']/div/div/div/section/div/div[1]").text
                series_title = series_title.split('\n')[0]
            except StaleElementReferenceException:
                series_data = driver.find_element(By.CLASS_NAME,'custom-scroll').find_element(By.CLASS_NAME,'inner')
                series_title = series_data.find_element(By.XPATH,"//*[@id='overlay-container']/div/div/div/section/div/div[1]").text
                series_title = series_title.split('\n')[0]
            try:
                series_summary = series_data.find_element(By.XPATH, '//*[@id="overlay-container"]/div/div/div/section/div/div[1]/section/p').text
            except StaleElementReferenceException:
                series_data = driver.find_element(By.CLASS_NAME,'custom-scroll').find_element(By.CLASS_NAME,'inner')
                series_summary = series_data.find_element(By.XPATH, '//*[@id="overlay-container"]/div/div/div/section/div/div[1]/section/p').text
            try:
                series_information = series_data.find_elements(By.TAG_NAME,"li")
                series_information = [info for info in series_information if info.text != '']
            except StaleElementReferenceException:
                series_data = driver.find_element(By.CLASS_NAME,'custom-scroll').find_element(By.CLASS_NAME,'inner')
                series_information = series_data.find_elements(By.TAG_NAME,"li")
                series_information = [info for info in series_information if info.text != '']

            try:
                series_rating_check = series_data.find_elements(By.CLASS_NAME, 'rating')
            except StaleElementReferenceException:
                series_data = driver.find_element(By.CLASS_NAME,'custom-scroll').find_element(By.CLASS_NAME,'inner')
                series_rating_check = series_data.find_elements(By.CLASS_NAME, 'rating')
            if series_rating_check:
                try:
                    series_rating = series_data.find_element(By.CLASS_NAME, 'rating').text
                    series_genre = series_information[1].text
                except StaleElementReferenceException: 
                    series_data = driver.find_element(By.CLASS_NAME,'custom-scroll').find_element(By.CLASS_NAME,'inner')
                    series_rating = series_data.find_element(By.CLASS_NAME, 'rating').text
                    series_information = series_data.find_elements(By.TAG_NAME,"li")
                    series_information = [info for info in series_information if info.text != '']
                    series_genre = series_information[1].text
            else:
                series_rating = ''
                series_genre = series_information[0].text
            
            series_select_dropdown = driver.find_element(By.CLASS_NAME,'season-select')
            series_episodes = WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.TAG_NAME,'option')))
            series_episodes = driver.find_elements(By.TAG_NAME,'option')
            series_num = len(series_episodes)
            
            series = {}
            series['id'] = series_id
            series['title'] = series_title
            series['link'] = series_link
            series['genre'] = series_genre
            series['seasons'] = series_num
            series['rating'] = series_rating
            series['summary'] = series_summary
            series['episodes'] = []
            
            
            for selected_season in series_episodes:
                selected_season.click()
                episode_container = driver.find_element(By.XPATH,'//*[@id="overlay-container"]/div/div/div/section/div/div[1]/div[4]/section')
                episodes = episode_container.find_elements(By.CLASS_NAME,'episode-container-atc')
                for episode in episodes:
                    episode_json = {}
                    episode_link = episode.find_element(By.TAG_NAME,'a').get_attribute('href')
                    episode_name = episode.find_element(By.CLASS_NAME,'episode-name-atc').text
                    episode_description = episode.find_element(By.CLASS_NAME,'episode-description-atc').text
                    episode_id = episode.find_element(By.CLASS_NAME,'episode-metadata-atc').find_elements(By.TAG_NAME,'span')[0].text
                    season_number = int(episode_id.split('E')[0].split('S')[1])
                    episode_number = int(episode_id.split('E')[1])
                    episode_duration = textToMinutes(episode.find_element(By.CLASS_NAME,'episode-metadata-atc').find_elements(By.TAG_NAME,'span')[1].text)
                
                    episode_json['id'] = episode_id
                    episode_json['link'] = episode_link
                    episode_json['episode_name'] = episode_name
                    episode_json['summary'] = episode_description
                    episode_json['season'] = season_number
                    episode_json['episode'] = episode_number
                    episode_json['runtime'] = episode_duration
                    
                    series['episodes'].append(episode_json)   
            print('SERIES_TASK: adding series ' + series_title)       
            series_list.append(series)
            for _ in range(series_num):
                driver.back()
        
    RESULTS_JSON['series'] =  series_list  
    driver.quit()  
    print('SERIES_TASK: finished series task')  

         
def on_demand_liveTV_task(url):
    driver = create_driver()
    driver.get(url)
    driver.set_window_size(1200, 800)
    
    categories = WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.XPATH, "//*[@id='root']/div/div/div/main/div[2]/div/section/div[2]/ul")))
    list_categories = WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.TAG_NAME, 'li')))
    list_categories = categories.find_elements(By.TAG_NAME, 'li')
    last_category = list_categories[-1].text
    
    driver.set_window_size(400, 800)
    
    ## Since a coudln't find a fixed reference point to finish the loop, i do a scroll down of the page until i found the last category while counting the number of loops needed
    section = WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div/div/main/div[2]/div/div[2]/section/div[3]/div/div[2]')))
    for i in range(500):
        driver.execute_script('arguments[0].scrollTop = arguments[0].scrollTop + 80;',section)
        try:
            category = driver.find_element(By.CLASS_NAME, 'category').text
        except (NoSuchElementException,StaleElementReferenceException):
            pass
        if category == last_category:
            break
    num_loops = i

    driver.set_window_size(1200, 800)
    WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.XPATH,'//*[@id="root"]/div/div/div/main/div[2]/div/section/div[2]/ul/li[1]/div/button'))).click()
    driver.set_window_size(400, 800)
    WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.CLASS_NAME,'channel')))

    list_channels = []
    channel_name_list = []
    # i add 20 more loops to get the items in the last category
    for _ in range(num_loops + 20):
        channel_ids = []
        channels = driver.find_elements(By.CLASS_NAME,'channel')
        idx = 0
        ## i grab all the channel data-id in the current view
        for channel in channels:
            try:
                channel_id = channel.find_element(By.CLASS_NAME,"ChannelInfo-Link").get_attribute('data-id')
                channel_ids.append(channel_id)
                idx += 1
            except StaleElementReferenceException:
                channels = driver.find_elements(By.CLASS_NAME,'channel')
                channel_id = channels[idx].find_element(By.CLASS_NAME,"ChannelInfo-Link").get_attribute('data-id')
                channel_ids.append(channel_id)
        ## using each of this ids I loop trough every channel and get the data
        for channel_id in channel_ids:
            channel_dict = {}
            shows = {}
            try:
                link = driver.find_element(By.CSS_SELECTOR,"a[data-id ='" + channel_id +"']")
            except NoSuchElementException:
                continue
            channel_name = link.find_element(By.XPATH, 'ancestor::*[2]').find_element(By.CLASS_NAME,'image').get_attribute('aria-label')
            channel_dict['channel_name'] = channel_name
            if channel_name not in channel_name_list:
                channel_name_list.append(channel_name)
            else:
                # If i already have the channel, i skip this loop
                continue
            channel_dict['link'] = link.get_attribute('href')
            for i in range(24):
                try:
                    right_button = driver.find_element(By.CLASS_NAME,'right').find_element(By.TAG_NAME,'button')
                    right_button.click()
                except NoSuchElementException:
                    return_button = driver.find_element(By.XPATH, '//*[@id="root"]/div/div/div/main/div[2]/div/div[2]/section/div[2]/div[1]/span[2]/div/button')
                    return_button.click()
                grids = link.find_element(By.XPATH, 'parent::node()').find_element(By.XPATH, 'following-sibling::*[1]').find_elements(By.CSS_SELECTOR,"div[role='gridcell']")
                for grid in grids:
                    try:
                        show_name = grid.find_element(By.CLASS_NAME, 'name-container').text
                        show_time = grid.find_element(By.CLASS_NAME, 'time').text
                        if show_name == '':
                            continue
                        shows[show_time] = show_name
                        channel_dict['timeline'] = shows
                        #print(shows)
                    except:
                        continue  
            list_channels.append(channel_dict)  
            print('LIVE_TV_TASK: adding channel ' + channel_name)
        # Once i finished all the channels in the current view, I scroll down and continue
        section = WebDriverWait(driver,PAGE_DELAY_TIME).until(EC.presence_of_element_located((By.XPATH, '//*[@id="root"]/div/div/div/main/div[2]/div/div[2]/section/div[3]/div/div[2]')))
        driver.execute_script('arguments[0].scrollTop = arguments[0].scrollTop + 80;',section)
        
    RESULTS_JSON['live_tv'] =  list_channels
    driver.quit()
    print('LIVE_TV_TASK: finished live_tv task') 
    
results_file = pathlib.Path(RESULTS_FILE)
if results_file.is_file():
    os.remove(RESULTS_FILE)

# Splitted the scraping process in 3 tasks, on-demand movies, on-demand series and the live-tv section
threads = []   
th1 = threading.Thread(target=on_demand_movies_task, args=('https://pluto.tv/on-demand',))
th2 = threading.Thread(target=on_demand_series_task, args=('https://pluto.tv/on-demand',))
th3 = threading.Thread(target=on_demand_liveTV_task, args=('https://pluto.tv/live-tv/',))
th1.start()
th2.start()
th3.start()
threads.append(th1)
threads.append(th2)
threads.append(th3)

for th in threads:
    th.join() # Main thread wait for threads finish
    


with open(RESULTS_FILE, 'w', encoding='latin1') as fp:
    json.dump(RESULTS_JSON, fp)

minutes = (time.time() - start_time) / 60
finish_time = 'Execution took ' + str(int(minutes)) + ' minutes'

with open(PATH + 'results/execution_time.txt', 'w') as fp:
    fp.write(finish_time)


