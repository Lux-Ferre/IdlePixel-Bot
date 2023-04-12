from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome(options=chrome_options)
root_page = "https://idle-pixel.com/login/"
driver.get(root_page)
username_field = driver.find_element("id", "id_username")
username_field.send_keys("LuxBot")
password_field = driver.find_element("id", "id_password")
password_field.send_keys("QofhMc78a#5&Hkfc")
password_field.submit()

chat_text_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "chat-area-input"))
    )
action = ActionChains(driver)
action.move_to_element(chat_text_field)
chat_text_field.send_keys("Full Python automation test.")
driver.execute_script("Chat.send()")
driver.close()
