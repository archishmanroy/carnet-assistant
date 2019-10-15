# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont
from os import path, listdir, getcwd, unlink, system
from natsort import natsorted
import shutil, json, argparse
from time import strftime


def checkImages(data, containingDirectory):
    # Flags missing images, extra images, and duplicate filenames
    images = []
    for element in data:
        images.append(str(element['image']))
        
    files = listdir(containingDirectory)
    filelist = [path.splitext(path.basename(filename))[0] for filename in files]
    missing_dir = [filename for filename in filelist if filename not in images]
    missing_list = [element for element in images if element not in filelist]
    duplicates_set = set([x for x in filelist if filelist.count(x) > 1])
    if len(duplicates_set) > 0 or len(data) != len(files) or len(missing_list) > 0 :
        print('Image check failed.')
        if len(duplicates_set) > 0:
            print('ERROR Filenames must be unique. Dont forget to update spreadsheet if you change one. \n\tDuplicated files: '+', '.join(duplicates_set))
        print(len(data))
        print(len(files))
        if len(data) != len(files):
            print("ERROR Did you take too many selfies?")
            print("\tThe {} lacks {} image/s.".format( 'image folder' if (len(data)>len(files) ) else 'spreadsheet', abs(len(data)-len(listdir(containingDirectory)))))

        if len(missing_list) > 0 :
            print('ERROR Filenames do not match up:')
            print("\tImages missing from the spreadsheet: {}".format(', '.join(missing_dir)))
            print("\tImages missing from the folder: {}".format(', '.join(missing_list)))   
        return 1

    return 0
    

def checkCountries(data):
# Check Country names are correct #
    
    country_codes = ['AF','AX','AL','DZ','AS','AD','AO','AI','AQ','AG','AR','AM','AW','AU','AT','AZ','BS','BH','BD','BB','BY','BE','BZ','BJ','BM','BT','BO','BQ','BA','BW','BV','BR','IO','BN','BG','BF','BI','CV','KH','CM','CA','KY','CF','TD','CL','CN','CX','CC','CO','KM','CG','CD','CK','CR','CI','HR','CU','CW','CY','CZ','DK','DJ','DM','DO','EC','EG','SV','GQ','ER','EE','ET','FK','FO','FJ','FI','FR','GF','PF','TF','GA','GM','GE','DE','GH','GI','GR','GL','GD','GP','GU','GT','GG','GN','GW','GY','HT','HM','VA','HN','HK','HU','IS','IN','ID','IR','IQ','IE','IM','IL','IT','JM','JP','JE','JO','KZ','KE','KI','KP','KR','KW','KG','LA','LV','LB','LS','LR','LY','LI','LT','LU','MO','MK','MG','MW','MY','MV','ML','MT','MH','MQ','MR','MU','YT','MX','FM','MD','MC','MN','ME','MS','MA','MZ','MM','NA','NR','NP','NL','NC','NZ','NI','NE','NG','NU','NF','MP','NO','OM','PK','PW','PS','PA','PG','PY','PE','PH','PN','PL','PT','PR','QA','RE','RO','RU','RW','BL','SH','KN','LC','MF','PM','VC','WS','SM','ST','SA','SN','RS','SC','SL','SG','SX','SK','SI','SB','SO','ZA','GS','SS','ES','LK','SD','SR','SJ','SZ','SE','CH','SY','TW','TJ','TZ','TH','TL','TG','TK','TO','TT','TN','TR','TM','TC','TV','UG','UA','AE','GB','US','UM','UY','UZ','VU','VE','VN','VG','VI','WF','EH','YE','ZM','ZW']

    entries = []
    for element in data:
        entries.append(str(element['country']))
    wrong_code = [entry for entry in entries if entry not in country_codes]
    if len(wrong_code) > 0:
        print('Country check failed.')
        print("\nUh oh- is that country on mars?: {}".format(wrong_code))
        return 1
    else:
        return 0

