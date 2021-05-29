#!/usr/bin/env python3

import re
import csv
from easygui import *
import sys
from tqdm import tqdm
import os
from colorama import Fore
from pathlib import Path
import pandas as pd

pd.set_option('display.max_columns', None)

maxInt = sys.maxsize

#for the "clean" function, add column headers you don't want
columnsdontwant = ['awards', 'warningpoints']

while True:
    # decrease the maxInt value by factor 10
    # as long as the OverflowError occurs.
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt/10)


def extractemailsfromfile(filename,lineextractor=False):
    from pathlib import Path
    fpath = Path(filename).parent
    fname = Path(filename).name.rsplit(".",1)[0]
    fname = f"{fname}_emails.txt"
    regex = re.compile("[\w\.-]+@[\w\.-]+\.\w+")

    emails = []

    with open(filename,encoding="utf8",errors="replace") as f:
        for s in tqdm(f, desc=f"Parsing {fname}"):
            if lineextractor:
                if regex.search(s.lower()):
                    emails.append(s)
            else:
                em = [email for email in re.findall(regex, s.lower()) if not email[0].startswith('//')]
                for x in em:
                    if x not in emails:
                        emails.append(x)

    with open(os.path.join(fpath,fname), "a",encoding="UTF8") as emailsfile:
        for x in emails:
            emailsfile.write(x + "\n")



def tableSelectGUI(tablenames,filename):
    tablecount = str(len(tablenames))
    msg = f"Found {tablecount} tables in {Path(filename).name}. Select Ones You want to Extract (best looking ones at top)"
    title = "Table Selection"
    iwant = ["account", "member", "user","admins","clients","customers","skype","customer_entity"]
    tablenames.sort()
    upfirst = [x for x in tablenames if any(y in x.lower() for y in iwant)] #put tables with info i like up first
    tot = upfirst + tablenames
    choices = sorted(set(tot), key=tot.index) #get rid of duplicates while preserving order
    choice = multchoicebox(msg, title, choices,preselect=None)
    return choice

typelist  = ["email","username","alias","ipaddress","ip_address","address","ip"]
regexp = re.compile(r"\),\((?=(?:[^']*'[^']*')*[^']*$)") #use this to get instance of "),(", change capturing groupthat aren't within a record so can determine if looking at list of records on one line, or one record per line. See here for getting rid of captured groups so only match on full match https://stackoverflow.com/questions/31915018/re-findall-behaves-weird/31915134#31915134
valregex = re.compile(r" values ?\(",re.IGNORECASE) #re.compile(r"\) values ",re.IGNORECASE) q mark matches space 0 or 100 times
valregex2 = re.compile(r" values[\s\(]",re.IGNORECASE)


