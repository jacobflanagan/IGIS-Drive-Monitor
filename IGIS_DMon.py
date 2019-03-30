#from tkinter import *
import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import simpledialog
import tkinter.ttk as ttk

#import multiprocessing as mp
#import threading as mp
#from multiprocessing.queues import Queue
from queue import Queue
from threading import Thread
from threading import Event

import sys, time, os

import subprocess as sp

import DMon_proc as DP
import image_manager as IM
import pix4d as p4d
import subFormat as sf
import rm_empty_dirs as rmed

#wrapper - output
def text_catcher(text_widget,queue):
	while True:
		t = queue.get().strip('\n').strip('\r')
		#print ("\r" in t)
		
		if t is not "": 
			text_widget.configure(state="normal")
			text_widget.insert(tk.END,  time.strftime("\n%Y-%m-%d %H:%M:%S: ", time.gmtime()), "bold" ) #time.strftime('\n%Y-%m-%d %H:%M:%S GMT', time.gmtime())
			text_widget.insert(tk.END, t)
			text_widget.configure(state="disabled")
			text_widget.see("end")

def progress_catcher(progress_widget,queue):
	while True:
		t = queue.get()
		#maybe check a number validity here
		if t > 100: #101+ are codes used to communicate
			statusbar.progress.configure(mode='indeterminate')
			statusbar.progress.start(10)
		else:
			statusbar.progress.stop()
			statusbar.progress.configure(mode='determinate')
			progress_widget['value'] = t
		
def status_catcher(status_var,queue):
	while True:
		t = queue.get()
		status_var.set(t)

# Queue that behaves like stdout
class StdoutQueue(Queue):
    def __init__(self,*args,**kwargs):
        Queue.__init__(self,*args,**kwargs)

    def write(self,msg):
        self.put(msg)

    def flush(self):
        sys.__stdout__.flush()

def getPix4DCredentials(cred_file):
	
	import os
	
	creds = {}
	creds["email"]=""
	creds["password"]=""
	creds["executable"]='C:\\Program Files\\Pix4Dmapper\\pix4dmapper.exe'
	
	if not os.path.isfile(cred_file): #create file with empty credential if it doesn't exist
		
		cf = open(cred_file,"w")
		for key in creds:
			cf.write( key + "=" + str(creds[key]) + "\n" )
		cf.close()
	
	cf = open(cred_file,"r")
	for line in cf:
		k, v = line.replace("\n","").split("=")
		creds[k]=v
	cf.close()
	
	return creds

class settings(dict):
	
	def __init__(self, file, *args, **kwargs):
		
		super(settings, self).__init__(*args, **kwargs)
		for arg in args:
			if isinstance(arg, dict):
				for k, v in arg.items():
					self[k] = v
					
		if kwargs:
			for k, v in kwargs.items():
				self[k] = v

		import json
		self.file = file
		
		try:
			with open(file, 'r') as f:
				items = json.load(f)
				for k, v in items.items():
					self[k] = v
			f.close()
		except: #start a new file
			self['project']=''
			self['block']=''
			self['monitor']=''
			self['keep source']=False
			self['image list process flag']=False
	
	def write(self):
		
		import json
		
		with open(self.file,'w') as file:
			json.dump(self, file, indent=2)
		file.close()
	

def disable_interface():
	
	global proj_ent
	global proj_btn
	
	global block_chk_date
	global block_chk_time
	global block_chk_sensor
	global block_chk_height
	global block_text
	
	global mon_btn
	global mon_text
	
	global man_ent
	global man_btn
	global man_btn_proc
	
	global advancedmenu
	
	elements_list = ( 
							proj_ent,
							proj_btn,
							
							block_chk_date,
							block_chk_time,
							block_chk_sensor,
							block_chk_height,
							block_text,
							
							mon_btn,
							mon_text,
							
							man_ent,
							man_btn,
							man_btn_proc,
						)
						
	for i in elements_list:
		i.config(state=tk.DISABLED)
	
	#menu items are "special" (do same as above if adding additional items)
	advancedmenu.entryconfig("Keep Copied Files", state="disable")
	advancedmenu.entryconfig("Create Image List with Processing Flag", state="disable")
	
	return
	
