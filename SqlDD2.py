#!/usr/bin/env python3

import re
import json
import csv
from easygui import *
import sys
from tqdm import tqdm
import os
from colorama import Fore
from pathlib import Path


#maybe add function for good only, only get
#csv.field_size_limit(sys.maxsize) #add this to get around issue of having too many chars in CSV cell
maxInt = sys.maxsize

while True:
    # decrease the maxInt value by factor 10
    # as long as the OverflowError occurs.

    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt/10)
"""
the code above might result in the following error: OverflowError: Python int too large to convert to C long. 
To circumvent this, you could use the following quick and dirty code (which should work on every system with Python 2 and Python 3):

import sys
import csv
maxInt = sys.maxsize

while True:
    # decrease the maxInt value by factor 10 
    # as long as the OverflowError occurs.

    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt/10)

"""


"""everythings seems to work well
 Tested on sql dumps that have multiple tables and multiple delimiters in values, those w/ and w/o line breaks
 WHat it does:
 1. opens file and scans X num of lines to determine encoding
 2. opens file with that Encoding and identified all the tables in the SQL dump
 3. If not tables, runs new function to grab data and figure out the tables
 4. if one table, grabs all data from table with that table name and out puts to file
 5. If more than one table found, allows user to choose table and then goes table by table and extracts data, adds to list and converts to json
 6. dumps file with proper encoding

POSSIBLE NEW WAY TO DELIMIT FILES
ok=[newline]
next(csv.reader(ok,delimiter=",",doublequote=False,strict=True, quotechar="'", skipinitialspace=True))

TO DO:
1. parse keys/headers for term "email", "username" etc and add tag at end of table name in GUI indicating as much
 Issues
 1. put tables with terms account, user, member, etc up first
  when ran linear sql chose cutomer_entity but there were multiple tables with that in name #think i fie=xed this by adding all the and target_table in line and target_table + "_" not in line #nope still something ip
 but maybe close enough
 Todo: would be great if when offered table selection, gave you first line of the table, but thats PITA
 """

def tableSelectGUI(tablenames,filename):
    tablecount = str(len(tablenames))
    msg = f"Found {tablecount} tables in {Path(filename).name}. Select Ones You want to Extract (best looking ones at top)"
    title = "Table Selection"
    iwant = ["account", "member", "user","admins","clients","customers"]
    tablenames.sort()
    upfirst = [x for x in tablenames if any(y in x for y in iwant)] #put tables with info i like up first
    tot = upfirst + tablenames
    choices = sorted(set(tot), key=tot.index) #get rid of duplicates while preserving order
    #choices = tablenames
    choice = multchoicebox(msg, title, choices,preselect=None)
    return choice

typelist  = ["email","username","alias","ipaddress","ip_address"]
regexp = re.compile(r"\),\((?=(?:[^']*'[^']*')*[^']*$)") #use this to get instance of "),(", change capturing groupthat aren't within a record so can determine if looking at list of records on one line, or one record per line. See here for getting rid of captured groups so only match on full match https://stackoverflow.com/questions/31915018/re-findall-behaves-weird/31915134#31915134
valregex = re.compile(r" values ?\(",re.IGNORECASE) #re.compile(r"\) values ",re.IGNORECASE) q mark matches space 0 or 100 times
valregex2 = re.compile(r" values \(",re.IGNORECASE)