def assembleImages(basedir, sheet, out, archive_dir, font, labeltype):
    
    #######################
    # Define output paths #
    #######################
    output_dir = path.join(basedir,"output")
    preprocessed_images_dir = path.join(basedir,"images",sheet)
    postprocessed_images_dir = path.join(basedir,"images/.post")
    assembled_pages_dir = path.join(basedir,"images/.pages")
    image_dict = path.join(basedir,"dicts/image_dict.json")
    outfile = path.join(output_dir,out  )
    #archive_dir = path.join(output_dir,'archive',images_dict['archive'])

    
    if sheet not in listdir(path.join(basedir,"images")):
        print("Sheet name doesnt exist as image directory. Exiting.")
        quit()
    
    #########################################
    # Empty intermediate processing folders #
    #########################################
    
    for current_files in listdir(postprocessed_images_dir):
        file_path = path.join(postprocessed_images_dir,current_files)
        try:
            if path.isfile(file_path):
                if current_files != '.gitignore':
                    unlink(file_path)
        except Exception as e:
            print(e)
    
    for current_files in listdir(assembled_pages_dir):
        file_path = path.join(assembled_pages_dir,current_files)
        try:
            if path.isfile(file_path):
                if current_files != '.gitignore':
                    unlink(file_path)
        except Exception as e:
            print(e)
    
    ########################################
    # Define Page size and image placement #
    ########################################
    n_w, n_h = 2, 4
    dpi = 300
    w, h = int(8.27 * dpi), int(11.69 * dpi)  # A4 dimension 2481 * 3507
    
    header, footer, lmargin, rmargin = 100, 100, 100, 100
    r_hgap, r_vgap = 0.1, 0.2
    
    image_w, image_h = int((w - (lmargin + rmargin)) / (n_w + (n_w - 1) * r_hgap)), int((h - (footer + header)) / (n_h + (n_h - 1) * r_vgap))
    hgap, vgap = int((w - (lmargin + rmargin) - n_w * image_w) / (n_w - 1)), int((h - (footer + header) - n_h * image_h) / (n_h - 1))
    
    if image_w * n_w + hgap * (n_w - 1) + lmargin + rmargin > w or image_h * n_h + vgap * (n_h - 1) + footer + header > h:
        print("Computation error!")
    
    ##########
    # Images #
    ##########
    size = (image_w, image_h)
    overlay_x0 = 0
    overlay_y0 = 0
    overlay_height = image_h / 10
    overlay_width = image_w / 6
    overlay_x1 = overlay_x0 + overlay_width
    overlay_y1 = overlay_y0 + overlay_height
    overlay_size = int(overlay_height * 0.8)
    
    with open(image_dict) as file:
    	images_dict = json.load(file)
    
    ##################
    # Process images #
    ##################
    for img_infile_name in natsorted(listdir(preprocessed_images_dir)):
        if img_infile_name.startswith('.'):
            continue
        # get the file name and location
        img_infile = path.join(preprocessed_images_dir, img_infile_name)
        # get the image number from the dictionary
        if labeltype == 1:
            overlay_text = path.splitext(img_infile_name)[0]
        elif labeltype == 0:
    	    overlay_key = path.splitext(img_infile_name)[0]
    	    overlay_text = str(images_dict[overlay_key])
    
        img_outfile = path.join(postprocessed_images_dir, "_{0}.jpeg".format(overlay_text))
    
        # resize the image and convert to RGBA
        img = Image.open(img_infile).convert('RGB')
        img.thumbnail(size)
    
        # add the text box
        draw = ImageDraw.Draw(img)
        draw.rectangle(((overlay_x0, overlay_y0), (overlay_x1, overlay_y1)), fill="white")
        fnt = ImageFont.truetype(font, overlay_size)
        draw.text((overlay_x0, overlay_y0), overlay_text, font=fnt, fill=(0, 0, 0, 255))
        del draw
    
        # save the output
        img.save(img_outfile, "JPEG")
        print("Image {0} saved".format(img_infile_name))
    
    ##################
    # Assemble pages #
    ##################
    n_pages = int(float(len(listdir(postprocessed_images_dir))) / (n_w * n_h))
    for n_page in range(n_pages + 1):
        page = Image.new('RGB', (w, h), 'white')
        for file in range(n_w * n_h):
    	    #print(file)
    	    #print(n_page * n_h * n_w + file)
            if not path.isfile(path.join(postprocessed_images_dir, "_{}.jpeg".format(n_page * n_h * n_w + file +1))):
                break 	
            pos = (int(lmargin + ((file * image_w + (file - file / n_w) * hgap) % (w - (lmargin + rmargin)))), header + file // n_w * (image_h + vgap))
            #print(", ".join(file, header, file, n_w, image_h, vgap))
            page.paste(Image.open(path.join(postprocessed_images_dir,"_{}.jpeg".format(n_page * n_h * n_w + file +1))), box=pos)
        page.save(path.join(assembled_pages_dir,"page_{0:02d}.pdf".format(n_page)))
    
    #################################
    # Get list of all created pages #
    #################################
    list_of_pages = []
    for element in natsorted(listdir(assembled_pages_dir)):
    	list_of_pages.append(path.join(assembled_pages_dir,str(element)))
    str_list_of_pages = " ".join(list_of_pages)
    
    ##########################
    # Assemble the final pdf #
    ##########################
    files = sorted([path.join(assembled_pages_dir, file) for file in listdir(assembled_pages_dir)])
    file_list = " ".join(files)
    system("pdftk {0} cat output {1}".format(file_list,outfile))
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    # How to use the IMAGE ASSISTANT ################################################################
    #												#
    # 1. All images in /pre/ will be resized and graphically labeled with a number			#
    # 2. Two choices of how to label, use test=0 for json dictionary or 1 for image filename	#
    # 3. Processes images saved in /post/								#
    # 4. Then assembled into A4 pages (pdfs) and saved in pages					#
    # 5. Finally the pages are concatenated. Output pdf saved in ../Output/				#
    #												#
    # BY CATRIONA BRUCE 15/6/2018									#
    # catriona.bruce@tum.de										#
    # To create an the image list for WH3 carnet							#
    #												#	
    #												#
    # New users should define output paths, make sure their directory structure matches: 		#
    # Carnet-wh3(Carnet-Assistant(credentials,dicts,templates),Images(pages,pre,post),Output)	#					
    #################################################################################################
    
    #########################################################################################
    # Test mode is for when the spreadsheet doesn't match the pictures in source directory, #
    # In test mode (1) the pictures are labeled by file name,				#			   
    # otherwise (0) to use the dictionary created by carnet assistant    			#
    #########################################################################################
    