def SQLtoJson(filename,ENCODING,FORMAT="json",dumpall=False):
    def find_tables(dump_filename):  # this works
        print(f"Getting tables from {Path(dump_filename).name}")
        table_list = []
        othertables = ""
        noncreatetableTables = []

        with open(dump_filename, 'r', encoding=ENCODING,errors='replace') as f:
            count = 0
            for line in tqdm(f,desc=f"Parsing..."):

                line = line.strip()
                try:
                    if line.startswith('INSERT ') or line.startswith('insert  into'): #took out the lowr as found one sql file where some lines began with insert as name or paswword and added special circumstance for badly dumped dql
                        othertables = "Yup"
                        insertstatement = re.findall(r'\binsert\W+(?:\w+\W+)?into\b', line, re.IGNORECASE)[
                            0]  # to account for various in insert statements like "insert   into", "INSERT INTO" etc
                        tablename = line[line.find(insertstatement) + len(insertstatement):].strip().split(" ")[0].strip(
                            " `\n").strip('"')
                        noncreatetableTables.append(tablename)
                except:
                    pass
                if line.lower().startswith('create table'):
                    line = line.replace("IF NOT EXISTS ","").replace("&quot;","`") #get rid of those term so below regex works

                    table_name = re.findall("create table [`']([\w_]+)[`']", line,flags = re.IGNORECASE)
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

        return (table_list,othertables,noncreatetableTables)

    tables,othertables,noncreatetableTables = find_tables(filename)

    def read_dump(dump_filename, target_table,dumbdump=False):
        tableregexp = re.compile(f"[`'\s]({target_table})[`'\s(]")
        errors = []
        #print (F"Grabbing values for table: {target_table}")
        with open(dump_filename,'r',encoding=ENCODING,errors='replace') as f: #sometimes there are stupid encoding issues where certain char cant be read by encoder, so fuck em
            read_mode = 0  # 0 - skip, 1 - header, 2 - data, 3 - data

            headers = []
            items = []
            values = []
            wronglength =[]

            for line in tqdm(f,desc=f"Parsing {Fore.LIGHTBLUE_EX}{target_table}{Fore.RESET} table"):
                try:
                    line = line.strip()

                    if dumbdump:
                        if line.strip().startswith("(") or line.strip().startswith("VALUES"):
                            if regexp.search(line):
                                read_mode = 2  # print(line) #dont think need these read modes anymore but kept as legacy just in case
                                # continue

                            else:
                                read_mode = 3
                    else:
                        if line.lower().startswith('insert') and tableregexp.search(line.split("(",1)[0]):#target_table in line.split("(", 1)[0][:50] and target_table + "_" not in line.split("(",1)[0] and "_"+target_table not in line.split("(",1)[0]:
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

                    if line.lower().startswith('create table') and tableregexp.search(line.split("(",1)[0]):#target_table in line and target_table + "_" not in line.split("(",1)[0] and "_"+target_table not in line.split("(",1)[0]: # the "_" gets rid of false positives like target_table_1 etc but not target_table1
                        splitline = line.split(target_table)[1]
                        splitfirst = line.split(target_table)[0]
                        if not splitline or not splitline[0].isdigit() and not splitline[0].isalpha() and (not splitfirst[-1].isdigit() and not splitfirst[-1].isalpha()):
                            read_mode =1

                            continue
                    if read_mode==0:
                        continue
                    elif read_mode==1:
                        if line.lower().startswith('primary') or line.lower().startswith("unique key"):

                            read_mode=0
                            continue
                        elif line.lower().startswith(")"): #added this to deal with desking, w/o worked fien for other ones
                            read_mode=0
                            continue
                        #colheader = re.findall('`([\w_]+)`',line) #old version, only grabs header if in quotes
                        colheader = re.findall('^([^ \t]+).*',line)
                        for col in colheader:
                            headers.append(col.strip("'").strip("`"))

                    elif read_mode ==2:
                        if line.lower().startswith('insert') and tableregexp.search(line.split("(",1)[0]):#target_table in line.split("(", 1)[0][:50] and target_table + "_" not in line.split("(",1)[0]:
                            data =re.split(valregex,line,1)[1] #max split of 1

                            thing1 = cleanline(data,overridequotechar="'")
                            for y in thing1:
                                if len(y) == len(headers):
                                    values.append(y)
                                else:
                                    wronglength.append(line)

                    elif read_mode ==3:
                        if line.lower().startswith('insert') and tableregexp.search(line.split("(",1)[0]) and line.endswith("VALUES"):
                            pass
                        else:

                            line = line.strip("\t,\r\n")
                            if valregex2.search(line):
                                line = "(" + re.split(valregex, line, 1)[1] #add intro parens back

                            if line.strip()[0]=="(" or "VALUES (" in line or "VALUES(" in line:
                                data = re.findall('\((.*)\)', line)  # get everythign between first and last occurance of parens
                            else:
                                data = [line] #for times when no parens oustide valies (rare)

                            try:

                                if len(
                                        data) > 1:  # for tht etime swhere you have insert values wih all headers before the value sto be inserted, this doesnt matter anymore as getting all data bwn first and last parens
                                    newline = data[1]
                                else:
                                    newline = data[0]

                                thing1 = cleanline(newline,readmode=3,overridequotechar="'")
                                for x in thing1:
                                    if len(x) == len(headers):

                                        values.append(x)
                                    else:
                                        wronglength.append(line)
                                # need to

                                #These lines may not be needed anymore. messed up some other files. we'll see...nope still need it
                                if line.endswith(";") and not line.startswith(
                                        "INSERT INTO"):  # added this if/else clause to deal with desking issue where script was getting values of all table sfor some reason, when added it above  I lose last entry in table, so now add it here so add data to list but after switch read-mode. Added extra line startswith cond as realized that when have insert into statements all the way down, those end with semi-colon
                                    read_mode = 0
                                    continue



                            except IndexError:
                                pass
                            except Exception as e:
                                errors.append(line)

                except Exception as e:
                    errors.append(line)

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
                    print(F"    Generating CSV for {target_table}")
                    with open(os.path.join(bpath, F"{filename} - {target_table}.csv"), "w", encoding=ENCODING,
                              newline='', errors="replace") as f:

                        headers.append("table")
                        writer = csv.writer(f)
                        writer.writerow(
                            headers)
                        for x in values:
                            x.append(target_table)
                            writer.writerow([z.strip('\t "\'') for z in x])
                else:
                    print(F"    Found no values in {target_table}")
                if wronglength:
                    with open(
                        os.path.join(bpath, F"{filename} - {target_table}_wrong_length.csv"), "w",
                        encoding=ENCODING, newline='', errors="replace") as f2:
                            for y in wronglength:
                                f2.write(y+"\n")

                #else:
                 #   print(F"    Found no values in {target_table}")



        if errors:
            with open(os.path.join(bpath, f"{filename}_ErroredLines.txt"), 'a') as outfile:
                for x in errors:
                    outfile.write(x + "\n")

    if dumpall:
        mintables = 100000
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
        missing = [x for x in noncreatetableTables if x not in tables]
        if missing:
            textbox("\n".join(missing),
                    "WARNING: These tables that have insert statement but not create table statement","Right now you'll need to manually extract the table if you want them")
        tablechoices = tableSelectGUI(tables,filename)
    else:
        tablechoices = tables
    if len(tables)==0:
        print("No create table statements found! Going to try running the 'NoCreateTable' function and see what happens")
        everything = NoCreateTable(filename,ENCODING,norepeatinginsert=True)
        if not everything:
            print("  Damn it, no luck. Trying something else...")
            everything = NoCreateTable(filename, ENCODING,norepeatinginsert=False)
            if not everything:
                print("  Still nothing. Should probably open the file and see what's going on")
    else:
        everything =[]
        if tablechoices:
            count = 0
            for x in tablechoices:
                try:
                    count +=1
                    print(f"{count}/{len(tablechoices)}\n")
                    read_dump(filename,x)

                except Exception as e:
                    print(f"Error with {x} because of {str(e)}")
        else:
            print("No tables select. Goodbye.")
    return everything

