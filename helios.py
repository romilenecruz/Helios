import xml.etree.ElementTree as ET #importing the parsing tool ElementTree as the variable ET
from array import *
import requests, zipfile, io, os, glob, pprint
from datetime import datetime, timedelta
import RPi.GPIO as GPIO
from time import sleep


#####################################################################################################################################
######################################## Setting up Raspberry Pi GPiOS ##############################################################
#####################################################################################################################################


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(16, GPIO.OUT)
GPIO.setup(20, GPIO.OUT)
GPIO.setup(21, GPIO.OUT)
GPIO.setup(26, GPIO.OUT)


#####################################################################################################################################
######################################## Constructing the CAISO query URL ############################################################
#####################################################################################################################################


next_day = datetime.now() +  timedelta(+1) #getting the date for the next day
tomorrow = next_day.strftime('%Y%m%d') #storing the next day in the variable 'tomorrow' with the format YYYddMM (the format CAISO uses for the query)
path = "E:/As of 11.17.2020/School/2021 Spring/EE 496/Energy Management System/Project Code/" #where the file will be stored, will be different for the Raspberry Pi


start_url = "http://oasis.caiso.com/oasisapi/SingleZip?queryname=PRC_LMP&" #beginning of the URL, does not change


start_date = "startdatetime=" #part of the URL that will tell CAISO what the start date is


start_time = "T00:00-0000&" #start time, does not change


end_date = "enddatetime=" #part of the URL that will tell CAISO what the end date is


end_time = "T23:00-0000&" #end time, does not change


end_url = "&version=1&market_run_id=DAM&node=STREAMVW_6_N001" #end of the URL, does not change unless you want to change the node


CAISO_query = start_url + start_date + tomorrow + start_time + end_date + tomorrow + end_time + end_url #constucting the whole URL


#####################################################################################################################################
######################################## Getting the .xml file from CAISO ###########################################################
#####################################################################################################################################


r = requests.get(CAISO_query) #using python requests to access the URL, content stored in the variable 'r'
z = zipfile.ZipFile(io.BytesIO(r.content)) #get the .zip file from 'r' and store it in 'z'
z.extractall() #extract the contents of that .zip file which is an .xml file, using this method doesn't save the intial .zip file, just the .xml file that was inside



list_of_files = glob.glob(path + '*xml') #from our list of files in the path, only pull the files that end with .xml


latest_file = max(list_of_files, key=os.path.getctime) #pull that latest .xml file we downloaded


#####################################################################################################################################
#################################################### Sunrise-Sunset API #############################################################
#####################################################################################################################################


sdsu_lat = "32.7760" #latitude of SDSU
sdsu_long = "-117.0713" #longitude of SDSU


sun_api_date_format = next_day.strftime('%Y-%m-%d') #format of date for Sunrise-Sunset API


sun_api_start = "https://api.sunrise-sunset.org/json?" #start of the Sunrise-Sunset API URL


sun_api_lat = "lat=" #part of the URL that will tell Sunset-Sunrise what the latitude is


sun_api_long = "&lng=" #part of the URL that will tell Sunset-Sunrise what the longitude is


sun_api_date = "&date=" #part of the URL that will tell Sunset-Sunrise what the date is


sun_api_url = sun_api_start + sun_api_lat + sdsu_lat + sun_api_long + sdsu_long + sun_api_date + sun_api_date_format #constucting the Sunset-Sunrise API URL


y = requests.get(sun_api_url) #using python requests to access the URL, content stored in the variable 'y'


#####################################################################################################################################
############################################ Manipulating Sunrise-Sunset API Data ###################################################
#####################################################################################################################################


sunrise = pprint.pformat(y.json()['results']['sunrise']) #using pprint to parse thorugh JSON data and pulling the sunrise information
sunset = pprint.pformat(y.json()['results']['sunset']) #using pprint to parse thorugh JSON data and pulling the sunset information


sun_up_casted = str(sunrise) #casting sunrise as a string


sun_down_casted = str(sunset) #casting sunset as a string


sun_up_left_text = sun_up_casted.partition(":")[0] #partitioning the sun_up_casted string by ':' and getting the data from 0th index (returns 'hour)
sun_up_right_text = sun_up_left_text.partition("'")[2] #partitioning 'hour by "'" and getting data from the 2nd index (returns hour)


sun_down_left_text = sun_down_casted.partition(":")[0] #partitioning the sun_down_casted string by ':' and getting the data from 0th index (returns 'hour)
sun_down_right_text = sun_down_left_text.partition("'")[2] #partitioning 'hour by "'" and getting data from the 2nd index (returns hour)


sun_up_hour = int(sun_up_right_text) # casting hour as an int
sun_down_hour = int(sun_down_right_text) #casting hour as an int