def SQLtoJson(filename,ENCODING,FORMAT="json",dumpall=False):
    def find_tables(dump_filename):  # this works
        print(f"Getting tables from {Path(dump_filename).name}")
        table_list = []
        othertables = ""

        with open(dump_filename, 'r', encoding=ENCODING,errors='replace') as f:
            count = 0
            for line in tqdm(f,desc=f"Parsing..."):

                line = line.strip()
                if line.startswith('INSERT ') or line.startswith('insert  into'): #took out the lowr as found one sql file where some lines began with insert as name or paswword and added special circumstance for badly dumped dql
                    othertables = "Yup"
                if line.lower().startswith('create table'):
                    # print (line)
                    # newline = line
                    line = line.replace("IF NOT EXISTS ","").replace("&quot;","`") #get rid of those term so below regex works

                    table_name = re.findall('create table `([\w_]+)`', line,flags = re.IGNORECASE)
                    if not table_name:
                        table_name = re.findall('create table ([\w_]+)', line,flags = re.IGNORECASE)
                    table_list.extend(table_name)
                elif line.lower().startswith('truncate table'):#uniqueish case found with "minecraftjunkie.sql" #remove if causing issues elsewhere
                    table_name = re.findall('truncate table ([\w_]+)', line.lower())
                    table_list.extend(table_name)

                count+=1
        table_list = list(set(table_list))
        if len(table_list) >0:
            print (F"Found {Fore.LIGHTBLUE_EX}{str(len(table_list))} {Fore.RESET}tables:")
        table_list.sort()
        #for y in table_list:
         #   print(F"\t{y}")
        return (table_list,othertables)

    tables,othertables = find_tables(filename)

    def read_dump(dump_filename, target_table,dumbdump=False):

        #print (F"Grabbing values for table: {target_table}")
        with open(dump_filename,'r',encoding=ENCODING,errors='replace') as f: #sometimes there are stupid encoding issues where certain char cant be read by encoder, so fuck em
            read_mode = 0  # 0 - skip, 1 - header, 2 - data, 3 - data

            headers = []
            items = []
            values = []
            for line in tqdm(f,desc=f"Parsing {Fore.LIGHTBLUE_EX}{target_table}{Fore.RESET} table"):
                #if read_mode !=0:
                 #   print(str(read_mode))
                try:
                    line = line.strip()
                    #have issues with common tablenames like users where that word is in that line so really need proximity search or maybe search just first x characters, added [:50] fuck yes, seems to work
                    #having issues where common term
                    #get your headers
                    # get your values
                    if dumbdump:
                        if line.strip().startswith("("):
                            if regexp.search(line):
                                # if '),(' in line:  # when sql dump is not line seperated
                                read_mode = 2  # print(line) #dont think need these read modes anymore but kept as legacy just in case
                                # continue

                            else:
                                read_mode = 3
                    else:
                        if line.lower().startswith('insert') and target_table in line.split("(", 1)[0][
                                                                                 :50] and target_table + "_" not in line.split("(",1)[0] and "_"+target_table not in line.split("(",1)[0]:
                            splitline = line.split(target_table)[1]
                            splitfirst = line.split(target_table)[0]
                            if not splitline or not splitline[0].isdigit() and not splitline[0].isalpha() and (
                                    not splitfirst[-1].isdigit() and not splitfirst[
                                -1].isalpha()):  # take care of when have targetable accounts and dont want values from tables called accounts1 or useraccounts
                                if regexp.search(line):
                                #if '),(' in line:  # when sql dump is not line seperated
                                    read_mode = 2  # print(line) #dont think need these read modes anymore but kept as legacy just in case
                                    # continue

                                else:
                                    read_mode = 3
                                #continue

                    if line.lower().startswith('create table') and target_table in line and target_table + "_" not in line.split("(",1)[0] and "_"+target_table not in line.split("(",1)[0]: # the "_" gets rid of false positives like target_table_1 etc but not target_table1
                        splitline = line.split(target_table)[1]
                        splitfirst = line.split(target_table)[0]
                        if not splitline or not splitline[0].isdigit() and not splitline[0].isalpha() and (not splitfirst[-1].isdigit() and not splitfirst[-1].isalpha()):
                            read_mode =1

                            continue
                                #values.append(line) testing
                    if read_mode==0:
                        continue
                    elif read_mode==1:
                        if line.lower().startswith('primary'):
                            # add more conditions here for different cases
                            #(e.g. when simply a key is defined, or no key is defined)
                            read_mode=0
                            continue
                        elif line.lower().startswith(")"): #added this to deal with desking, w/o worked fien for other ones
                            read_mode=0
                            continue
                        #print (line)
                        #colheader = re.findall('`([\w_]+)`',line) #old version, only grabs header if in quotes
                        colheader = re.findall('^([^ \t]+).*',line)
                        for col in colheader:
                            headers.append(col.strip("'").strip("`"))
                    # Filling up the headers

                            #if line.endswith(';'):
                             #   break
                    elif read_mode ==2:
                        if line.lower().startswith('insert') and target_table in line[
                                                                                 :50] and target_table + "_" not in line.split("(",1)[0]:
                            #print("AL")
                            data =re.split(valregex,line,1)[1].strip("\n\r;") #max split of 1
                            #data = line.split(" VALUES ", 1)[1]  #

                            #data = re.split(regexp,data) #for some reason doesnt work properly in file encontrame.sql
                            data = data.split("),(")
                            data = [x.replace('`', '').strip(" (").strip(") ") for x in data]
                            #print("BC")
                            for y in data:
                                #print("Adding line")
                                newline = y.replace('`', '').replace("\t", "")
                                newline = re.sub("(?<!, (?<=))\\\\'(?!, ')", "&quot ",
                                                 newline)  # may need to change back to just 2 backslahes for some #get rid of single quotation makrs unless preceded by , or followed by for some reason replacing every quotation mark when //' not present ,

                                #newline = y.replace('`', '').replace("\t", "").replace("\\'", "&quot ")
                                newline = newline.strip(" ()\"")
                                newline = re.split(r",(?=(?:[^\']*\'[^\']*\')*[^\']*$)",
                                                   newline)  # another regex variation that may work better that split on comma only if comma not inside single quotes from https://stackoverflow.com/questions/18893390/splitting-on-comma-outside-quotes
                                thing1 = [x.replace('\0', '') for x in newline]  # elimate null bytes
                                thing1 = [x.strip("'").replace("&quot ", "'").replace("\\\\","") for x in thing1] #add back in quote chars and remove slashes now that line hopefully parse and split properly
                                # y = [y]
                                # thing = next(csv.reader(y, quotechar="'", skipinitialspace=True))
                                values.append(thing1)
                                #print("line added")
                    elif read_mode ==3:
                        if line.lower().startswith('insert') and target_table in line[
                                                                                 :50] and target_table + "_" not in line.split("(",1)[0] and line.endswith(
                            "VALUES"):
                            pass
                        else:
                            # if line.endswith(";"): #added this if/else clause to deal with desking issue where script was getting values of all table sfor some reason, but then I lose last entry in table
                            #   read_mode=0
                            #  continue
                            # else:
                            line = line.strip("\t,")
                            if valregex2.search(line):
                                line = re.split(valregex, line, 1)[1]
                                #line = line.split(") VALUES ", 1)[1]
                            if line.strip()[0]=="(" or "VALUES (" in line or "VALUES(" in line:
                                data = re.findall('\((.*\))', line)  # get everythign between first and last occurance of parens
                            else:
                                data = [line] #for times when no parens oustide valies (rare)
                            try:
                                if len(
                                        data) > 1:  # for tht etime swhere you have insert values wih all headers before the value sto be inserted, this doesnt matter anymore as getting all data bwn first and last parens
                                    newline = data[1]
                                else:
                                    newline = data[0]
                                newline = newline.replace('`', '').replace("\t", "").replace("\\\\","").replace("\\'", "&quot ")

                                newline = newline.strip(
                                    " ()\"")  # .replace("\\'","") #added second replace to get rid of escaped single quotation marks that were fucking up when split values. Originally split on commas but that was whole thing too
                                # and now have issue with values like 'cjvhcvjcvc\\' need something that searches for
                                # newline = next(csv.reader(newline,   skipinitialspace=True))#quotechar="'", removed quotechar for now as having too many issues with internal single quote issues, but now having issue where splits on comma inside

                                # newline = re.split(r", (?=(?:'[^']*?(?: [^']*)*))|, (?=[^',]+(?:,|$))", newline) #using regex to avoid issue with single quote and comma splits
                                newline = re.split(r",(?=(?:[^\']*\'[^\']*\')*[^\']*$)",
                                                   newline)  # another regex variation that may work better that split on comma only if comma not inside single quotes from https://stackoverflow.com/questions/18893390/splitting-on-comma-outside-quotes
                                # newline = [newline]
                                thing1 = [x.replace('\0', '') for x in newline]  # elimate null bytes
                                thing1 = [x.strip(" '") for x in thing1]
                                values.append(thing1)
                                # need to

                                #These lines may not be needed anymore. messed up some other files. we'll see. nope still need it
                                if line.endswith(";") and not line.startswith(
                                        "INSERT INTO"):  # added this if/else clause to deal with desking issue where script was getting values of all table sfor some reason, when added it above  I lose last entry in table, so now add it here so add data to list but after switch read-mode. Added extra line startswith cond as realized that when have insert into statements all the way down, those end with semi-colon
                                    read_mode = 0
                                    continue



                            except IndexError:
                                pass
                            except Exception as e:
                                print(F"{line} fucked up because {str(e)}")
                                print(read_mode)
                                break
                except Exception as e:
                    print(line[:100],str(e))

            if not headers:
                headers = backupheaders(dump_filename,ENCODING)
            values = [list(item) for item in set(tuple(row) for row in values)] #filter out exact duplicate entries, convert to tuple first as lists cant be hashed
            if FORMAT == "csv":
                filename = Path(dump_filename).name.rsplit(".",1)[0].strip()
                basepath = os.path.dirname(dump_filename)#dump_filename.rsplit("\\", 1)[0]
                if not os.path.exists(os.path.join(basepath,"SqlConversions",filename)):
                    os.makedirs(os.path.join(basepath,"SqlConversions",filename))
                bpath = os.path.join(basepath,"SqlConversions",filename)
                if [x for x in headers if any(y in x for y in typelist)]:
                    if not os.path.exists(os.path.join(bpath, "Good Ones")):
                        os.makedirs(os.path.join(bpath, "Good Ones"))
                    bpath = os.path.join(bpath, "Good Ones")
                if len(values)>0:
                    with open(os.path.join(bpath, F"{filename} - {target_table}.csv"),"w",encoding=ENCODING,newline = '') as f:
                        headers.append("table")
                        writer = csv.writer(f)
                        writer.writerow(
                            headers)
                        for x in values:
                            x.append(target_table)
                            writer.writerow([z.strip('"') for z in x])
                    print(F"    Generating CSV for {target_table}")
                else:
                    print(F"    Found no values in {target_table}")


            else:
                for x in values:
                    x = [y.strip("'\t") for y in x]
                    item = dict(zip(headers,x))
                    item['table'] = target_table
                    items.append(item)

                return items
    if dumpall:
        mintables = 10
    else:
        mintables =1
    if not othertables:
        print("Can't find an 'INSERT' statement. Maybe it's not a proper SQL dump. Let me try something")
        try:
            for x in tables:
                allitems = read_dump(filename, x,dumbdump=True)
        except Exception as e:
            with open(filename, 'r', encoding=ENCODING, errors='replace') as f:
                firstlines = [next(f) for x in range(10)]
            print("I give up, here's what the first 10 or so lines look like, you tell me")
            firstlines = [x for x in firstlines if x != '\n']
            for x in firstlines:
                print(x)
        tablechoices = []
        #quit()
    elif len(tables) >mintables:
        tablechoices = tableSelectGUI(tables,filename)
    else:
        tablechoices = tables
    if len(tables)==0:
        print("No proper tables found! So going to try running the NoTableFunction and see what happens")
        everything = NoCreateTable(filename,ENCODING,norepeatinginsert=True)
        if not everything:
            print("  Trying something else...")
            everything = NoCreateTable(filename, ENCODING,norepeatinginsert=False)
            if not everything:
                print("  No luck oh well. Should prob open the file and see what's going on")


    else:
        everything =[]
        if tablechoices:
            count = 0
            for x in tablechoices:
                try:
                    count +=1
                    print(f"{count}/{len(tablechoices)}\n")
                    allitems = read_dump(filename,x)
                    if FORMAT == "json":
                        if len(allitems) ==1:
                            print (allitems)
                            break
                        else:
                            everything.extend(allitems)
                except Exception as e:
                    print(f"Error with {x} because of {str(e)}")
        else:
            print("No tables select. Goodbye.")
    return everything

