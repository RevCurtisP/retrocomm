#!/usr/bin/python3
#Poshmark Packing Slip Generator
#uses Poshmark order notification email as input
#Requires Python 3.7 and FPDF library

import argparse
import email
import quopri
import urllib.request

from html.parser import HTMLParser
from fpdf import FPDF

class Order():

  section = -1
  sections = []
  contents = []
  images = []

  def __init__(self, shipfrom, seller):
    self.add_section("Shipping From")
    for line in shipfrom:
      self.add_content(line)
    self.add_section("Seller")
    self.add_content(seller)
    self.add_section("header")
  
  def add_section(self, section):
    self.section += 1
    self.sections.append(section)
    self.contents.append([])
    self.images.append("")

  def add_content(self, content):
    if self.section > -1:
      self.contents[self.section].append(content)

  def add_image(self, url):
    if self.section > -1:
      self.images[self.section] = url

  def get_content(self, section, multiple=False):
    if multiple:
      result = []
      for index in range(0,len(self.sections)):
        if self.sections[index] == section:
          tuple = self.contents[index], self.images[index]
          result.append(tuple)
    elif section in self.sections:
      index = self.sections.index(section) 
      result = self.contents[index]
    else:
      result = None
    return result

class PackSlip():

  def __init__(self, order):
    self.order = order
  
  def generate(self, pdf_name):
    self.left_margin = .75
    self.top_margin = 1
    self.pdf = FPDF("P", "in", "Letter")
    self.pdf.set_margins(self.left_margin, self.top_margin, self.left_margin)
    self.pdf.add_page()
    self.header()
    self.y = 3
    self.items()
    self.pdf.output(pdf_name)
    
  def header(self):
    self.pdf.set_font("Arial", "B", 24)
    self.pdf.cell(7, .5, "Packing Slip", 0, 1, 'C')
    self.heading("Shipping From", 0, .75, 3.5, 12)
    self.heading("Shipping To", 3.5, .75, 3.5, 12)
    self.heading("Seller", 0, 2, 1.5)
    self.heading("Buyer", 1.5, 2, 1.5)
    self.heading("Order Date", 3, 2, 1.5)
    self.heading("Order ID", 4.5, 2, 2.5)

  def heading(self, section, x=0, y=0, w=7, p=11):
    if y: self.pdf.set_y(y + self.top_margin)
    if x: self.pdf.set_x(x + self.left_margin)
    self.pdf.set_font("Arial", "B", p)
    self.pdf.cell(w, .25, section, 0, 2, 'L')
    contents = self.order.get_content(section)
    self.block(contents, w, .2, p)

  def block(self, lines, w=7, h=.2, p=11): 
    self.pdf.set_font("Arial", "", p)
    for line in lines:
      self.pdf.cell(w, h, line, 0, 2, 'L')

  def items(self):
    items = self.order.get_content("Item", True)
    for item in items:
      self.item(item)
      self.y = self.y + 1

  def item(self, item): 
    content, image = item
    x = self.left_margin
    y = self.y + self.top_margin
    self.pdf.image(image, x, y, .75, .75)
    self.pdf.set_xy(x+1, y) 
    self.block(content[1:4], 6, .25) 
    
  def print_items(self):
    items = self.order.get_content("Item", True)
    for item in items:
      self.print_item(item)

  def print_item(self, item):
    content, image = item
    print("Item")
    print(" ", image)
    for index in range(1,4):
      print(" ", content[index])



class Tag():

  name = ""
  attrs = {}
  sections = ["Shipping To", "Order Date", "Order ID", "Buyer", "Item"]

  def __init__(self, order):
    self.order = order
  
  def attr(self, name):
    for (key, value) in self.attrs:
      if key == name: return value
    return None

  def start(self):
    if self.name == "img":
      #if self.attr("alt") == "Poshmark":
      #  print("Logo URL:", self.attr("src"))
      if self.attr("width") == "75":
        self.order.add_image(self.attr("src"))
        #print("Item URL:", self.attr("src"))

  def data(self, data):
    if self.name == "td":
      section = data.strip()
      if section in self.sections:
        self.order.add_section(section)
        #print("Section: ", data)
      else:
        if data.strip() != "": 
          self.order.add_content(data)
          #print("   Data: ", data)

class Parser(HTMLParser):
  def __init__(self, order):
    self.order = order
    self.tag = None
    self.tags = []
    super().__init__()

  def handle_starttag(self, tag, attrs):
    self.tags.append(self.tag)
    self.tag = Tag(self.order)
    self.tag.name = tag
    self.tag.attrs = attrs
    self.tag.start()

  def handle_endtag(self, tag):
    if self.tag != None:
      self.tag = self.tags.pop()

  def handle_data(self, data):
    if self.tag != None:
      self.tag.data(data);

def email_html(file):
  infile = open(file, "rb")
  message = email.message_from_binary_file(infile)
  if message.is_multipart():
    for part in message.get_payload():
      body = part.get_payload()
      break
  else:
    body = message.get_payload(decode=True)
  return quopri.decodestring(body).decode()

def packslip_from_email(email, pdf):
  shipfrom = ["Curtis F Kaylor", "159 Hunter Ave", "Munroe Falls OH 44262"]
  seller = "@revcurtisp"
  order = Order(shipfrom, seller)
  parser = Parser(order)
  html = email_html(email)
  parser.feed(html)
  packslip = PackSlip(order)
  packslip.generate(pdf)


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("emlfile", help="Input File Name (with .eml extension)")
  parser.add_argument("pdffile", help="Output File Name (with .pdf extension)")
  args = parser.parse_args()

  packslip_from_email(args.emlfile, args.pdffile)

if __name__ == "__main__":
    main()