sun_up = sun_up_hour-7 #convert sunrise time to PST 24 hour format


midnight = 12
sun_down = midnight - (7 - sun_down_hour) + 12 #convert sunset time to PST 24 hour format


#########################################################################################################################################
################################################ Pulling data from the weather.gov API ##################################################
#########################################################################################################################################


s = requests.get('https://api.weather.gov/gridpoints/SGX/59,15/forecast') #weather.gov API URL


clouds = "Mostly Cloudy" #weather type inside weather.gov API
rain = "Chance Rain Showers" #weather type inside weather.gov API
good_weather = "Sunny" #weather type inside weather.gov API


weather_day = [] #empty weather_day list
weather_type = [] #empty weather_type list


x = 0 #initiating x


while x < 14: #while loop to iterate x through the weather.gov API JSON data


    day = s.json()['properties']['periods'][x]['name'] #getting the day
    expected = s.json()['properties']['periods'][x]['shortForecast'] #getting the expected weather
    weather_day.append(day) #putting the day into the weather_day list
    weather_type.append(expected) #putting the expected weather into the weather_type list
    x += 1 #inrementing x by 1


zipped = list(zip(weather_day, weather_type)) #zipping weather day and weather type into one list


tomorrow_weather = weather_type.pop(2) #popping data in 2nd index, returns tomorrows forecast


#####################################################################################################################################
########################################### Pulling the correct data from the CAISO .xml file #######################################
#####################################################################################################################################


tree = ET.parse(latest_file) #pulling the .xml file and storing it in 'tree'
root = tree.getroot() #need this to access everything in the XML file


temp_time = [] #temp array for the time aka the interval hour
time = [] #new arary for the time with only the time of the LMP


temp_cost = [] #temp array for the cost aka the value
cost = [] #new array for the cost with only the cost of the LMP
sort_cost = [] #array for the sorted LMP price


for elm in root.findall(".//{http://www.caiso.com/soa/OASISReport_v1.xsd}REPORT_DATA"): #go into the REPORT_DATA


   if elm.find("{http://www.caiso.com/soa/OASISReport_v1.xsd}DATA_ITEM").text == "LMP_PRC": #find the tag called DATA_ITEM and if the text inside is LMP_PRC continue
      
      hour = elm.find(".//{http://www.caiso.com/soa/OASISReport_v1.xsd}INTERVAL_NUM").text #go into the INTERVAL_NUM to get the hour of the day
      price = elm.find(".//{http://www.caiso.com/soa/OASISReport_v1.xsd}VALUE").text #find the price of energy


      temp_time.append(hour) #put hour into list
      temp_cost.append(price) #put price into list



os.remove(latest_file) #delete the .xml file because we got the data from it already


#####################################################################################################################################
############################################ Sorting the pulled data from CAISO #####################################################
#####################################################################################################################################


time = [int(x) for x in temp_time] #casting the time into an int whilst putting it into a new list called time
cost = [float(x) for x in temp_cost] #casting the cost into a float whilst putting it into a new list called cost
sort_cost = [float(x) for x in temp_cost] #casting the cost into a float whilst putting it into a new list called sort_list


sort_cost.sort() #sort the sort_cost list


high_threshold = sort_cost.pop(19) #set the high threshold to the sorted cost in the 19th position


low_threshold = sort_cost.pop(4) #set the low threshold to the sorted cost in the 4th position


combined = list(zip(time, cost)) #combine the time and cost lists into a 2D list


sorted_list = sorted(combined) #sort the combined list


#####################################################################################################################################
############################################ Using all the data for the EMS algorithm ###############################################
#####################################################################################################################################


