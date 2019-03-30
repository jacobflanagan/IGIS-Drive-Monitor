import exifread

import datetime, shutil, os

#own imports
import subFormat as sf

def dirparts(dir):
	return list(filter(None,dir.replace("/","\\").split("\\")))

def dictlist2csv(dict_list, filename):
	
	import csv
	
	with open(filename, 'w') as f:
		
		w = csv.DictWriter( f, dict_list[0].keys(), lineterminator='\n' )
		w.writeheader()
		for dict in dict_list:
			w.writerow(dict)
			
	f.close()
	
def get_imagelist(dir, q = None):
	
	import hashlib
	
	imgext = ['img','tif','jpg']
	dir = "\\".join(dirparts(dir))
	il = sf.find_files(dir,imgext, recursive=False)
	
	d_il = []
	ind = 0
	
	for i in il:
		ind = ind+1
		imagename = dirparts(i)[-1]
		checksum = hashlib.md5( open(i,'rb').read() ).hexdigest()
		d_il.append( {"image":imagename, "MD5":checksum} )
		if q:
			q.put( int( ind*100/len(il) ) )
	
	return d_il

class images():
	
	#class vars: imagefiles, sensors
	
	def __init__(self, directory, sq, pq, exit):
		
		self.exit = exit
		self.pq = pq
		self.sq = sq
		
		self.GCPs = False
		
		imgext = ['img','tif','jpg']
		print ('Searching files for extensions ' + ", ".join(imgext) + ".")
		self.sq.put('Searching')
		self.pq.put(101)
		#get a list of images on the drive
		ifiles = sf.find_files(directory,imgext)
		self.imagefiles = {}
		
		#get sensor information
		sensors = []
		min_dt = datetime.datetime.strptime('3000','%Y')
		max_dt = datetime.datetime.strptime('1000','%Y')
		
		if not len(ifiles):
			print('No images found.')
			return
		print ('Found ' + str(len(ifiles)) + ' images. Meta analysis initiated.' )
		
		self.sq.put('Analysing Images') 
		self.pq.put(0)
		
		i,l = 0,len(ifiles)
		for ifile in ifiles:
			
			i=i+1
			#print ( int( (i/l)*100 ), self.exit.is_set() )
			self.pq.put( int( (i/l)*100 ) )
			
			if self.exit.is_set(): 
				print ( 'Image meta analsys halted.' )
				self.pq.put( 0 )
				return
			f = open(ifile,'rb')
			tags = exifread.process_file(f)
			f.close()
			
			#add image to image dictionary
			try:
				sensor = str(tags["Image Model"])
				dt = datetime.datetime.strptime(str(tags['Image DateTime']),"%Y:%m:%d %H:%M:%S") #is it always formatted this way?
			except: #missing some important tag info, skip it
				continue
			self.imagefiles[ifile] = {'sensor':sensor, 'datetime':dt}
			
			#add to sensor list
			sensors.append(str(tags["Image Model"]))
			if dt < min_dt: min_dt = dt
			if dt > max_dt: max_dt = dt
			
		#store unique sensors to class variable
		self.sensors = list(set(sensors))
		self.min_datetime = min_dt
		self.max_datetime = max_dt
		
		print ( 'Analysis complete.' )
		self.sq.put('Done')
		
	def copy_images(self, proj_dst, blockname, keep_src = False, cr8_imagelist = True): #source files are in self.imagefiles
		
		def bool2str(b):
			if b: return "true"
			else: return "false"
		
		print( 'Copying source images with deletion set to: ' + bool2str(not keep_src) )
		l=len(self.imagefiles)
		if l<1: 
			#print ("No Images found.")
			return
		i = 0
		#sf.printProgressBar(i, l, prefix = 'Copy in Progress:', suffix = 'Complete', length = 50)
		self.sq.put('Copying Images')
		self.pq.put(0)
		sf.ensure_dir(proj_dst+'/'+blockname+"/fake.txt")
		for ifile in self.imagefiles:
			if not self.exit.is_set(): #using the parent thread/mp event to determine when to quit
				if keep_src: shutil.copy2(ifile, proj_dst+'/'+blockname+'/'+blockname+"_"+sf.dir2file(ifile))
				else: shutil.move(ifile, proj_dst+'/'+blockname+'/'+blockname+"_"+sf.dir2file(ifile))
				i = i+1
				self.pq.put( int( (i/l)*100 ) )
				#sf.printProgressBar(i, l, prefix = 'Copy in Progress:', suffix = 'Complete', length = 50)
			else:
				print ( 'Copy was Cancelled. Successfully copied %.2f' % ((i/l)*100) + "% of detected images." )
				self.sq.put('Cancelled')
				return
		
		#create imagelist with image checksum and processing tag process0
		if cr8_imagelist:
			dictlist2csv(get_imagelist(proj_dst+'\\'+blockname), proj_dst+'\\'+blockname+"\\imagelist.process0")
		
		if self.GCPs:
			try:
				os.mkdir(proj_dst+'\\'+blockname+"\\GCPs")
			except:
				print( 'Directory "GCPs" already existed in destination.' )
		
		print( 'Copy complete.')
		self.sq.put('Done')