def enable_interface():
	global proj_ent
	global proj_btn
	
	global block_chk_date
	global block_chk_time
	global block_chk_sensor
	global block_chk_height
	global block_text
	
	global mon_btn
	global mon_text
	
	global man_ent
	global man_btn
	global man_btn_proc
	
	global advancedmenu
	
	elements_list = ( 
							proj_ent,
							proj_btn,
							
							block_chk_date,
							block_chk_time,
							block_chk_sensor,
							block_chk_height,
							block_text,
							
							mon_btn,
							mon_text,
							
							man_ent,
							man_btn,
							man_btn_proc,
						)
						
	for i in elements_list:
		i.config(state=tk.NORMAL)
	
	#menu items are "special" (do same as above if adding additional items)
	advancedmenu.entryconfig("Keep Copied Files", state="normal")
	advancedmenu.entryconfig("Create Image List with Processing Flag", state="normal")
	
	return

def monitor_clicked(q):
	global mon_state
	global mon_btn
	global mon_btn_orig_color
	global mon_text
	
	global mon_proc
	global output_lbox
	
	global block_text
	global namedate
	global nametime
	global namesensor
	global nameheight
	
	if mon_state:
		
		#create the new monitor and start it
		mon_proc.shutdown()
		mon_proc.join()
		#messagebox.showinfo("Complete","Please Remove Drive")
		
		mon_btn.config(text="Monitor", bg=mon_btn_orig_color)
		enable_interface()
		mon_state = False
		
	else:
		
		#check project location validity
		if proj_ent.get() == "":
			q.put("A valid project location must be given.")
			return
		
		mon_btn.config(text="Monitor", bg="salmon")
		disable_interface()
		mon_btn.config(state=tk.NORMAL) #reenable monitor button
		mon_state = True
		
		block_elements = {'blockname':block_text.get(), 'date':bool(namedate.get()), 'time':bool(nametime.get()), 'height':bool(nameheight.get()), 'sensors':bool(namesensor.get())}
		mon_proc = DP.Monitor(mon_text.get(), proj_ent.get(), block_elements,  q, pq, sq, keep_var.get(), imagelist_flag.get() ) #send the Drive Lable to look for
		mon_proc.start()
		
	return

def proj_clicked():
	global win
	global proj_ent
	win.directory = filedialog.askdirectory(initialdir = proj_ent.get(), title = "Select Project Location Folder")
	if win.directory is not "": proj_ent.delete(0, tk.END)
	proj_ent.insert(tk.END, win.directory)
	return
	
def imagelist_clicked():
	
	global commondir
	global pq #progress queue
	
	directory = filedialog.askdirectory(initialdir = commondir, title = "Select Image Folder")
	
	def createimagelist(dir):
		disable_interface()
		q.put( "Creating image list with processing flag for: \n" + dir )
		sq.put( "Generating List" )
		il = IM.get_imagelist(dir, pq)
		
		if il:
			IM.dictlist2csv(il, dir+"\\imagelist.process0")
			q.put( "Image list created.")
		else:
			q.put( "No images found in directory: \n" + dir )
		enable_interface()
		sq.put( "Idle" )
		pq.put(0)
				
	if directory:
		commondir = directory
		t = Thread(target=createimagelist,args=(directory,))
		t.daemon = True
		t.start()
	
def man_clicked():
	global win
	global man_ent
	win.directory = filedialog.askdirectory()
	if win.directory is not "":
		man_ent.delete(0, tk.END)
		man_ent.insert(tk.END, win.directory)
	return
	
