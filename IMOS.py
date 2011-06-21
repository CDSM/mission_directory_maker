#!/usr/bin/env python
#
# -- Colorado Denver South Mission --
#  -    IMOS Data Grabber Class    -
#
import time, sys, os
import socket, httplib, urllib, urllib2, form_grabber
import BeautifulSoup, csv
import ho.pisa as pisa

###
# Config
###
LOGIN_URL = "https://apps.lds.org/imos/security/j_stack_security_check"
POST_URL  = "https://apps.lds.org/imos/index.jsf"
ORGANIZATIONS_URL = "https://apps.lds.org/imos/mission/organization/index.jsf"
MAX_RETRIES = 5

#!# End Config #!#

# super cool debug function
def display_dict(dictionary, header):
    print "-" * 50
    print "- %s" % header
    print "-" * 50
    for key in dictionary.keys():
        print "'%s' => '%s'" % (key, dictionary[key])
        print
    print "-" * 50
    print

class session:
    def __init__(self, username, password):
        """
        Initialize IMOS session class
        """
        self.__username = username
        self.__password = password
        self.__opener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        self.__opener.addheaders = [('User-agent', 'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT)')]
        self.__logged_in = False
        self.__view_state = ""

    def __get_doc(self, url):
        """
        Return HTML string contents of a given URL
        """
        for i in range(0, MAX_RETRIES):
            try:
                page = self.__opener.open(url).read()
                return page
            except urllib2.URLError:
                time.sleep(3)
            except httplib.BadStatusLine or httplib.InvalidURL:
                time.sleep(3)
            except socket.error or socket.timeout:
                time.sleep(3)
            except:
                import traceback
                traceback.print_exc()
                count += 1
        raise NameError("Failed to grab URL: %s", url)

    def __show_status(self, message):
        """
        Print line to console without \n
        """
        sys.stdout.write("[+] %s, " % message)
        sys.stdout.flush()

    def login(self):
        """
        Log in to IMOS
        Returns True if successful, or False if unsuccessful
        """

        # Grab the login page, and then parse out the FORM data
        self.__show_status("Getting login page")
        page = self.__get_doc(LOGIN_URL)
        action_url, data = form_grabber.process_form(page, LOGIN_URL)
        data["j_username"] = self.__username
        data["j_password"] = self.__password
        data["j_submit"] = "Sign In"
        print "Done"

        # Prepare the login request and try logging in
        self.__show_status("Attempting login")
        data = urllib.urlencode(data)
        request = urllib2.Request(action_url, data)
        response = self.__get_doc(request)
        print "Done"

        # Process the server's response
        if "Sign Out" not in response:
            return False
        self.__logged_in = True

        # get view_state variable
        view_state = response.split("name=\"javax.faces.ViewState\"")[1]
        view_state = view_state.split("value=\"")[1].split("\"")[0]
        self.__view_state = view_state

        return True

    def __get_area_specific_info(self, area_id, count):
        self.__show_status("--> Getting area meta information")
        post_data = {"listForm": "listForm",
                    "javax.faces.ViewState": self.__view_state,
                    "listForm:j_id103:%d:aLink" % count: "listForm:j_id103:%d:aLink" % count,
                    "areaId": area_id}
        post_data = urllib.urlencode(post_data)
        request = urllib2.Request(ORGANIZATIONS_URL, post_data)
        response = self.__get_doc(request)
        soup = BeautifulSoup.BeautifulSoup(response)

        # get phone number
        phone_number = ""
        for input in soup.findAll("input"):
            if not input.has_key("id"):
                continue
            input_id = input["id"]
            if input_id.endswith("phoneNumberInput"):
                phone_number = input["value"]
                phone_number = phone_number.replace("-", "")
                phone_number = phone_number.replace(" ", "")
                phone_number = phone_number.replace("(", "")
                phone_number = phone_number.replace(")", "")
                phone_number = phone_number.strip()
        # get car_id
        car_id = soup.findAll("textarea")[0].string
        car_id = car_id.strip()
        if car_id == "No Car":
            car_id = ""
        print "Done"

        return phone_number, car_id

    def __write_csv(self, file_name, areas):
        self.__show_status("Writing information to CSV file")
        rows = ["area id", "name", "phone number", "car id", "district", "zone"]

        file = open(file_name, "wb")
        writer = csv.writer(file)
        writer.writerow(rows)
        for area in areas:
            writer.writerow([area["id"], area["name"], area["phone"],
                             area["car_id"], area["district"], area["zone"]])
        file.close()

        print "Done"

    def __clean_up_phone_number(self, string):
        # pad the string with 0s until it's at least 10 digits
        while len(string) < 10:
                string = "0%s" % string
        string_list = list(string)
        string_list.reverse()
        string = "".join(string_list)

        index = 0
        output_number = ""
        for char in string:
                output_number = "%s%s" % (char, output_number)
                if index == 3:
                        output_number = "-%s" % output_number
                elif index == 6:
                        output_number = ") %s" % output_number
                elif index == 9:
                        output_number = "(%s" % output_number
                index += 1

        return output_number

    def dump_areas_info(self):
        if not self.__logged_in:
            if not self.login():
                raise NameError("Failed to log in, check credentials and try again.")

        self.__show_status("Getting areas list")
        post_data = {"landingPageForm": "landingPageForm",
                    "javax.faces.ViewState": self.__view_state,
                    "landingPageForm:organization": "landingPageForm:organization"}
        post_data = urllib.urlencode(post_data)
        request = urllib2.Request(POST_URL, post_data)
        response = self.__get_doc(request)
        soup = BeautifulSoup.BeautifulSoup(response)
        print "Done"

        # get view_state variable
        view_state = response.split("name=\"javax.faces.ViewState\"")[1]
        view_state = view_state.split("value=\"")[1].split("\"")[0]
        self.__view_state = view_state

        self.__show_status("Processing areas table")
        areas = []
        table = soup.findAll("table")[0]
        rows = table.findAll("tr")
        for row in rows[2:]:
            values = []
            columns = row.findAll("td")
            for column in columns:
                link_tag = column.findAll("a")[0]
                # get text value
                value = link_tag.string
                value = value.split("(")[0]
                value = value.replace("&amp;", "&")
                value = value.strip()
                values.append(value)
                # get areaId variable
                onclick = link_tag["onclick"]
                if "areaId" in onclick:
                    area_id = onclick.split("areaId':'")[1]
                    area_id = area_id.split("'")[0]
                    values.append(area_id)
            if len(values) < 4:
                continue
            area = {}
            area["zone"] = values[0]
            area["district"] = values[1]
            area["name"] = values[2]
            area["id"] = values[3]
            areas.append(area)
        print "Done"

        print "[+] Getting areas information"
        for i in range(len(areas)):
            area = areas[i]
            print "[+] %s (%d/%d)" % (area["name"], i+1, len(areas))
            try:
                phone_number, car_id = self.__get_area_specific_info(area["id"], i)
                area["phone"] = phone_number
                area["car_id"] = car_id
                areas[i] = area
            except:
                area["phone"] = ""
                area["car_id"] = ""
                print "Skipping"

        # dump it all into a CSV!
        self.__write_csv("areas.csv", areas)

    def dump_missionaries_info(self):
        if not self.__logged_in:
            if not self.login():
                raise NameError("Failed to log in, check credentials and try again.")

        # Get missionaries list page
        missionaries_list_url = "https://apps.lds.org/imos/mission/missionaries/missionary-list.jsf"
        self.__show_status("Getting missionaries list")
        response = self.__get_doc(missionaries_list_url)
        soup = BeautifulSoup.BeautifulSoup(response)
        print "Done"

        # get view_state variable
        view_state = response.split("name=\"javax.faces.ViewState\"")[1]
        view_state = view_state.split("value=\"")[1].split("\"")[0]
        self.__view_state = view_state

        # Process missionaries list
        self.__show_status("Processing missionaries list")
        missionaries = []
        table = soup.findAll("table")[0]
        rows = table.findAll("tr")
        for row in rows[2:]:
            columns = row.findAll("td")
            for column in columns:
                missionary = {}
                if not column.findAll("a"):
                    continue
                link_tag = column.findAll("a")[0]
                
                name = link_tag.findAll("strong")
                if not name:
                    continue
                name = str(name)
                name = name.replace("[", "")
                name = name.replace("]", "")
                name = name.replace("<strong>", "")
                name = name.replace("</strong>", "")
                name = name.split(",")
                name = "%s, %s" % (name[0], name[1].split()[0])
                missionary["name"] = name

                # get missionaryId variable
                try:
                    onclick = link_tag["onclick"]
                except:
                    continue

                if "missionaryId" in onclick:
                    missionary_id = onclick.split("missionaryId':'")[1]
                    missionary_id = missionary_id.split("'")[0]
                    missionary["id"] = missionary_id

                listform = onclick.split("listForm:j")[1]
                listform = listform.split("':'")[0]
                listform = "listForm:j" + listform
                missionary["listform"] = listform
                missionaries.append(missionary)
        print "Done"

        # Start processing missionaries list
        print "[+] Processing missionaries!"

        body = "<html>\n<body>"
        body += "<table width=\"100%\" height=\"100%\" border=0 cellpadding=\"5\">\n"
        body += "<tr>\n"

        count = -1
        original_view_state = self.__view_state
        for missionary in missionaries:
            # setup table column
            if count == 3:
                count = -1
                body += "</tr>\n<tr>\n"
            count += 1
            body += "<td align=\"center\">\n"

            # get information page
            name = missionary["name"]
            print "-" * 50
            print "[+] Getting information for %s" % name
            data = {"listForm": "listForm",
                    "listForm:mType": "",
                    "javax.faces.ViewState": original_view_state,
                    missionary["listform"]: missionary["listform"],
                    "missionaryId": missionary["id"]}
            data = urllib.urlencode(data)
            request = urllib2.Request(missionaries_list_url, data)
            response = self.__get_doc(request)
            soup = BeautifulSoup.BeautifulSoup(response)

            # get viewstate
            for tag in soup.findAll("input"):
                if not tag.has_key("name") or tag["name"] != "javax.faces.ViewState":
                    continue
                self.__view_state = tag["value"]
                break

            # get picture
            self.__show_status("Getting missionary's picture")    
            pictures_path = os.path.join(os.path.abspath("."), "missionary_photos")
            if not os.path.exists(pictures_path):
                os.mkdir(pictures_path)
            picture_file_path = os.path.join(pictures_path, "%s.jpg" % missionary["id"])
            if not os.path.exists(picture_file_path):
                picture_tag = soup.findAll("img")[0]
                picture_link = urllib2.urlparse.urljoin("http://apps.lds.org", picture_tag["src"])
                picture_data = self.__get_doc(picture_link)
                picture_file = open(picture_file_path, "wb")
                picture_file.write(picture_data)
                picture_file.close()
            print "Done"

            # get contact info
            self.__show_status("Getting missionary's contact info")
            data = {"missionaryTemplateForm": "missionaryTemplateForm",
                    "javax.faces.ViewState": self.__view_state,
                    "missionaryTemplateForm:contactsTab": "missionaryTemplateForm:contactsTab",
                    "missionaryId": missionary["id"]}
            data = urllib.urlencode(data)
            request = urllib2.Request("https://apps.lds.org/imos/mission/missionaries/profile.jsf", data)
            response = self.__get_doc(request)
            response = response.decode("utf-8")
            soup = BeautifulSoup.BeautifulSoup(response)
            lines = []
            for tag in soup.findAll("address"):
                strtag = str(tag).decode("utf-8")
                if "do not contact" in strtag:
                    continue
                if "Deceased" in strtag:
                    continue
                if len(strtag.split("\n")) < 4:
                    continue
                for line in strtag.split("\n")[2:6]:
                    line = line.strip()
                    line = line.split("<br />")[1]
                    lines.append(line)
                break

            # clean up phone number
            phone_number = lines[3]
            phone_number = phone_number.split("/")[0]
            phone_number = phone_number.split("cell")[0]
            phone_number = "".join(filter(lambda x: x in map(str, range(10)), list(phone_number)))
            if len(phone_number) < 11:
                phone_number = self.__clean_up_phone_number(phone_number)
                lines[3] = phone_number

            address = "<br />\n".join(lines)
            print "Done"

            # get viewstate
            for tag in soup.findAll("input"):
                if not tag.has_key("name") or tag["name"] != "javax.faces.ViewState":
                    continue
                self.__view_state = tag["value"]
                break

            # put out HTML
            body += "<img src=\"%s\" height=\"163\"><br />\n" % picture_file_path
            body += "<p>\n"
            body += "<b>%s</b><br />\n" % missionary["name"]
            body += address
            body += "</p>\n"
            body += "</td>\n"

        body += "</table>\n"
        body += "</body>\n</html>"
        soup = BeautifulSoup.BeautifulSoup(body)
        body = soup.prettify()

        # export PDF versions of stake reports to desktop
        pdf_file_path = "directory.pdf"
        pdf_file_pipe = open(pdf_file_path, "wb")
        pisa.CreatePDF(body, pdf_file_pipe, path=os.path.abspath("."))
        pdf_file_pipe.close()