def predict_encoding(file_path, n_lines=600):
    '''Predict a file's encoding using chardet. This is very slow process esp when possible multiple encodings, so only use this if have encoding errors'''
    import chardet

    # Open the file as binary data
    with open(file_path, 'rb') as f:
        # Join binary lines for specified number of lines
        rawdata = b''.join([f.readline() for _ in range(n_lines)])

    return chardet.detect(rawdata)['encoding']


def backupheaders (dump_filename,ENCODING):
    with open(dump_filename, 'r', encoding=ENCODING, errors='replace') as f:
        content = f.readlines()
    headers = next(x for x in content if x.startswith("INSERT INTO")) #find item with headers
    headers = re.findall('\((.*\))', headers)[0]  # LEFT OFF HERE
    headers = headers.strip(' ()')
    headers = headers.split(",")
    headers = [x.strip(" `") for x in headers]
    return headers

def has_no_proper_create_table_or_repeatinG_insert(dump_filename,ENCODING):#when need to use values from INSERT INTO table, and insert does not repeat - tested on time warner business class.sql
    items = []
    with open(dump_filename, 'r', encoding=ENCODING, errors='replace') as f:
        content = f.readlines()
    headers = next(x for x in content if x.startswith("INSERT INTO")) #find item with headers
    tablename = headers[headers.find("INSERT INTO") + len("INSERT INTO"):].split()[0].strip("`")
    #extra = headers.split("VALUES",1)[1] #if guy who dumped messed up, check to see if values tied to headers cut out
    #extras = re.findall('\([^\)]*\)', extra) #find all values (in between parens)
    #for x in extras: #need to chaneg this so insert the values in lines after "VALUES"
    #    content.append(x)
    headers = re.findall('\((.*\))', headers)[0] #LEFT OFF HERE
    headers = headers.strip(' ()')
    headers = headers.split(",")
    headers = [x.strip(" `") for x in headers]
    for x in content:
        if x.count(",") >3 and x.strip(" \t").startswith("("): #check if line has more than 3 commas and begins with parens
            newline = x.strip('  \t()')
            newline = newline.replace('`', '').replace('\0', '')
            #newline = [newline]
            #newline = [x.replace('\0', '') for x in newline]  # elimate null bytes
            newline = re.split(r",(?=(?:[^\']*\'[^\']*\')*[^\']*$)",
                               newline)
            thing1 = [x.replace("&quot ", "'").strip(" '").replace("\\\\", "") for x in
                      newline]
            item = dict(zip(headers, thing1))
            item['table'] = tablename
            items.append(item)