def process_dir():
	
	global man_state
	global proc_exit
	global man_ent
	global q
	global pq
	global sq
	global proj_ent
	global block_text
	global keep_var
	
	sys.stdout = q
	
	disable_interface()
	man_btn_proc.config(state=tk.NORMAL) 
	q.put("Processing directory: " + man_ent.get() )
	
	images = IM.images( man_ent.get(), sq, pq, proc_exit )
	
	if proc_exit.is_set(): return
	
	blockname_elements = {'blockname':block_text.get(), 'date':bool(namedate.get()), 'time':bool(nametime.get()), 'height':bool(nameheight.get()), 'sensors':bool(namesensor.get())}
	
	if len(images.imagefiles): #only process if files found
		#name elements
		datetxt = ""
		timetxt = ""
		sensortxt = ""
		if blockname_elements['date']: 
			datetxt = images.min_datetime.strftime("%Y-%m-%d") + "_"
			print ( 'Images start date: ' + images.min_datetime.strftime("%Y-%m-%d") )
		if blockname_elements['time']: 
			timetxt = images.min_datetime.strftime("%H%M")
			print ( 'Images start time: ' + images.min_datetime.strftime("%H%M") )
		if blockname_elements['sensors']: 
			sensortxt = "_" + "_".join(images.sensors)
			print ( 'Images sensor(s): ' + ", ".join(images.sensors) )
		if blockname_elements['height']:
			images.GCPs = True
		
		blockname = datetxt + blockname_elements['blockname'] + timetxt + sensortxt
		
		print ("Processing drive with blockname: ")
		print (blockname)
		
		#status indication
		images.copy_images( proj_ent.get(), blockname, keep_var.get(), imagelist_flag.get() )
		
		#clean up source; dirs emptied by script are removed
		if not keep_var.get():
			q.put("Removing empty directories from source.")
			rmed.rmEmptyDirs( proj_ent.get() )
	
	pq.put(0)
	sq.put('Idle')
	
	if not proc_exit.is_set(): q.put("Processing Finished.")
	enable_interface()
	man_state = False
	
def manproc_clicked():
	
	global proc_t
	global man_state
	global proc_exit
	
	if man_ent.get() == "":
		
		q.put( "Invalid directory. Processing Aborted." )
		return
	
	if man_state:
		
		proc_exit.set() #communicate to threaded function to stop
		q.put("Processing cancelled by user.")
		enable_interface()
		man_state = False
		
	else:
		
		# Instantiate and start the processing thread
		proc_exit.clear() #reset the communicater
		proc_t = Thread(target=process_dir,args=())
		proc_t.daemon = True
		proc_t.start()
		man_state = True
	
	return
	
def on_closing():
	global d_settings
	global win
	
	global proj_ent
	global block_text
	global mon_text
	
	d_settings['project'] = proj_ent.get() 
	d_settings['block'] = block_text.get()
	d_settings['monitor'] = mon_text.get()
	d_settings['keep source'] = bool( keep_var.get() )
	d_settings['image list process flag'] = bool( imagelist_flag.get() )
	
	d_settings.write()
	
	win.destroy()
	
def update_block():
	global namedate
	global nametime
	
	
# GUI Stuff
class StatusBar(tk.Frame):   
	def __init__(self, master):
		tk.Frame.__init__(self, master)
		self.variable=tk.StringVar()
		self.statusmsg = tk.StringVar()
		self.label=tk.Label(self, bd=1, relief=tk.GROOVE, anchor=tk.E,
						   textvariable=self.variable,
						   font=('arial',9,'normal'))
		#self.variable.set('Status Bar')
		self.label.pack(side=tk.LEFT, fill=tk.X, expand=1)
		
		self.statuslbl = tk.Label(self.label, relief=tk.FLAT, anchor=tk.E, textvariable=self.statusmsg)
		self.statusmsg.set('Idle')
		self.statuslbl.pack(side=tk.LEFT, fill=tk.X, expand=1)
		
		self.progress = ttk.Progressbar(self.label, orient="horizontal",length=100,mode='determinate')
		self.progress.pack(side=tk.RIGHT, padx=1, pady=1)

		self.pack()

def aboutDialogue( ):
	version = "0.1.2"
	messagebox.showinfo( "About", "IGIS Drive Monitor\nVersion: " + version + "\n\nUnpolished and unofficial,\nmade in haste with Python 3.\njpflanagan@ucanr.edu" )
	