def predict_encoding(file_path, n_lines=600):
    '''Predict a file's encoding using chardet. This is very slow process esp when possible multiple encodings, so only use this if have encoding errors'''
    import chardet

    # Open the file as binary datac
    with open(file_path, 'rb') as f:
        # Join binary lines for specified number of lines
        rawdata = b''.join([f.readline() for _ in range(n_lines)])

    return chardet.detect(rawdata)['encoding']

def backupheaders (dump_filename,ENCODING):
    with open(dump_filename, 'r', encoding=ENCODING, errors='replace') as f:
        content = f.readlines()
    headers = next(x for x in content if x.startswith("INSERT INTO")) #find item with headers
    headers = re.findall('\((.*\))', headers)[0]
    headers = headers.strip(' ()')
    headers = headers.split(",")
    headers = [x.strip(" `") for x in headers]
    return headers

def tsvtocsv(tsvfile):
    import os
    from pathlib import Path
    import csv
    bpath = Path(tsvfile).parent
    filename = Path(tsvfile).name.rsplit(".",1)[0]
    csvfilename = filename + "_con.csv"
    with open(tsvfile, 'r', encoding="utf8",errors="replace") as fin, \
            open(os.path.join(bpath,csvfilename), 'w', encoding="utf8",
                 newline='') as fout:
        reader = csv.reader(fin, dialect='excel-tab', quoting=csv.QUOTE_MINIMAL) #quote line added because got erro Error: field larger than field limit. some other options for this error: https://stackoverflow.com/questions/15063936/csv-error-field-larger-than-field-limit-131072
        writer = csv.writer(fout)
        for row in reader:
            writer.writerow(row)