def NoCreateTable(dump_filename,ENCODING,norepeatinginsert):
    items = []
    allvalues = []
    #headers = []
    header=""
    tablenames =[]
    tables =[]
    tableheader = []
    tablename = ""

    with open(dump_filename, 'r', encoding=ENCODING, errors='replace') as f:
        for line in tqdm(f):
            #try:
            if line.strip():#check if line not empty
                if re.findall(r'\binsert\W+(?:\w+\W+)?into\b', line, re.IGNORECASE):
                    insertstatement = re.findall(r'\binsert\W+(?:\w+\W+)?into\b', line, re.IGNORECASE)[0] #to account for various in insert statements like "insert   into", "INSERT INTO" etc
                    tablename = line[line.find(insertstatement)+len(insertstatement):].split("(")[0].strip(" `\n")
                if tablename:
                    if "VALUES" in line:
                        if line.split(tablename, maxsplit=1)[-1].split(maxsplit=1)[0].startswith("VALUES"): #check if just have insert statements without headers
                            allvalues.append(getvalues(line,tablename,norepeatinginsert=norepeatinginsert)[0])
                        else:
                            # headers= re.findall('(?<=\()(.*?)(?=\))', line)[0] #get first parens here
                            # values =line[line.find("VALUES")+len("VALUES"):].split()[0]
                            value, header = getvalues(line, tablename, getheaders=True,
                                                      norepeatinginsert=norepeatinginsert)
                            allvalues.append(value)
                            if tablename not in tablenames:
                                tablenames.append(tablename)
                                # if f"{tablename}:{header}" not in tableheader:
                                tableheader.append({tablename: header})
                            #tablename["values"].append(getvalues(line,tablename)[0])
                    else:
                        #headers= re.findall('(?<=\()(.*?)(?=\))', line)[0] #get first parens here
                        #values =line[line.find("VALUES")+len("VALUES"):].split()[0]
                        value,header=getvalues(line, tablename,getheaders=True,norepeatinginsert=norepeatinginsert)
                        allvalues.append(value)
                        if tablename not in tablenames:
                            tablenames.append(tablename)
                        #if f"{tablename}:{header}" not in tableheader:
                            tableheader.append({tablename:header})
                else:
                    allvalues.append(getvalues(line, tablename,norepeatinginsert=True)[0])

            #except IndexError:
             #   pass
            #except Exception as e:
               # print (F"{line[:80]} failed because of {str(e)}")
    if allvalues:
        print("   Whoa looks like was able to grab some data!")
        flat_list = [item for sublist in allvalues for item in sublist] #flatten list
        filename = Path(dump_filename).name.rsplit(".", 1)[0]

        #filename = dump_filename.rsplit("\\", 1)[1].rsplit(".", 1)[0]
        basepath = os.path.dirname(dump_filename)  # dump_filename.rsplit("\\", 1)[0]
        if not os.path.exists(os.path.join(basepath, "SqlConversions")):
            os.makedirs(os.path.join(basepath, "SqlConversions"))
        bpath = os.path.join(basepath, "SqlConversions")
        if tableheader:
            for x in tableheader: #create seperate csvs for each table
                print(F"    Generating CSV...")
                with open(os.path.join(bpath, F"{filename} - {next(iter(x))}.csv"), "w", encoding=ENCODING, newline='') as f:
                    writer = csv.writer(f)
    ###issue with headers, sometimes worong, sometimes too short, not sure what going on - similiar TABLENAMES!
                    if x[next(iter(x))]:
                        writer.writerow(
                        x[next(iter(x))])
                    for row in flat_list:
                        if row[-1] ==next(iter(x)): #check if table we want is in value because added tablename to last column of values
                            writer.writerow([z.strip('"') for z in row])
        else:
            print(F"    Generating CSV...")
            with open(os.path.join(bpath, F"{filename} - tableX.csv"), "w", encoding=ENCODING,
                      newline='') as f:
                writer = csv.writer(f)
                ###issue with headers, sometimes worong, sometimes too short, not sure what going on - similiar TABLENAMES!

                for row in flat_list:

                    writer.writerow([z.strip('"') for z in row])
        return "YUP"
    else:
        return items