def processData( datadir ):
	
	pix4dexe = p4d_creds["executable"]
	email = p4d_creds["email"]
	password = p4d_creds["password"]
	
	p4d.create_project(projname, imgdir, email, password, pix4dexe)

class processDialogue(tk.Toplevel):
	
	def __init__( self, master, dir ):
		
		super(processDialogue, self).__init__(master) #complete inherit
		self.parent = master
		self.dir = dir
		
		global proj_ent
		
		self.title("Pix4D Project Creation")
		try:
			self.iconbitmap('pix4d.ico')
		except:
			pass
		self.grab_set()
		#self.geometry("350x420")
		self.resizable(False, False)
		self.focus_set()
		self.protocol("WM_DELETE_WINDOW", self.cancel)
		#self.bind("<FocusOut>", self.focus_set())
		
		tf = tk.Frame(self, padx=5, pady=5, width=350)
		tf.pack(side=tk.TOP,fill="x")
		self.build_toppane(tf)
		
		bf = tk.Frame(self)
		bf.pack(side=tk.BOTTOM, fill="x")
		self.build_bottompane(bf)
		
	def build_toppane(self, root):
		
		def dir_clicked():
			
			self.dir = filedialog.askdirectory(initialdir = self.dir, title = "Select Project Location Folder", parent=self)
			#root.lower()
			if self.dir is not "": self.e1.delete(0, tk.END)
			self.e1.insert(tk.END, self.dir)
			
		def create_clicked():
			
			l = len( sf.find_files(self.dir, ['img','tif','jpg'], recursive=False) )
			
			if l == 0:
				o_lbox_write( "Directory contains no images, project creation aborted." )
				return
				
			o_lbox_write( "Directory contains " + str(l) + " images." )
			
			dirparts = list( filter( None, self.dir.replace('\\','/').split('/') ) )
			dirparts.append( dirparts[-1] + ".p4d" )
			
			o_lbox_write( "Creating project as " + "/".join(dirparts) )
			o_lbox_write( "Standby, this could take a while..." )
			
			def work ():
				
				projname = "/".join(dirparts)
				
				btn2.configure( state="disabled" )
				self.statb.statusmsg.set("Creating project")
				self.statb.progress.configure(mode='indeterminate')
				self.statb.progress.start(10)
				#time.sleep(10)
				p4d.create_project_nolic( projname, self.dir )
				o_lbox_write( "Project created." )
				btn2.configure( state="normal" )
				self.statb.progress.stop()
				self.statb.progress.configure(mode='determinate')
				
				o_lbox_write( "Opening project " + projname + "." )
				sp.Popen(projname,shell=True)
				self.statb.statusmsg.set("Idle")
			
			t = Thread(target=work,args=())
			t.daemon = True
			t.start()
		
		LF1 = tk.LabelFrame(root, text="Image Directory:", padx=5, pady=5, height = 200)
		LF1.pack(side="top", fill = "x")
		LF2 = tk.LabelFrame(root, text="Project Name:", padx=5, pady=5, height = 200)
		LF2.pack(side="bottom", fill="x")
		
		#directory input
		self.e1 = tk.Entry( LF1, relief=tk.FLAT, borderwidth = 5 )
		self.e1.insert( tk.END, self.dir )
		btn = tk.Button(LF1, text="...", command=dir_clicked, padx=5, pady=5, borderwidth = 1) 
		btn.config( height = 1, width = 1)
		self.e1.pack(side = tk.LEFT, fill="x", expand="yes")
		btn.pack(side=tk.LEFT, padx=5, pady=5)
		
		btn2 = tk.Button(LF1, text="Create", command=create_clicked, padx=5, pady=5, borderwidth = 1)
		btn2.pack(side=tk.RIGHT, padx=5, pady=5)
		
		o_lbox = tk.Text(LF2, borderwidth = 0, relief=tk.FLAT, state="disabled", font=("Helvetica", 8), width = 60, height = 20) #height=5, 
		o_lbox.tag_configure("bold", font="Helvetica 8 bold")
		sb = tk.Scrollbar(LF2, orient="vertical")
		sb.config(command=o_lbox.yview)
		o_lbox.config(yscrollcommand=sb.set)
		sb.pack(side=tk.RIGHT, fill="y")
		o_lbox.pack(side=tk.LEFT, fill="both", expand=True) 
		
		o_lbox.configure(state="normal")
		o_lbox.insert(tk.END,  time.strftime("%Y-%m-%d %H:%M:%S: ", time.gmtime()), "bold" )
		o_lbox.insert(tk.END, "Logging using UTM time.")
		o_lbox.configure(state="disabled") #prevent user from writing to output
		
		def o_lbox_write(text):
			
			t = text.strip('\n').strip('\r')
			
			if t is not "": 
				o_lbox.configure(state="normal")
				o_lbox.insert(tk.END,  time.strftime("\n%Y-%m-%d %H:%M:%S: ", time.gmtime()), "bold" ) #time.strftime('\n%Y-%m-%d %H:%M:%S GMT', time.gmtime())
				o_lbox.insert(tk.END, t)
				o_lbox.configure(state="disabled")
				o_lbox.see("end")
		#self.e2 = tk.Entry( LF2, relief=tk.FLAT, borderwidth = 5 )
		#self.e2.pack( fill="x", expand="yes" )
		
	def build_bottompane(self, root):
		
		self.statb = StatusBar(root)
		self.statb.pack(side=tk.BOTTOM,fill="both")
	
	def cancel(self, event=None):

		# put focus back to the parent window
		self.parent.focus_set()
		self.destroy()