def isListEmpty(inList):
    if isinstance(inList, list): # Is a list
        return all( map(isListEmpty, inList) )
    return False # Not a list


def NoCreateTable(dump_filename,ENCODING,norepeatinginsert):
    items = []
    allvalues = []

    header=""
    tablenames =[]
    tableheader = []
    tablename = ""
    basepath = os.path.dirname(dump_filename)  # dump_filename.rsplit("\\", 1)[0]
    if not os.path.exists(os.path.join(basepath, "SqlConversions")):
        os.makedirs(os.path.join(basepath, "SqlConversions"))
    bpath = os.path.join(basepath, "SqlConversions")
    filename = Path(dump_filename).name.rsplit(".", 1)[0]

    with open(dump_filename, 'r', encoding=ENCODING, errors='replace') as f:
        for line in tqdm(f):
            #try:
            if line.strip():#check if line not empty
                if re.findall(r'\binsert\W+(?:\w+\W+)?into\b', line, re.IGNORECASE):
                    insertstatement = re.findall(r'\binsert\W+(?:\w+\W+)?into\b', line, re.IGNORECASE)[0] #to account for various in insert statements like "insert   into", "INSERT INTO" etc
                    tablename = line[line.find(insertstatement)+len(insertstatement):].split("(")[0].strip(" `\n").strip('"')
                if tablename:
                    if "VALUES" in line:
                        if line.split(tablename, maxsplit=1)[-1].split(maxsplit=1)[0].startswith("VALUES"): #check if just have insert statements without headers
                            vals = getvalues(line,tablename,norepeatinginsert=norepeatinginsert)[0]
                            for x in vals:
                                allvalues.append(x)
                        else:

                            try:
                                value, header = getvalues(line, tablename, getheaders=True,
                                                      norepeatinginsert=norepeatinginsert)
                                for x in value:
                                    allvalues.append(x)
                            except Exception as e:
                                print(str(e),line)
                                sys.exit()
                            if tablename not in tablenames:
                                tablenames.append(tablename)
                                # if f"{tablename}:{header}" not in tableheader:
                                tableheader.append({tablename: header})
                    else:

                        try:
                            value,header=getvalues(line, tablename,getheaders=True,norepeatinginsert=norepeatinginsert)
                            for x in value:#added these 2 lines with new clean line func
                                x = x.append(tablename)
                                allvalues.append(x)
                        except:
                            print(line)
                            with open(os.path.join(bpath, f"{filename}_Errors.txt"), 'a') as outfile:
                                outfile.write(line+"\n")
                        if tablename not in tablenames:
                            tablenames.append(tablename)
                            tableheader.append({tablename:header})
                else:
                    vals = getvalues(line, tablename,norepeatinginsert=True)[0]
                    for x in vals:
                        allvalues.append(x)


            tablename = "" #reset table name
    if not isListEmpty(allvalues):
        print("   Whoa looks like was able to grab some data!")
        flat_list = [item for sublist in allvalues for item in sublist] #flatten list

        if tableheader:
            for x in tableheader: #create seperate csvs for each table
                print(F"    Generating CSV...")
                with open(os.path.join(bpath, F"{filename} - {next(iter(x))}.csv"), "w", encoding=ENCODING, newline='') as f:
                    writer = csv.writer(f)
                    if x[next(iter(x))]:
                        writer.writerow(
                        x[next(iter(x))])
                    for row in flat_list:
                        if len(tableheader) >1:
                            if row[-1] ==next(iter(x)): #check if table we want is in value because added tablename to last column of values
                                writer.writerow([z.strip('"') for z in row])
                        else:
                            writer.writerow([z.strip('"') for z in row]) #if there's only one table in here, no need to check for table name
        else:
            print(F"    Generating CSV...")
            with open(os.path.join(bpath, F"{filename} - tableX.csv"), "w", encoding=ENCODING,
                      newline='') as f:
                writer = csv.writer(f)

                for row in flat_list:

                    writer.writerow([z.strip('"').strip("\t") for z in row])
        return "YUP"
    else:
        return False