def getvalues(line,target_table,getheaders=False,norepeatinginsert=False):
    values=[]
    headers=""
    #headers=[]
    if getheaders:
        if target_table in line[:50] and target_table + "_" not in line.split("(",1)[0]:
            headers= re.findall('(?<=\()(.*?)(?=\))', line)[0]
            headers = headers.strip(' ()')
            headers = headers.split(",")
            headers = [x.strip(" `") for x in headers]
            headers.append("table_name")
    data = ""
    if norepeatinginsert:
        if line.count(",") > 3 and line.strip(" \t").startswith("("):
            data = line
    elif line.lower().startswith('insert') and target_table in line[
                                                             :50] and target_table + "_" not in line.split("(",1)[0]:

        try:
            data = line.split(" VALUES", 1)[1]  #
        except:
            data = line.split(" values", 1)[1]  #

        #if '),(' in data:

    if data.strip("\r\n"):
        if regexp.search(data):
            data = ["("+(x)+")" for x in re.split(regexp,data)[1:]]

        #data = ["("+(x)+")" for x in data.split('),(')[1:]]

        else:
            data = [data]
        data = [re.findall('\((.*\))', x) for x in data]

        for y in data:
            y = [x.replace('`', '').strip(" (").strip(") ") for x in y]

            if len(
                    y) > 1:  # for tht etime swhere you have insert values wih all headers before the value sto be inserted, this doesnt matter anymore as getting all data bwn first and last parens
                y = y[1]
            else:
                y = y[0]
            newline = y.replace('`', '').replace("\t", "")#.replace("\\'", "&quot ") #if not next two chars ',
            newline = re.sub("(?<!, (?<=))\\\\'(?!, ')","&quot ",newline)#may need to change back to just 2 backslahes for some #get rid of single quotation makrs unless preceded by , or followed by for some reason replacing every quotation mark when //' not present ,
            newline = newline.strip(" ()\"")
            newline = re.split(r",(?=(?:[^\']*\'[^\']*\')*[^\']*$)",
                               newline)  # another regex variation that may work better that split on comma only if comma not inside single quotes from https://stackoverflow.com/questions/18893390/splitting-on-comma-outside-quotes
            thing1 = [x.replace('\0', '') for x in newline]  # elimate null bytes
            thing1 = [x.replace("&quot ", "'").strip(" '").replace("\\\\", "") for x in
                      thing1]  # add back in quote chars and remove slashes now that line hopefully parse and split properly
            thing1.append(target_table)
            # y = [y]
            # thing = next(csv.reader(y, quotechar="'", skipinitialspace=True))
            values.append(thing1)

    return values,headers