##MAIN
if __name__ == "__main__":	

	#some global vars
	default_label = "IGIS"
	default_blockname = "BlockName"
	mon_state = False
	man_state = False
	proc_t = Thread(target=process_dir,args=())
	proc_exit = Event()
	commondir = os.getcwd()
	
	#load or create settings
	d_settings = settings('settings.json')
	p4d_creds = getPix4DCredentials('Pix4D.cred')
	
	q = StdoutQueue( maxsize=-1 ) #, ctx=mp.get_context() )
	pq = Queue( maxsize=-1 ) #, ctx=mp.get_context() )
	sq = Queue( maxsize=-1) #, ctx=mp.get_context() )

	win = tk.Tk()
	win.title("IGIS Drive Monitor")
	try:
		win.iconbitmap('igis.ico')
	except:
		pass
	#win.geometry("350x600")
	#win.minsize(600, 300)
	win.resizable(False, False)
	
	##MENU BAR
	menubar = tk.Menu(win)

	#Process Menu
	processmenu = tk.Menu( menubar, tearoff=0 )
	processmenu.add_command( label="Create Pix4D Project", command=lambda:processDialogue( win, dir=proj_ent.get() ) )
	processmenu.add_command( label="Create Image List/Processing Flag", command=imagelist_clicked )
	menubar.add_cascade( label="Tools", menu=processmenu )
	
	#Options Menu
	advancedmenu = tk.Menu(menubar, tearoff=0) #really, the options menu
	#advancedmenu.add_command(label="Keep Copied Files")
	keep_var = tk.IntVar(win)
	keep_var.set( d_settings['keep source'] )
	imagelist_flag = tk.IntVar(win)
	imagelist_flag.set( d_settings['image list process flag'] )
	advancedmenu.add_checkbutton(label="Keep Copied Files", onvalue=1, offvalue=0, variable=keep_var)
	advancedmenu.add_checkbutton(label="Create Image List with Processing Flag", onvalue=1, offvalue=0, variable=imagelist_flag)
	menubar.add_cascade(label="Options", menu=advancedmenu)
	
	#Help Menu
	helpmenu = tk.Menu( menubar, tearoff=0 )
	helpmenu.add_command( label="Help", command=lambda:sp.Popen('Help.pdf',shell=True) )
	helpmenu.add_command( label="About", command=aboutDialogue )
	menubar.add_cascade( label="Help", menu=helpmenu )

	win.config(menu=menubar)
	
	##PANES
	#Panes making up the windows
	left_pane = tk.Frame(win, width = 600)
	left_pane.grid(row=0, column=0, sticky="n")
	
	right_pane = tk.Frame(win, height = 300, width = 400)
	right_pane.grid(row=0, column=1, sticky="n")
	#frame.pack(side=tk.BOTTOM,fill="both", expand=True, padx=5, pady=5)
	
	bottom_pane = tk.Frame(win, height = 10)
	bottom_pane.grid(row=1, column=0, columnspan = 2, sticky="ew")
	
	label_pady = 5
	##LEFT PANE
	#project Label
	proj_lbl = tk.LabelFrame(left_pane, text="1.) Project Location", padx=5, pady=5, height = 65)
	proj_lbl.pack_propagate(0)
	proj_lbl.pack(side = tk.TOP, fill="both", expand="no", padx=5, pady=label_pady)
	
	proj_ent = tk.Entry(proj_lbl, borderwidth = 5, relief=tk.FLAT)
	proj_ent.insert(tk.END, d_settings['project'])
	proj_ent.pack(side = tk.LEFT, fill=tk.X, expand="yes", padx=5, pady=2)

	proj_btn = tk.Button(proj_lbl, text="...", command=proj_clicked, padx=5, pady=5, borderwidth = 1)
	proj_btn.config( height = 1, width = 1)
	proj_btn.pack(side = tk.RIGHT, padx=5, pady=5)

	#Block Label
	block_lbl = tk.LabelFrame(left_pane, text="2.) Block Naming", padx=5, pady=5, height = 200)
	block_lbl.pack_propagate(0)
	block_lbl.pack(side = tk.TOP, fill="both", expand="no", padx=5, pady=label_pady)

	namedate = tk.IntVar(value=1)
	block_chk_date = tk.Checkbutton(block_lbl, text = "Date Prefix", variable = namedate, borderwidth=1, relief=tk.FLAT, command = update_block)
	block_chk_date.grid(row=0,column=0)

	nametime = tk.IntVar(value=1)
	block_chk_time = tk.Checkbutton(block_lbl, text = "Start Time", variable = nametime, borderwidth=1, relief=tk.FLAT)
	block_chk_time.grid(row=0,column=1)

	namesensor = tk.IntVar(value=1)
	block_chk_sensor = tk.Checkbutton(block_lbl, text = "Sensor", variable = namesensor, borderwidth=1, relief=tk.FLAT)
	block_chk_sensor.grid(row=0,column=2)

	nameheight = tk.IntVar(value=1)
	block_chk_height = tk.Checkbutton(block_lbl, text = "Contains GCPs", variable = nameheight, borderwidth=1, relief=tk.FLAT)
	block_chk_height.grid(row=0,column=3)
	
	block_frame = tk.Frame(block_lbl)	
	block_frame.grid( row=1, column=0, columnspan=4, sticky='ew' )
	
	block_lbl_help = tk.Label(block_frame, text = "Core Name:")
	#block_lbl_help.grid(row=1,column=0,sticky=tk.W)
	block_lbl_help.pack(side = tk.LEFT)

	block_text = tk.Entry(block_frame, text = "Base Name", borderwidth = 5, relief=tk.FLAT)
	block_text.insert(tk.END, d_settings['block'])
	block_text.pack(side = tk.LEFT, fill=tk.X, expand="yes", padx=4, pady=2)
	#block_text.grid(row=1,column=1,columnspan=3, padx=4, pady=2, sticky=(tk.E,tk.W))

	#monitor Label
	mon_lbl = tk.LabelFrame(left_pane, text="3.) Drive Monitor", padx=5, pady=5, height = 65)
	mon_lbl.pack_propagate(0)
	mon_lbl.pack(side = tk.TOP, fill="both", expand="no", padx=5, pady=label_pady)

	mon_btn = tk.Button(mon_lbl, text="Monitor", command=lambda:monitor_clicked(q), padx=5, pady=5, borderwidth = 1)
	mon_btn.pack(side = tk.RIGHT, padx=5, pady=5)
	#mon_btn.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W+tk.E)

	mon_btn_orig_color = mon_btn.cget("background")

	mon_lbl_help = tk.Label(mon_lbl, text = "Monitor for Label:")
	#mon_lbl_help.grid(row=0,column=0,sticky=tk.W)
	mon_lbl_help.pack(side=tk.LEFT)
	
	mon_text = tk.Entry(mon_lbl, borderwidth = 5, relief=tk.FLAT)
	mon_text.insert(tk.END, d_settings['monitor'])
	mon_text.pack(side = tk.LEFT, fill=tk.X, expand="yes", padx=4, pady=2)
	#mon_text.grid(row=0, column=1, columnspan=2, padx=4, pady=2)

	#Manual Label
	man_lbl = tk.LabelFrame(left_pane, text="(Optional) Manually Process Directory", padx=5, pady=5, height = 65)
	man_lbl.pack_propagate(0)
	man_lbl.pack(side = tk.TOP, fill="both", expand="no", padx=5, pady=label_pady)

	man_ent = tk.Entry(man_lbl, borderwidth = 5, relief=tk.FLAT)
	man_ent.pack(side = tk.LEFT, fill=tk.X, expand="yes", padx=4, pady=2)

	man_btn = tk.Button(man_lbl, text="...", command=man_clicked, padx=5, pady=5, borderwidth = 1) #borderwidth=0, relief=tk.SOLID, highlightbackground = "#C0C0C0", highlightcolor = "#C0C0C0"
	man_btn.config( height = 1, width = 1)
	man_btn.pack(side = tk.LEFT, padx=5, pady=5)

	man_btn_proc = tk.Button(man_lbl, text="Process", command=lambda:manproc_clicked(), padx=5, pady=5, borderwidth = 1)
	man_btn_proc.pack(side = tk.RIGHT, padx=5, pady=5)

	
	##RIGHT PANE
	#Output Label
	output_lbl = tk.LabelFrame(right_pane, text="Process Output", padx=5, pady=5, height = 100)
	output_lbl.pack_propagate(1)
	output_lbl.pack(fill="both", expand="yes", padx=5, pady=label_pady)
	
	output_lbox = tk.Text(output_lbl, borderwidth = 0, relief=tk.FLAT, state="disabled", font=("Helvetica", 8), width = 60, height = 20) #height=5, 
	output_lbox.tag_configure("bold", font="Helvetica 8 bold")
	scrollbar = tk.Scrollbar(output_lbl, orient="vertical")
	scrollbar.config(command=output_lbox.yview)
	output_lbox.config(yscrollcommand=scrollbar.set)
	scrollbar.pack(side=tk.RIGHT, fill="y")
	output_lbox.pack(side=tk.LEFT, fill="both", expand=True) #, padx=5, pady=5)
	
	output_lbox.configure(state="normal")
	output_lbox.insert(tk.END, time.strftime("%Y-%m-%d %H:%M:%S: ", time.gmtime()), "bold" )
	output_lbox.insert(tk.END, "Logging using UTM time.")
	output_lbox.configure(state="disable")
	
	statusbar = StatusBar(bottom_pane)
	statusbar.pack(side=tk.BOTTOM,fill="both")
	
	# Instantiate and start the text monitor
	monitor = Thread(target=text_catcher,args=(output_lbox,q))
	monitor.daemon = True
	monitor.start()
	#Instantiate and start the progress monitor
	pmon = Thread( target=progress_catcher,args=(statusbar.progress,pq) )
	pmon.daemon = True
	pmon.start()
	#Instantiate and start the status message monitor
	smon = Thread( target=status_catcher,args=(statusbar.statusmsg,sq) )
	smon.daemon = True
	smon.start()
	
	#p = ttk.Progressbar(bottom_pane, orient="horizontal",length=100,mode='determinate')
	#p.pack(side=tk.BOTTOM, padx = 2, pady = 2)
	
	#init creation, should be overwritten anyway
	mon_proc = DP.Monitor(default_label, proj_ent.get(), {}, q, pq, sq, d_settings['keep source'], d_settings['image list process flag'] )
	
	win.protocol("WM_DELETE_WINDOW", on_closing)
	tk.mainloop()
	
	#this is cheap, but works for now (in case monitor was left running)
	try: 
		mon_proc.shutdown()
	except:
		print ("Shutdown")