def getvalues(line,target_table,getheaders=False,norepeatinginsert=False):
    values=[]
    headers=""
    tableregexp = re.compile(f"[`'\s]({target_table})[`'\s(]")

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

    elif line.lower().startswith('insert') and tableregexp.search(line.split("(",1)[0]):

        try:
            data = line.split(" VALUES", 1)[1]  #
        except:
            try:
                data = line.split(" values", 1)[1]  #
            except:
                data = line.split("VALUES ",1)[1]
    elif line[0].strip() =="(":
        #data = re.findall('\((.*\))', line)
        data = line
        #if '),(' in data:
    elif line.count(",") > 3 and line.strip(" \t").startswith("VALUES"):
        #print("yes")
        data = "("+line.split("VALUES(",1)[1]
    if data.strip("\r\n"):
        if regexp.search(data):
            data = ["("+(x)+")" for x in re.split(regexp,data)[1:]]

        else:
            data = [data]
        data = [re.findall('\((.*\))', x) for x in data]

        for y in data:
            y = [x.replace('`', '').strip(" (").strip(") ") for x in y]

            if len(y) > 1:  # for tht etime swhere you have insert values wih all headers before the value sto be inserted, this doesnt matter anymore as getting all data bwn first and last parens
                y = y[1]
            else:
                y = y[0]
            thing1 = cleanline(y,readmode=3)

            values.append(thing1)

    return values,headers

def cleanline(values, readmode=2, overridequotechar=""):
    values = values.replace(", ", ",").replace("\t", "")

    QUOTECHAR = "'"

    if overridequotechar:
        QUOTECHAR = overridequotechar
    rows = []
    latest_row = []

    reader = csv.reader([values], delimiter=',',
                        doublequote=True,# when they are double quotes eg '' in middle of value. may need to switch to False for other tables
                        escapechar='\\',
                        quotechar=QUOTECHAR,
                        strict=False
                        )
    if readmode == 3:  # get raw output of the reader, as otherwise if there is ")" at end os value
        rows = list(reader)
    else:
        for reader_row in reader:
            for column in reader_row:
                if len(column) == 0 or column == 'NULL':
                    latest_row.append(chr(0))
                    continue
                if column[0] == "(":
                    new_row = False
                    if len(latest_row) > 0:
                        if latest_row[-1][-1] == ")":
                            latest_row[-1] = latest_row[-1][:-1]
                            new_row = True
                    if new_row:
                        latest_row = ['' if field == '\x00' else field for field in latest_row]

                        rows.append(latest_row)
                        latest_row = []
                    if len(latest_row) == 0:
                        column = column[1:]
                latest_row.append(column)
            if latest_row[-1][-2:] == ");":
                latest_row[-1] = latest_row[-1][:-2]
                latest_row = ['' if field == '\x00' else field for field in latest_row]

                rows.append(latest_row)

    return rows

def fivedigittodate(fivedigits):
    from datetime import datetime
    try:
        fivedigits = int(fivedigits)
        dt = datetime.fromordinal(datetime(1900, 1, 1).toordinal() + fivedigits - 2)
        newdate = dt.strftime("%m/%d/%Y")
    except:
        newdate = fivedigits
    return newdate