def no_TABLE_NAME_NOHEADERS_JUST_lines():
    field1=""
    field2="etc"

def getridofuselesscolumns(file):
    import pandas as pd
    import numpy as np

    df = pd.read_csv(file,encoding="UTF8")


    columnsdontwant = ["avatartype","birthdayprivacy","threadmode","buddylist","awaydate","returndate","totalpms","usergroupid",
                       "avatardimensions","additionalgroups","daysprune","ignorelist","pmfolders","notepad","referrer",
                       "timeonline", "moderationtime",
                        "postnum","membergroupids","warn_last","joined","usertitle","displaygroupid",'joindate', 'lastvisit',
                       'lastactivity', 'lastpost', 'lastpostid', 'posts',"reputation","options",
                       "birthday_search",'referrerid', 'emailstamp', 'pmtotal', 'pmunread',
                       'profilevisits',"active","plan","timezone","table","passworddate","styleid",
                       'referrerid', 'languageid', 'emailstamp', 'threadedmode', 'emailnotification',"profilevisits","friendcount","token","scheme"]
    firstdrop = [x for x in df.columns if x in columnsdontwant]
    df.drop(firstdrop, axis=1, inplace=True) #drop them
    secdrop = [x for x in df.columns if "dbtech_" in x]
    df.drop(secdrop, axis=1, inplace=True) #drop them

    #df replace None,
    df.replace("blank", np.nan, inplace=True)
    df.replace("Null", np.nan, inplace=True)
    df.replace("NULL", np.nan, inplace=True)
    df.replace("0000-00-00", np.nan, inplace=True)

    df = df.dropna(axis=1, thresh=int(.001 * len(df)))  # drop all columns that have less than .001 values
    droplist2 = []
    for x in df.columns:
        if x not in ["id","userid"]:
            if df[x].dtype in ["int64","float64"]:
                if all(float(y)<9999 for y in df[x].dropna()):
                    droplist2.append(x)

    df.drop(droplist2, axis=1, inplace=True) #drop them
    df.replace(np.nan, '', regex=True, inplace=True) #replace nan with ""
    droplist = [x for x in df.columns if all(
        len(str(y)) < 3 for y in df[x].tolist())]  # find columns if all values only 1 character long e.g. 0,1 y, n
    # droplist2 = [x for x in df.columns if all(len(str(int(y)))<3 for y in df[x].tolist() and all(type(x)==float for x in df[x].tolist()))]#find columns if all values only 1 character long e.g. 0,1 y, n
    df.drop(droplist, axis=1, inplace=True)  # drop them

    df = df.astype("object") #convert to object as pandas converts in to float which is PITA and fucks up next line

    df.dropna(axis=1, how='all', inplace=True) #drop columsn where all rows empty

    #convert all int floats to ints

    df1 = df.applymap(str)
    df1.drop_duplicates(inplace=True)

    df1.to_csv(file.replace(".csv","_cleaned.csv"), index=False, escapechar='\n')  # ignore newline character inside strings

    #df = df.replace({'\n': '<br>', "\r": "<br>"}, regex=True)


