import tkinter as tk

import win32api
import time, datetime

#import multiprocessing as mp
from threading import Thread
from threading import Event

import sys

import winsound

#own imports
import image_manager as IM
import rm_empty_dirs as rmed

target_label = "IGIS" #drive name to watch for (REMOVED)
monitor_time = 0.5 #in seconds

#global variables
toMonitor = False #(REMOVED)

class Monitor(Thread):
	
	#blockname_elements dictionary structure: {blockname:[BlockName Str], date:[Bool], time:[Bool], height:[Bool], sensor:[Bool]}
	def __init__(self, label, project, blockname_elements, q, pq, sq, keep_source = False, cr8_imagelist = True): #q = Output should be a stdout queue, p = progress, dictionary style
		Thread.__init__(self)
		self.exit = Event()
		self.project = project
		self.label = label
		self.blockname_elements = blockname_elements
		self.q = q
		self.pq = pq
		self.sq = sq
		self.keep_source = keep_source
		self.cr8_imagelist = cr8_imagelist
		
	def toggle(self):
		self.exit.set()
		
	def run(self):
		
		sys.stdout = self.q
		
		print( "Monitoring drives..." )
		
		while not self.exit.is_set():
			
			self.sq.put("Monitoring Drives")
			self.pq.put(101) #progressbar waiting mode
			
			drives = win32api.GetLogicalDriveStrings()
			drives = drives.split('\000')[:-1]
			
			for drive in drives:
				
				label = win32api.GetVolumeInformation(drive)
				
				#print (label)
				
				if label[0] == self.label:
					
					print ("Drive found with label: " + self.label)
					
					#do the work
					images = IM.images( drive, self.sq, self.pq, self.exit )
					
					#print ('moving on', self.exit.is_set() )
					
					if self.exit.is_set(): 
						self.sq.put('Cancelled')
						return
					
					if len(images.imagefiles): #only process if files found
						#name elements
						datetxt = ""
						timetxt = ""
						sensortxt = ""
						if self.blockname_elements['date']: 
							datetxt = images.min_datetime.strftime("%Y-%m-%d") + "_"
							print ( 'Images start date: ' + images.min_datetime.strftime("%Y-%m-%d") )
						if self.blockname_elements['time']: 
							timetxt = images.min_datetime.strftime("%H%M")
							print ( 'Images start time: ' + images.min_datetime.strftime("%H%M") )
						if self.blockname_elements['sensors']: 
							sensortxt = "_" + "_".join(images.sensors)
							print ( 'Images sensor(s): ' + ", ".join(images.sensors) )
						if self.blockname_elements['height']:
							images.GCPs = True
						
						
						blockname = datetxt + self.blockname_elements['blockname'] + timetxt + sensortxt
						
						print ( "Processing drive with blockname: " + blockname )
						
						#status indication
						#self.sq.put("Copying Images")
						
						images.copy_images(self.project, blockname, keep_src = self.keep_source, cr8_imagelist = self.cr8_imagelist)
					
					##post copy
					#clean up source; dirs emptied by script are removed
					if not self.keep_source:
						print("Removing empty directories from source.")
						rmed.rmEmptyDirs( drive )
					
					self.sq.put("Remove Drive")
					self.pq.put(101) #reset the progress bar
					if not self.exit.is_set(): print ("Drive has been processed, please remove to continue (Properly eject if necessary)...")
					
					#make a sound
					try:
						winsound.PlaySound('done.wav',winsound.SND_FILENAME)
					except:
						pass
					
					#wait until drive ejection (or a label rename)
					i=0
					while not self.exit.is_set():
						time.sleep(monitor_time)
						try: 
							if win32api.GetVolumeInformation(drive)[0] == self.label: #probably a better method for checking if plugged in. "Stuck in Thread" issue when calling shutdown
								#if i and i%10 == 0: 
								#	print ("Waiting for drive removal...")
								#i+=1
								continue
						except:
							break
					
					if not self.exit.is_set(): print ("Drive removed. Drive Monitoring now resuming.")
					
			time.sleep(monitor_time)
		
		print ("Monitoring drives ceased.")
		self.sq.put("Idle")
		self.pq.put(0)
			
	def shutdown(self):
		
		orig_stdout = sys.stdout
		sys.stdout = self.q
		
		try:
			print ("Shutting down drive monitor...")
		except:
			sys.stdout = orig_stdout
			print ("Shutting down drive monitor...")
		
		self.exit.set()
