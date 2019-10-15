#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess, gspread, sys, json, pdfrw, argparse
from os import path, system, mkdir, listdir
from natsort import natsorted
from operator import itemgetter, attrgetter
from oauth2client.service_account import ServiceAccountCredentials
from time import strftime
from utils import *

def setupArgumentParser():
    parser = argparse.ArgumentParser(
        description='provide name of google worksheet (not filename!)', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-b',
        '--base',
        help='base directory (e.g. ~/Carnet-Assistant)',
        type=str,
        required=True)
    parser.add_argument(
        '-s',
        '--sheet',
        help='Name of worksheet',
        type=str,
        required=True)
    parser.add_argument(
        '-t',
        '--test',
        help='Use file names to label images, not json dict',
        type=bool,
        required=False,
        default = 0)
    parser.add_argument(
        '-f',
        '--font',
        help='Path of some system font eg Ubuntu-B.ttf',
        type=str,
        default='/usr/share/fonts/truetype/ubuntu-font-family/Gravity-Bold.otf')
    parser.add_argument(
        '-k',
        '--credentialsAccount',
        help='Spreadsheet service account key credentials file',
        type=str,
        default='service-account-key.json')
    parser.add_argument(
        '--credentialsSheet',
        help='Spreadsheet key file',
        type=str,
        default='spreadsheet.key')   
    return parser


###############################
############ MAIN #############
###############################