def cleandir(dir):
    for x in os.listdir(dir):
        try:
            file = os.path.join(dir, x)
            getridofuselesscolumns(file)
        except Exception as e:
            print(x,str(e))

def sqlconverter(filepath,format,get_encoding=False,dumpall=False):
    import pprint
    from pathlib import Path
    pp = pprint.PrettyPrinter(indent=4)
    if get_encoding:
        ENCODING = predict_encoding(filepath)
        print (F"Identified encoding of file as {ENCODING}")
    else:
        ENCODING = "utf8"
    filename =Path(filepath).name.rsplit(".",1)[0]
    alljson = SQLtoJson(filepath,ENCODING,FORMAT=format,dumpall=dumpall)
    p = Path(filepath)

      # move json file to jsonbackups folder to keep things tidy
    """
    if alljson:
        basepath = filepath.rsplit("\\", 1)[0]
        if not os.path.exists(os.path.join(basepath, "SqlConversions")):
            os.makedirs(os.path.join(basepath, "SqlConversions"))
        bpath = f"{basepath}\\SqlConversions"
        print (F"\nTotal of {str(len(alljson))} items in the JSON object")
        print("First item in Json file")
        pp.pprint(alljson[1])
        print("\nLast item in Json file")
        pp.pprint(alljson[-1])
        try:
            with open(os.path.join(bpath, f"{filename}.json"),"w",encoding=ENCODING) as outfile:
                json.dump(alljson,outfile,ensure_ascii=False) #ensure ascii arg needed to dump russian characters
        except:
            try:
                with open(os.path.join(bpath, f"{filename}.json"), "w", encoding="utf8") as outfile: #on engmagroup sql file, chardet thought was windows-1251 but was actually utf8
                    json.dump(alljson, outfile, ensure_ascii=False)
                print("All done.")
            except Exception as e:
                print (str(e))
                return alljson
    """