def getridofuselesscolumns(file):
    import pandas as pd
    import numpy as np
    import warnings
    warnings.filterwarnings("ignore")
    pd.set_option('display.max_colwidth', -1)
    if file.endswith(".csv"):
        try:
            df = pd.read_csv(file,encoding="UTF8",dtype=object,index_col=False) #readdirtyfile had issues with tabs etc
        except UnicodeDecodeError:
            print("Decoding error. Trying to figure out encoding ")

            encoding = predict_encoding(file)
            print(f"Ok was encoded in {encoding}. Now tryign to clean file")
            df = pd.read_csv(file,encoding=encoding,dtype=object,index_col=False)
    else:
        df = pd.read_table(file,encoding="utf8",dtype=object)
    firstdrop = [x for x in df.columns if x in columnsdontwant]
    df.drop(firstdrop, axis=1, inplace=True) #drop them
    secdrop = [x for x in df.columns if "dbtech_" in x]
    df.drop(secdrop, axis=1, inplace=True) #drop them
    df = df.applymap(lambda x: x.strip().strip("'") if isinstance(x, str) else x)

    df.replace("blank", np.nan, inplace=True)
    df.replace("<blank>", np.nan, inplace=True)
    df.replace("0", np.nan, inplace=True)
    df.replace("N/A", np.nan, inplace=True)
    df.replace("Null", np.nan, inplace=True)
    df.replace("None", np.nan, inplace=True)
    df.replace("\\N", np.nan, inplace=True)
    df.replace("NULL", np.nan, inplace=True)
    df.replace("0000-00-00", np.nan, inplace=True)
    df.replace("0000-00-00 00:00:00", np.nan, inplace=True)

    df.replace(np.nan, '', regex=True, inplace=True) #replace nan with ""
    bdaycols = ["bday_day", "bday_month", "bday_year"]
    bdaycols2=["bday_d", "bday_m", "bday_y"]
    if all(elem in df.columns.values.tolist() for elem in bdaycols):  # check to see if they all in there
        df["birthdate"] = df[bdaycols].apply(
            lambda row: '-'.join(row.values.astype(str)).replace("--", "").replace(".0",""), axis=1)
        df.drop(bdaycols,axis=1,inplace=True)

    if all(elem in df.columns.values.tolist() for elem in bdaycols2):  # check to see if they all in there
        df["birthdate"] = df[bdaycols2].apply(
            lambda row: '-'.join(row.values.astype(str)).replace("--", "").replace(".0",""), axis=1)
        df.drop(bdaycols2,axis=1,inplace=True)
    droplist = []
    for x in df.columns:
        try:
            if all(len(str(y)) < 2 for y in df[x].tolist()):
                droplist.append(x)
        except:
            pass

    df.drop(droplist, axis=1, inplace=True)  # drop them

    df.dropna(axis=1, how='all', inplace=True) #drop columsn where all rows empty

    #convert all int floats to ints

    df1 = df.applymap(str)
    df1.replace("0.0", np.nan, inplace=True)
    df1.drop_duplicates(inplace=True)
    df1 = df1.applymap(str)

    bpath = Path(file).parent
    newfilename = Path(file).name.rsplit(".",1)[0] + "_cleaned.csv"
    df1.to_csv(os.path.join(bpath,newfilename), index=False, escapechar='\n')  # ignore newline character inside strings

    if not os.path.exists(os.path.join(bpath,"originals")):
        os.makedirs(os.path.join(bpath,"originals"))
    os.rename(file, os.path.join(bpath,"originals",Path(file).name))


def orderedunique(items):
    items = list(filter(None,items))
    found = set([])
    keep = []

    for item in items:
        if item.lower() not in found:
            found.add(item.lower())
            keep.append(item.lower())

    return keep

def htmltabletocsv(filelocation):
    for i, df in enumerate(pd.read_html(filelocation)):
        bath = Path(filelocation).parent
        fname = Path(filelocation).name.rsplit(".",1)[0]
        df.to_csv(os.path.join(bath,f'{fname}_{i}.csv'),index=False)