if good_weather in tomorrow_weather: # if there are no clouds or rain in the forecast
   print("Power plan for " + next_day.strftime('%m/%d/%Y'))
   print("There will be a lot of solar production today.\n")
   print("Hour by hour breakdown: ")


   for t, c in sorted_list: #for the time, hour in the sorted list
      if t >= sun_up and t < sun_down:
         if c >= high_threshold:
            print(f'Hour {t}')
            print(" ---> The sun is out.")
            print(" ---> High threshold of", high_threshold, "passed.")
            print(" ---> Use batteries to power load.")
            print(" ---> Contacts 1, 3, 4 open and Contact 2 shut.\n")
            GPIO.output(26, GPIO.LOW)
            GPIO.output(20, GPIO.LOW)
            GPIO.output(21, GPIO.LOW)
            GPIO.output(16, GPIO.HIGH)
            sleep(2)


         elif c <= low_threshold:
            print(f'Hour {t}')
            print(" ---> The sun is out.")
            print(" ---> Low threshold of", low_threshold, "not passed.")
            print(" ---> Charge the batteries using grid.")
            print(" ---> Contacts 2, 3 open and Contacts 1, 4 shut.\n")


         else:
            print(f'Hour {t}')
            print(" ---> The sun is out.")
            print(" ---> Solar panels generating enery and grid is powering house.")
            print(" ---> Contacts 1, 2, 4 open and Contact 3 shut.\n")           


      else:
         if c >= high_threshold:
            print(f'Hour {t}')
            print(" ---> The sun is not out.")
            print(" ---> High threshold of", high_threshold, "passed.")
            print(" ---> Use batteries to power load.")
            print(" ---> Contacts 1, 3, 4 open and Contact 2 shut.\n")
            GPIO.output(26, GPIO.LOW)
            GPIO.output(20, GPIO.LOW)
            GPIO.output(21, GPIO.LOW)
            GPIO.output(16, GPIO.HIGH)
            sleep(2)


         elif c <= low_threshold:
            print(f'Hour {t}')
            print(" ---> The sun is not out.")
            print(" ---> Low threshold of", low_threshold, "not passed.")
            print(" ---> Charge the batteries using grid.")
            print(" ---> Contacts 2, 3 open and Contacts 1, 4 shut.\n")


         else:
            print(f'Hour {t}')
            print(" ---> The sun is not out.")
            print(" ---> Solar panels generating energy and grid is powering house.")
            print(" ---> Contacts 1, 2, 4 open and Contact 3 shut.\n")


else:
   print("Today is " + next_day.strftime('%m/%d/%Y'))
   print("There will not be a lot of solar production today\n")
   print("Hour by hour breakdown: ")
   
   for t, c in sorted_list: #for the time, hour in the sorted list
      if t >= sun_up and t < sun_down:
         if c >= high_threshold:
            print(f'Hour {t}')
            print(" ---> The sun is out.")
            print(" ---> High threshold of", high_threshold, "passed.")
            print(" ---> Use batteries to power load.")
            print(" ---> Contacts 1, 3, 4 open and Contact 2 shut.\n")
            GPIO.output(26, GPIO.LOW)
            GPIO.output(20, GPIO.LOW)
            GPIO.output(21, GPIO.LOW)
            GPIO.output(16, GPIO.HIGH)
            sleep(2)


         elif c <= low_threshold:
            print(f'Hour {t}')
            print(" ---> The sun is out.")
            print(" ---> Low threshold of", low_threshold, "not passed.")
            print(" ---> Charge the batteries using grid.")
            print(" ---> Contacts 2, 3 open and Contacts 1, 4 shut.\n")
            GPIO.output(16, GPIO.LOW)
            GPIO.output(20, GPIO.LOW)
            GPIO.output(26, GPIO.HIGH)
            GPIO.output(21, GPIO.HIGH)
            sleep(2)


         else:
            print(f'Hour {t}')
            print(" ---> The sun is out.")
            print(" ---> Solar panels generating energy and grid is powering house.")
            print(" ---> Contacts 1, 2, 4 open and Contact 3 shut.\n")    
            GPIO.output(21, GPIO.LOW)
            GPIO.output(16, GPIO.LOW)
            GPIO.output(21, GPIO.LOW)
            GPIO.output(20, GPIO.HIGH)
            sleep(2)       


      else:
         if c >= high_threshold: #if c is greater than or equal to our threshold, then print out the statement
            print(f'Hour {t}')
            print(" ---> The sun is not out.")
            print(" ---> High threshold of", high_threshold, "passed.")
            print(" ---> Use batteries to power load.")
            print(" ---> Contacts 1, 3, 4 open and Contact 2 shut.\n")
            GPIO.output(26, GPIO.LOW)
            GPIO.output(20, GPIO.LOW)
            GPIO.output(21, GPIO.LOW)
            GPIO.output(16, GPIO.HIGH)
            sleep(2)


         elif c <= low_threshold:
            print(f'Hour {t}')
            print(" ---> The sun is not out.")
            print(" ---> Low threshold of", low_threshold, "not passed.")
            print(" ---> Charge the batteries using grid.")
            print(" ---> Contacts 2, 3 open and Contacts 1, 4 shut.\n")
            GPIO.output(16, GPIO.LOW)
            GPIO.output(20, GPIO.LOW)
            GPIO.output(26, GPIO.HIGH)
            GPIO.output(21, GPIO.HIGH)
            sleep(2)


         else:
            print(f'Hour {t}')
            print(" ---> The sun is not out.")
            print(" ---> Solar panels generating energy and grid is powering house.")
            print(" ---> Contacts 1, 2, 4 open and Contact 3 shut.\n")
            GPIO.output(21, GPIO.LOW)
            GPIO.output(16, GPIO.LOW)
            GPIO.output(21, GPIO.LOW)
            GPIO.output(20, GPIO.HIGH)
            sleep(2)
            