def directoryconvert(directory):
    import os


def main():
    import argparse
    import warnings
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", '-json', action='store_true', help="add this flag to convert to JSON, otherwise will convert to CSV by default")
    parser.add_argument('--filepath', '-f', help="where's the SQL")
    parser.add_argument('--directory', '-dir', help="convert folder of sql files")

    parser.add_argument('--clean', '-c', help="clean a CSV")
    parser.add_argument('--cleandir', '-cd', help="clean a directory of CSVs")

    parser.add_argument('--dumpall', '-d', action='store_true',help="grab and convert every table")


    parser.add_argument("--encoding", '-e', action='store_true',help="add flag if want to specify encoding. Best not to at first.")
    if len(sys.argv[1:]) == 0:
        parser.print_help()
        # parser.print_usage() # for just the usage line
        parser.exit()
    args = parser.parse_args()
    #print(args.dumpall)
    #sys.exit()
    if args.json:
        format = "json"
    else:
        format = "csv"
    if args.encoding:
        ENCODING = True
    else:
        ENCODING = False
    if args.clean:
        getridofuselesscolumns(args.clean)
    elif args.cleandir:
        files = os.listdir(args.cleandir)
        for x in files:
            if x.endswith(".csv"):
                filepath = os.path.join(args.cleandir, x)
                try:
                    getridofuselesscolumns(filepath)

                except Exception as e:
                    print(f"{filepath}:Fuked up::{str(e)}")
    elif args.filepath:
        sqlconverter(args.filepath,format,get_encoding=ENCODING,dumpall = args.dumpall)
    elif args.directory:
        files = os.listdir(args.directory)
        for x in files:
            if x.endswith(".sql"):
                filepath = os.path.join(args.directory, x)
                try:
                    sqlconverter(filepath, format, get_encoding=ENCODING, dumpall=args.dumpall)
                except Exception as e:
                    print (f"{filepath}:Fuked up::{str(e)}")

if __name__ == '__main__':
    main()
#sqlconverter(r"D:\Breached Databases\newestones\verifiedish\api_gryamatics_com.sql","csv",get_encoding=False) #And pick "users" table is GOOD TEST