def intoTOIPaddress(IPint):
    import ipaddress
    if type(IPint)==str and IPint.endswith(".0"):
        IPint = IPint.replace(".0","")
    if type(IPint)==float:
        IPint = str(IPint).replace(".0","")
    if type(IPint)==str and "x" in IPint:
        IPint = int(IPint, 16)
    elif IPint.isdigit():
        IPint = int(IPint)
    try:
        if IPint<0:
            IPint = IPint + 4294967296
        try:
            ip = ipaddress.ip_address(IPint).exploded
        except:
            ip = IPint
    except:
        ip = IPint
    return ip



def cleandir(dir):
    for x in os.listdir(dir):
        try:
            file = os.path.join(dir, x)
            getridofuselesscolumns(file)
        except Exception as e:
            print(x,str(e))


def convertXL2csv(directory): #gets Excel file and converts each sheet to CSV and moves XL file to folder
    from tqdm import tqdm
    import os
    errors =[]
    for root, dirs, files in os.walk(directory):
        for file in tqdm(files):
            if file.endswith("xls") or file.endswith("xlsx"):
                filepath = os.path.join(root, file)
                try:
                    convertExceltoCSV(filepath)
                except:
                    errors.append(filepath)

    return errors

def sqlconverter(filepath,format,get_encoding=False,dumpall=False):
    from pathlib import Path
    if get_encoding:
        ENCODING = predict_encoding(filepath)
        print (F"Identified encoding of file as {ENCODING}")
    else:
        ENCODING = "utf8"
    SQLtoJson(filepath,ENCODING,FORMAT=format,dumpall=dumpall)

def convertExceltoCSV(filepath):
    filename = Path(filepath).name.rsplit(".")[0]
    directory = Path(filepath).parent

    xfile = pd.ExcelFile(filepath)
    topfolder=""
    sheets = xfile.sheet_names
    for sheet in sheets:
        df = xfile.parse(sheet)
        if sheet.startswith("Sheet"):
            sheet = sheet.replace("Sheet", "")
        if len(df) > 0:
            df.to_csv(os.path.join(directory, f"{filename}_{sheet}.csv"), encoding='utf-8', index=False)


def prettytabletoCSV(filepath):
    import csv
    with open(filepath,encoding="utf8",errors="replace") as f:
        s = f.read()
    result = [tuple(filter(None, map(str.strip, splitline))) for line in s.splitlines() for splitline in
              [line.split("|")] if len(splitline) > 1]
    filename, file_extension = os.path.splitext(filepath)
    with open(filepath.replace(file_extension,'.csv'), 'w',newline="",encoding="utf8") as outcsv:
        writer = csv.writer(outcsv)
        writer.writerows(result)

class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