if __name__ == "__main__":
    options =                   setupArgumentParser().parse_args()
    basedir =                   options.base
    path_images =               path.join(basedir,"images",options.sheet)
    path_fdf_dir =              path.join(basedir,"dicts")
    path_pdf_templates =        path.join(basedir,"templatescopy")
    carnet_output_dir =         path.join(basedir,"output")
    page_output_dir =           path.join(basedir,"output/.pages")
    
    archive =                   strftime("%Y%m%d%H%M%S")+"-"+options.sheet
    carnet_archive_dir =        path.join(basedir,"output/archive",archive)
    
    extra_templates =          ["extra-front.pdf","extra-back.pdf"]
    front_page_templates =      ["antrag-blank.pdf", "carnet-blank.pdf"]
    outputs =                   ["antrag.pdf", "carnet.pdf", "images.pdf"]

    ##############################################
    # use creds to create client for G-Drive API #
    ##############################################
    creds_account =         path.join(basedir,"creds/",options.credentialsAccount)
    creds_sheet =           path.join(basedir,"creds/",options.credentialsSheet)
    scope =                ['https://www.googleapis.com/auth/drive', 'https://spreadsheets.google.com/feeds']
    creds =                ServiceAccountCredentials.from_json_keyfile_name(creds_account, scope)
    client =               gspread.authorize(creds)

    #####################################
    # Find workbook  and open worksheet #
    #####################################
    with open(creds_sheet, 'r') as file:
        spreadsheet_key = file.read().replace('\n', '')
    sheet = client.open_by_key(spreadsheet_key).worksheet(options.sheet)

    ############################################################################# 
    # Parse entries as list of dictionaries. There will be ten entries per page #
    #############################################################################
    data = sheet.get_all_records()

    if checkCountries(data):
        print('Exiting.')
        quit()

    if checkImages(data,path_images):
        print('Exiting.')
        quit()

    nentries = len(data)
    npages = nentries//10 
    nlastpage = nentries%10 #number of list entries on the last page. used to fill the final dictionary with some empty values to avoid null pointer
    print("pages: {0}, items on last page: {1}".format(npages,nlastpage))
    
    #########################################
    # Write dictionary for numbering images #
    #########################################
    dict_images = {"archive":archive}
    for item in range(nentries):
        key_image = data[item]['image']
        value_item = data[item]['item']
        dict_images[key_image] = value_item

    with open("{}/image_dict.json".format(path_fdf_dir),"w") as file:
        file.write(json.dumps(dict_images))

    ##################################
    # Empty old pages from directory #
    ##################################
    for current_files in listdir(page_output_dir):
        file_path = path.join(page_output_dir,current_files)
        try:
            if path.isfile(file_path):
                if current_files != '.gitignore':
                    unlink(file_path)
        except Exception as e:
            print(e)
            
    ###########################################
    # Create FDF files from the list of dicts #
    # Define header and footer and keys       #
    ###########################################
    fdf_header = "%FDF-1.2\n1 0 obj<</FDF<< /Fields[\n\n"
    extra_footer = "<< /T({W.C})/V({}) >>\n<< /T({W.E})/V({}) >>\n"
    fdf_footer = "\n] >> >>\nendobj\ntrailer\n<</Root 1 0 R>>\n%%EOF"
    data_keys = {"item":"A","description":"B","quantity":"C","mass":"D","value":"E","country":"F","image":"Z"}
    unit = {"C":"","D":" kg","E":" EUR"}
    page_sums = [{"C":0,"D":0,"E":0}]
    for counter in range(0,npages+1):
        page_sums.append({"C":0,"D":0,"E":0})

    ###################
    # Start page loop #
    ################### 
    for page_number in range (npages+1):
        first_item = page_number*10
        last_item = (page_number+1)*10  

        ########################################
        # Open a new fdf file and write header #
        ########################################
        with open("{0}/page-{1}.fdf".format(path_fdf_dir,page_number),"w+") as file:
            file.write(fdf_header)
            # Write the initial P sums
            carried_sums = "\n"
            print(page_sums)
            for key in page_sums[page_number]:
                carried_sums += "<< /T(P.{0})/V({1}{2}) >>\n".format(key,page_sums[page_number][key]/100,unit[key])
                if page_number == 0:
                    file.write("<< /T(P.{0})/V({1}) >>\n".format(key,""))
                elif page_number in range(1,npages+1):
                    file.write(carried_sums)
                    print('carried_sums= '+carried_sums)
                page_sums[page_number+1]["C"] = page_sums[page_number]["C"]
                page_sums[page_number+1]["D"] = page_sums[page_number]["D"]
                page_sums[page_number+1]["E"] = page_sums[page_number]["E"]
                    
            ############################                
            # Loop over next ten items #
            ############################
            for item in range(first_item,last_item):
                if item == len(data):
                    for empty in range(item%10, 10):
                        for key in data[0]:
                            if key == "image":
                                continue
                            key_string = "{0}.{1}".format(empty,data_keys[key])
                            empty_key_value_pair = "<< /T({0})/V({1}) >>\n".format(key_string,"")
                            file.write(empty_key_value_pair)
                    break
                
                ############################
                # Loop over each parameter #
                ############################
                for key in data[item]:
                    form_field = data_keys[key]
                    if form_field == "Z" or "":
                        continue
                    
                    #######################################
                    # Write the <<\T()\V()>> pair to file #
                    #######################################
                    key_string = "{0}.{1}".format(item%10,form_field)
                    value_string = str(data[item][key])
                    key_value_pair = "<< /T({0})/V({1}) >>\n".format(key_string, value_string)
                    file.write(key_value_pair)
                    
                    ###############
                    # Update sums #     
                    ###############                                     
                    if form_field =="C":
                        page_sums[page_number+1]["C"] += int(data[item][key]*100)
                    if form_field =="D":
                        page_sums[page_number+1]["D"] += int(data[item][key]*100)
                    if form_field =="E":
                        page_sums[page_number+1]["E"] += int(data[item][key]*100)
                    #print(page_sums[page_number+1]["D"])
                        
            #########################
            # Write page final sums #
            #########################   
            for key in page_sums[page_number+1]:
                print('page sums')
                print(page_sums)
                print('key= '+key)
                if page_number == npages+1:
                    break
                sums_key_value_pair = "<< /T(S.{0})/V({1}{2}) >>\n".format(key,float(page_sums[page_number+1][key])/100,unit[key])
                print(str(page_number)+'\t'+str(item)+'\t'+sums_key_value_pair)
                file.write(sums_key_value_pair)
                #print(sums_key_value_pair)

            ###################################
            # Write footer and close fdf file #
            ###################################
            file.write(extra_footer)
            file.write(fdf_footer)
            parsed_fdf = file.read()
            
        #############################################################
        # bash command pdftk uses fdf to create, fill and write pdf #
        #############################################################
        fill_form_in_bash = "pdftk {0}/{1} fill_form {2}/page-{4}.fdf output {3}/page-{4}.pdf flatten".format(path_pdf_templates,extra_templates[page_number%2],path_fdf_dir,page_output_dir,page_number)
        system(fill_form_in_bash)

    ##############################
    # Assemble the finished list #
    ##############################
    finished_list_pages = []
    for finished_list_page in natsorted(listdir(page_output_dir)):
        finished_list_pages.append("{0}/{1}".format(page_output_dir,str(finished_list_page)))
    str_finished_list = " ".join(finished_list_pages)

    ###########################
    # Assemble the final pdfs #
    ###########################
    yeeah = (" ( •_•)","( •_•)>⌐■-■\n(⌐■ _■ )")
    for index in range(len(front_page_templates)):
        current_front_page = path.join(path_pdf_templates,front_page_templates[index])
        system("pdftk {0} {1} cat output {2}".format(current_front_page,str_finished_list,path.join(carnet_output_dir,outputs[index])))
        print("{} \t File written {}".format(yeeah[index],outputs[index]))
        
    ################################
    # Create image pdf if possible #
    ################################
    assembleImages(basedir, options.sheet, outputs[2], carnet_archive_dir, options.font, options.test)
    
    ##################
    # Archive a copy #
    ##################
    mkdir(carnet_archive_dir)
    system("cp {} {}".format(path.join(carnet_output_dir,outputs[0]), carnet_archive_dir))
    system("cp {} {}".format(path.join(carnet_output_dir,outputs[1]), carnet_archive_dir))
    system("cp {} {}".format(path.join(carnet_output_dir,outputs[2]), carnet_archive_dir))
    print("\n\n (\____/) \n( ͡ ͡° ͜ ʖ ͡ ͡°)\n  \╭☞ \╭☞\n\n \t ʕ •́؈•̀)\nArchived in {}.".format(archive))   