def main():
    import argparse
    import warnings
    from colorama import Style

    warnings.filterwarnings("ignore")
    import sys
    description = f"""{Fore.CYAN}

                       _____  ____  _      _____                               
                      / ____|/ __ \| |    |  __ \                          _   
                     | (___ | |  | | |    | |__) |_ _ _ __ ___  ___ _ __ _| |_ 
                      \___ \| |  | | |    |  ___/ _` | '__/ __|/ _ \ '__|_   _|
                      ____) | |__| | |____| |  | (_| | |  \__ \  __/ |    |_|  
                     |_____/ \___\_\______|_|   \__,_|_|  |___/\___|_|         
                                                           

                           {Fore.RESET}by:{Fore.CYAN} Matteo Tomasini (citcheese) {Fore.RESET}
                                    Version: {Fore.CYAN}0.8{Fore.RESET}                                      

            {color.BOLD}        SQLParser+ - Convert SQL dumps and other leak dumps to CSVs!{Style.RESET_ALL}

    {Fore.CYAN}_____________________________________________________________________________{Fore.RESET}
    """
    print(description + "\n")

    parser = argparse.ArgumentParser()
    group3 = parser.add_argument_group(f'{Fore.CYAN}What Do you Want to convert?{Fore.RESET}')

    group3.add_argument('--sqlextract', '-s', help="convert SQL file or folder of files to CSV",metavar="")
    group3.add_argument('--emailsonly', '-em', help="only extract emails from file",metavar="")
    group3.add_argument('--html', '-html', help="convert file with HTML tables to CSVs",metavar="")
    group3.add_argument('--xltocsv', '-xl', help="converts each sheet of Excel file to CSV file - throw in file or folder",metavar="")
    group3.add_argument('--pretty', '-pt', help="converts 'pretty table' dump to CSV",metavar="")


    group2 = parser.add_argument_group(f'{Fore.CYAN}SQL Dump Options{Fore.RESET}')

    group2.add_argument('--dumpall', '-d', action='store_true', help="grab and convert every table")
    group2.add_argument("--encoding", '-e', action='store_true',help="add if want to specify encoding or if getting UTF errors. Best not to at first.")

    group1 = parser.add_argument_group(f'{Fore.CYAN}Post Processing Options{Fore.RESET}')

    group1.add_argument('--clean', '-c', help="clean a CSV",metavar="")
    group1.add_argument('--cleandir', '-cd', help="clean a directory of CSVs",metavar="")

   
    parser.add_argument("--recursive","-r",action='store_true',help="Use to convert/clean files within subfolders")


    if len(sys.argv[1:]) == 0:
        parser.print_help()
        parser.exit()

    args = parser.parse_args()
    format = "csv"
    if args.encoding:
        ENCODING = True
    else:
        ENCODING = False

    if args.emailsonly:
        extractemailsfromfile(args.emailsonly)
    if args.clean:
        getridofuselesscolumns(args.clean)
    elif args.pretty:
        prettytabletoCSV(args.pretty)
    elif args.xltocsv:
        item = args.xltocsv
        if args.recursive:
            if os.path.isdir(item):
                convertXL2csv(item)
            else:
                print("This doesn't appear to be a directory")
        else:
            if os.path.isfile(item):
                print(f"{Fore.RED}Now converting:{Fore.RESET} {item}")
                convertExceltoCSV(item)
            elif os.path.isdir(item):
                files = os.listdir(item)
                for x in tqdm(files):
                    if x.endswith("xls") or x.endswith("xlsx"):
                        convertExceltoCSV(os.path.join(item,x))
    elif args.cleandir:
        if args.recursive:
            for root, dirs, files in os.walk(args.cleandir):
                for file in tqdm(files):
                    if file.endswith(".csv"):
                        filepath = os.path.join(root, file)
                        try:
                            getridofuselesscolumns(filepath)

                        except Exception as e:
                            print(f"{filepath}:Messed up::{str(e)}")
        else:
            files = os.listdir(args.cleandir)

            for x in tqdm(files):
                if x.endswith(".csv"):
                    filepath = os.path.join(args.cleandir, x)
                    try:
                        getridofuselesscolumns(filepath)

                    except Exception as e:
                        print(f"{filepath}:Messed up::{str(e)}")
    elif args.sqlextract:
        item = args.sqlextract
        if os.path.isfile(item):
            sqlconverter(item,format,get_encoding=ENCODING,dumpall = args.dumpall)
        elif os.path.isdir(item):

            if args.recursive:
                for root, dirs, files in os.walk(item):
                    for file in files:
                        if file.endswith(".txt") or file.endswith(".sql"):
                            filepath = os.path.join(root, file)
                            try:
                                sqlconverter(filepath, format, get_encoding=ENCODING, dumpall=args.dumpall)
                            except Exception as e:
                                print(f"{filepath}:Messed up::{str(e)}")

            else:
                files = os.listdir(item)
                for x in files:
                    if x.endswith(".sql") or x.endswith(".txt") and os.path.isfile(os.path.join(item, x)):
                        filepath = os.path.join(item, x)
                        try:
                            sqlconverter(filepath, format, get_encoding=ENCODING, dumpall=args.dumpall)
                        except Exception as e:
                            print (f"{filepath}:Messed up::{str(e)}")
    elif args.html:
        htmltabletocsv(args.html)



if __name__ == '__main__':
    main()

